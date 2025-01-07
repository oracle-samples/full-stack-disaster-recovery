#!/usr/bin/python
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# Example script written by Antoun Moubarak, Cloud Architecture Specialist

import oci
import argparse
import os
import subprocess
import sys
import csv
import time
from datetime import timezone 
import datetime
import pandas

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Restore MySQL DB backup to another OCI region')
parser.add_argument("db_source_label", help="System Label of the Source MySQL system to be restored. System Label from the config file", type=str)
parser.add_argument("dest_ad_number", nargs='?', const=1, default=1, help="Destination Availability Domain Number (Default value is 1 for AD1)", type=int)
parser.add_argument("--config", action='store_true', help="Update config file with the new OCID of the restored MySQL DB System")
group = parser.add_mutually_exclusive_group()
group.add_argument("--switch", action='store_true', help="TAG the Source MySQL DB to be terminated after a Restore (Switchover scenario)")
group.add_argument("--drill", action='store_true', help="TAG the Target MySQL DB to be terminated after a Restore (Dry Run scenario)")
parser.add_argument("-t", "--timeout", help = "Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.", type = int, default = 1200)
args = parser.parse_args()

# Extracting arguments
oci_src_db_system_label = args.db_source_label
oci_dst_ad_number = args.dest_ad_number
oci_max_wait_seconds = args.timeout

current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Config file containing system details
config_file_name = current_directory + "/config.csv"

# Read the data from the config file
# The config file is expected to have headers and contain details about various MySQL DB systems.
with open(config_file_name, mode='r', newline='') as file:
    reader = csv.reader(file)
    next(reader, None)  # Skip headers
    rows = [row for row in reader]

# Use pandas to search for the MySQL DB label in the config file
df = pandas.read_csv(config_file_name, header=0)
for row in rows:
    if row[df.columns.get_loc("MYSQL_DB_LABEL")] == oci_src_db_system_label:
        oci_src_db_system_id = row[df.columns.get_loc("MYSQL_DB_OCID")]
        oci_dst_db_comp_id = row[df.columns.get_loc("COMPARTMENT_OCID")]
        oci_dst_bkp_comp_id = row[df.columns.get_loc("COMPARTMENT_OCID")]
        oci_src_region = row[df.columns.get_loc("PRIMARY_REGION")]
        oci_dst_region = row[df.columns.get_loc("STANDBY_REGION")]
        oci_src_subnet_id = row[df.columns.get_loc("PRIMARY_SUBNET_OCID")]
        oci_dst_subnet_id = row[df.columns.get_loc("STANDBY_SUBNET_OCID")]
        break

# Validation for mutually dependent arguments
if args.switch and not args.config:
    parser.error('--config argument is required with --switch')
if args.drill and not args.config:
    parser.error('--config argument is required with --drill')

# Validate destination availability domain number
if oci_dst_ad_number not in [1, 2, 3]:
    print("\n{datetime.datetime.now(timezone.utc)} FAILURE - Wrong AD number provided!")
    sys.exit(1)

# Ensure the source DB system ID is found
try:
    oci_src_db_system_id
except NameError:
    print("\n{datetime.datetime.now(timezone.utc)} ERROR: MySQL DB Label not found! Check the config file.")
    sys.exit(1)

# Prepare a temporary regions file for OCI SDK configuration
regions_file = current_directory + "/regions_restore_bkp." + time.strftime("%Y%m%d%H%M%S")
with open(regions_file, "w") as regions:
    regions.write("[SOURCE]\n")
    regions.write(f"region = {oci_src_region}\n")
    regions.write("[DESTINATION]\n")
    regions.write(f"region = {oci_dst_region}\n")

# Initialize OCI configurations for source and destination regions
oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
oci_src_config = oci.config.from_file(file_location=regions_file, profile_name="SOURCE")
oci_dst_config = oci.config.from_file(file_location=regions_file, profile_name="DESTINATION")

# Retrieve destination region's availability domain details
try:
    oci_dst_identity_client = oci.identity.IdentityClient(config=oci_dst_config, signer=oci_signer)
    oci_dst_ad_list = oci_dst_identity_client.list_availability_domains(compartment_id=oci_dst_db_comp_id)
    oci_dst_ad = oci_dst_ad_list.data[oci_dst_ad_number - 1].name
except Exception as e:
    print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
    os.remove(regions_file)
    print(f"\n{datetime.datetime.now(timezone.utc)} FAILURE - Error getting the AD details in the destination region!")
    sys.exit(1)

# Retrieve and restore backup details
try:
    try:
        # Retrieve source DB system details
        oci_src_db_sys_clt = oci.mysql.DbSystemClient(config=oci_src_config, signer=oci_signer)
        oci_src_db_sys_details = oci_src_db_sys_clt.get_db_system(oci_src_db_system_id)
        
        # Check if HeatWave is enabled and get its details
        if oci_src_db_sys_details.data.is_heat_wave_cluster_attached:
            oci_src_db_sys_heat_details = oci_src_db_sys_clt.get_heat_wave_cluster(oci_src_db_system_id)
            add_heat = True
            oci_src_heat_clus_size = oci_src_db_sys_heat_details.data.cluster_size
            oci_src_heat_clus_shape = oci_src_db_sys_heat_details.data.shape_name
            oci_dst_heat_details = oci.mysql.models.AddHeatWaveClusterDetails(
                cluster_size=oci_src_heat_clus_size,
                shape_name=oci_src_heat_clus_shape
            )
        else:
            add_heat = False
    except Exception as e:
        print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
        print(f"\n{datetime.datetime.now(timezone.utc)} FAILURE - Unable to get if source DB has HeatWave enabled.")
        add_heat = False

    # Retrieve the latest active backup for the source DB system
    oci_dst_db_bkp_clt = oci.mysql.DbBackupsClient(config=oci_dst_config, signer=oci_signer)
    oci_dst_db_bkp_lst = oci_dst_db_bkp_clt.list_backups(
        compartment_id=oci_dst_db_comp_id,
        lifecycle_state="ACTIVE",
        db_system_id=oci_src_db_system_id,
        sort_by="timeUpdated",
        sort_order="DESC"
    )
    oci_dst_last_bkp_id = oci_dst_db_bkp_lst.data[0].id
    oci_dst_last_bkp_name = oci_dst_db_bkp_lst.data[0].display_name
    oci_dst_last_bkp_db_details = oci_dst_db_bkp_clt.get_backup(oci_dst_last_bkp_id)
    oci_dst_last_db_name = oci_dst_last_bkp_db_details.data.db_system_snapshot.display_name
    oci_dst_last_bkp_db_name = oci_dst_last_db_name
    oci_dst_shape = oci_dst_last_bkp_db_details.data.db_system_snapshot.shape_name
    oci_dst_data_storage_size_in_gbs = oci_dst_last_bkp_db_details.data.db_system_snapshot.data_storage_size_in_gbs
    oci_dst_ha_enabled = oci_dst_last_bkp_db_details.data.db_system_snapshot.is_highly_available
    oci_dst_deletion_policy_details = oci.mysql.models.CreateDeletionPolicyDetails(
        automatic_backup_retention=oci_dst_last_bkp_db_details.data.db_system_snapshot.deletion_policy.automatic_backup_retention,
        final_backup=oci_dst_last_bkp_db_details.data.db_system_snapshot.deletion_policy.final_backup,
        is_delete_protected=oci_dst_last_bkp_db_details.data.db_system_snapshot.deletion_policy.is_delete_protected
    )
    oci_dst_data_storage_details = oci.mysql.models.DataStorageDetails(
        is_auto_expand_storage_enabled=oci_dst_last_bkp_db_details.data.db_system_snapshot.data_storage.is_auto_expand_storage_enabled,
        max_storage_size_in_gbs=oci_dst_last_bkp_db_details.data.db_system_snapshot.data_storage.max_storage_size_in_gbs
    )
    oci_dst_backup_policy_details = oci.mysql.models.CreateBackupPolicyDetails(
        is_enabled=oci_dst_last_bkp_db_details.data.db_system_snapshot.backup_policy.is_enabled,
        retention_in_days=oci_dst_last_bkp_db_details.data.db_system_snapshot.backup_policy.retention_in_days,
        window_start_time=oci_dst_last_bkp_db_details.data.db_system_snapshot.backup_policy.window_start_time
    )

    # Prepare DB system creation details for restoration
    oci_dst_db_restore_model = oci.mysql.models.CreateDbSystemSourceFromBackupDetails(
        backup_id=oci_dst_last_bkp_id,
        source_type="BACKUP"
    )
    oci_dst_db_create_dbsystem_details = oci.mysql.models.CreateDbSystemDetails(
        availability_domain=oci_dst_ad,
        compartment_id=oci_dst_db_comp_id,
        source=oci_dst_db_restore_model,
        display_name=oci_dst_last_bkp_db_name,
        subnet_id=oci_dst_subnet_id,
        shape_name=oci_dst_shape,
        backup_policy=oci_dst_backup_policy_details,
        data_storage=oci_dst_data_storage_details,
        data_storage_size_in_gbs=oci_dst_data_storage_size_in_gbs,
        deletion_policy=oci_dst_deletion_policy_details,
        is_highly_available=oci_dst_ha_enabled,
        description=f"Restored from backup: {oci_dst_last_bkp_name} of DB system {oci_dst_last_db_name}. Backup ID: {oci_dst_last_bkp_id}"
    )
    oci_dst_db_restore_clt = oci.mysql.DbSystemClient(config=oci_dst_config, signer=oci_signer)

    # Initiate restoration
    oci_dst_db_create_dbs = oci_dst_db_restore_clt.create_db_system(oci_dst_db_create_dbsystem_details)
    oci_dst_db_create_dbs_id = oci_dst_db_create_dbs.data.id
    oci_dst_db_create_dbs_get_rsp = oci_dst_db_restore_clt.get_db_system(oci_dst_db_create_dbs_id)
    
    print(f"\n{datetime.datetime.now(timezone.utc)} INFO - Restore Last Backup in progress: {oci_dst_last_bkp_id}")

    # Wait for restoration to complete
    oci_dst_db_create_dbs_wait_active = oci.wait_until(
        oci_dst_db_restore_clt,
        oci_dst_db_create_dbs_get_rsp,
        'lifecycle_state',
        'ACTIVE',
        max_wait_seconds=oci_max_wait_seconds
    )

    # Add HeatWave cluster if needed
    if add_heat:
        oci_dst_db_restore_clt.add_heat_wave_cluster(
            db_system_id=oci_dst_db_create_dbs_id,
            add_heat_wave_cluster_details=oci_dst_heat_details
        )

except Exception as e:
  print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
  os.remove(regions_file)
  print(f"\n{datetime.datetime.now(timezone.utc)} FAILURE - Error Restoring the Backup or No Backup found te be restored for MySQL DB System {oci_src_db_system_id} in region {oci_dst_region}")
  sys.exit(1)

# Update the configuration file if required - Reopen because Headers were excluded
if args.config:
    print(f"{datetime.datetime.now(timezone.utc)} INFO - Updating config file...")
    with open(config_file_name, mode='r', newline='') as file:
        reader = csv.reader(file)
        rows = [row for row in reader]

    df = pandas.read_csv(config_file_name, header=0)
    for row in rows:
        if row[df.columns.get_loc("MYSQL_DB_LABEL")] == oci_src_db_system_label:
            new_primary_region = row[df.columns.get_loc("STANDBY_REGION")]
            new_primary_subnet = row[df.columns.get_loc("STANDBY_SUBNET_OCID")]
            new_primary_dns_view = row[df.columns.get_loc("STANDBY_DNS_VIEW_OCID")]
            break

    # Update values based on scenario
    if args.drill:
        row[df.columns.get_loc("MYSQL_DB_TO_TERMINATE")] = oci_dst_db_create_dbs_id
    elif args.switch:
        old_mds_id = row[df.columns.get_loc("MYSQL_DB_OCID")]
        row[df.columns.get_loc("MYSQL_DB_OCID")] = oci_dst_db_create_dbs_id
        row[df.columns.get_loc("MYSQL_DB_TO_TERMINATE")] = old_mds_id
        row[df.columns.get_loc("STANDBY_REGION")] = row[df.columns.get_loc("PRIMARY_REGION")]
        row[df.columns.get_loc("PRIMARY_REGION")] = new_primary_region
        row[df.columns.get_loc("STANDBY_SUBNET_OCID")] = row[df.columns.get_loc("PRIMARY_SUBNET_OCID")]
        row[df.columns.get_loc("PRIMARY_SUBNET_OCID")] = new_primary_subnet
        row[df.columns.get_loc("STANDBY_DNS_VIEW_OCID")] = row[df.columns.get_loc("PRIMARY_DNS_VIEW_OCID")]
        row[df.columns.get_loc("PRIMARY_DNS_VIEW_OCID")] = new_primary_dns_view
    else:
        row[df.columns.get_loc("MYSQL_DB_OCID")] = oci_dst_db_create_dbs_id
        row[df.columns.get_loc("STANDBY_REGION")] = row[df.columns.get_loc("PRIMARY_REGION")]
        row[df.columns.get_loc("PRIMARY_REGION")] = new_primary_region
        row[df.columns.get_loc("STANDBY_SUBNET_OCID")] = row[df.columns.get_loc("PRIMARY_SUBNET_OCID")]
        row[df.columns.get_loc("PRIMARY_SUBNET_OCID")] = new_primary_subnet
        row[df.columns.get_loc("STANDBY_DNS_VIEW_OCID")] = row[df.columns.get_loc("PRIMARY_DNS_VIEW_OCID")]
        row[df.columns.get_loc("PRIMARY_DNS_VIEW_OCID")] = new_primary_dns_view

    # Write updated data back to the config file
    with open(config_file_name, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows)

# Clean up temporary files
os.remove(regions_file)
print(f"{datetime.datetime.now(timezone.utc)} INFO - Restore Last Backup MySQL DB System complete: {oci_dst_db_create_dbs_id}\n")
