#!/usr/bin/python -x
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# Example script written by Antoun Moubarak, Cloud Architecture Specialist

import oci
import argparse
import os
import sys
import csv
import time
from datetime import timezone
import datetime
import pandas

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Copy MySQL DB backup to another OCI region')
parser.add_argument("db_source_label", help="System Label of the Source MySQL system to be copied. System Label from the config file", type=str)
parser.add_argument("-t", "--timeout", help="Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.", type=int, default=1200)
args = parser.parse_args()

# Extract parsed arguments
oci_src_db_system_label = args.db_source_label
oci_max_wait_seconds = args.timeout

# Get the current directory of the script
current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Config file containing system details
config_file_name = current_directory + "/config.csv"

# Read the data from the config file
# The config file is expected to have headers and contain details about various MySQL DB systems.
with open(config_file_name, mode='r', newline='') as file:
    reader = csv.reader(file)
    next(reader, None)  # Skip the header row
    rows = [row for row in reader]

# Use pandas to search for the MySQL DB label in the config file
df = pandas.read_csv(config_file_name, header=0)
for row in rows:
    if row[df.columns.get_loc("MYSQL_DB_LABEL")] == oci_src_db_system_label:
        oci_src_db_system_id = row[df.columns.get_loc("MYSQL_DB_OCID")]
        oci_src_bkp_comp_id = row[df.columns.get_loc("COMPARTMENT_OCID")]
        oci_dst_bkp_comp_id = row[df.columns.get_loc("COMPARTMENT_OCID")]
        oci_src_region = row[df.columns.get_loc("PRIMARY_REGION")]
        oci_dst_region = row[df.columns.get_loc("STANDBY_REGION")]
        break

# Verify that the MySQL DB label was found
try:
    oci_src_db_system_id
except NameError:
    print("\n{datetime.datetime.now(timezone.utc)} ERROR: MySQL DB Label not found! Check the config file.")
    sys.exit(1)

# Prepare a temporary regions file for OCI SDK configuration
regions_file = current_directory + "/regions_copy_bkp." + time.strftime("%Y%m%d%H%M%S")
with open(regions_file, "w") as regions:
    regions.write("[SOURCE]\n")
    regions.write(f"region = {oci_src_region}\n")
    regions.write("[DESTINATION]\n")
    regions.write(f"region = {oci_dst_region}\n")

# Set up OCI signer and configuration
oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
oci_src_config = oci.config.from_file(file_location=regions_file, profile_name="SOURCE")
oci_dst_config = oci.config.from_file(file_location=regions_file, profile_name="DESTINATION")

# Fetch DB system details
try:
    oci_src_db_sys_clt = oci.mysql.DbSystemClient(config=oci_src_config, signer=oci_signer)
    oci_src_db_sys_details = oci_src_db_sys_clt.get_db_system(oci_src_db_system_id)
except Exception as e:
    print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
    os.remove(regions_file)
    print("\n{datetime.datetime.now(timezone.utc)} FAILURE - Error retrieving DB system details! Check the config file.")
    sys.exit(1)

# Fetch the list of backups for the source DB system
try:
    oci_src_db_bkp_clt = oci.mysql.DbBackupsClient(config=oci_src_config, signer=oci_signer)
    oci_src_db_bkp_lst = oci_src_db_bkp_clt.list_backups(
        compartment_id=oci_src_bkp_comp_id,
        lifecycle_state="ACTIVE",
        db_system_id=oci_src_db_system_id,
        sort_by="timeUpdated",
        sort_order="DESC"
    )

    # Extract details of the latest backup
    oci_src_last_bkp_id = oci_src_db_bkp_lst.data[0].id
    oci_src_last_bkp_name = oci_src_db_bkp_lst.data[0].display_name

    # Check if HeatWave cluster is attached
    if oci_src_db_sys_details.data.is_heat_wave_cluster_attached:
        oci_src_db_sys_heat_details = oci_src_db_sys_clt.get_heat_wave_cluster(oci_src_db_system_id)
        oci_src_heat_clus_size = oci_src_db_sys_heat_details.data.cluster_size
        oci_src_heat_clus_shape = oci_src_db_sys_heat_details.data.shape_name
        oci_src_bkp_cp_details = oci.mysql.models.CopyBackupDetails(
            compartment_id=oci_dst_bkp_comp_id,
            display_name=f"{oci_src_last_bkp_name} from {oci_src_region}",
            source_backup_id=oci_src_last_bkp_id,
            source_region=oci_src_region,
            description=f"Source Backup : {oci_src_last_bkp_id} copied from {oci_src_region} region. oci_src_heat=YES oci_src_heat_clus_size={oci_src_heat_clus_size} oci_src_heat_clus_shape={oci_src_heat_clus_shape}"
        )
    else:
        oci_src_bkp_cp_details = oci.mysql.models.CopyBackupDetails(
            compartment_id=oci_dst_bkp_comp_id,
            display_name=f"{oci_src_last_bkp_name} from {oci_src_region}",
            source_backup_id=oci_src_last_bkp_id,
            source_region=oci_src_region,
            description=f"Source Backup : {oci_src_last_bkp_id} copied from {oci_src_region} region. oci_src_heat=NO"
        )

    # Initiate backup copy to destination
    oci_dst_db_bkp_clt = oci.mysql.DbBackupsClient(config=oci_dst_config, signer=oci_signer)
    try:
        oci_dst_prv_act_bkp_rsp = oci_dst_db_bkp_clt.list_backups(
            compartment_id=oci_src_bkp_comp_id,
            db_system_id=oci_src_db_system_id,
            lifecycle_state="ACTIVE",
            sort_by="timeCreated",
            sort_order="DESC"
        )
        oci_dst_prv_act_last_bkp_id = oci_dst_prv_act_bkp_rsp.data[0].id
        oci_dst_prv_act_last_bkp_details = oci_dst_db_bkp_clt.get_backup(oci_dst_prv_act_last_bkp_id)
        oci_dst_prv_act_last_bkp_orig_source = oci_dst_prv_act_last_bkp_details.data.original_source_backup_id

        if oci_dst_prv_act_last_bkp_orig_source != oci_src_last_bkp_id:
            oci_dst_db_bkp_copy = oci_dst_db_bkp_clt.copy_backup(copy_backup_details=oci_src_bkp_cp_details)
            print(f"\n{datetime.datetime.now(timezone.utc)} INFO - Copy Last Backup in progress: {oci_src_last_bkp_id}")
            oci.wait_until(oci_dst_db_bkp_clt, oci_dst_db_bkp_clt.get_backup(oci_dst_db_bkp_copy.data.id), 'lifecycle_state', 'ACTIVE', max_wait_seconds=oci_max_wait_seconds)
        else:
            print(f"\n{datetime.datetime.now(timezone.utc)} INFO - Last Backup already copied: {oci_src_last_bkp_id}")
    except Exception:
        print(f"\n{datetime.datetime.now(timezone.utc)} INFO - No Previous Backup found!")
        oci_dst_db_bkp_copy = oci_dst_db_bkp_clt.copy_backup(copy_backup_details=oci_src_bkp_cp_details)
        print(f"{datetime.datetime.now(timezone.utc)} INFO - Copy Last Backup in progress: {oci_src_last_bkp_id}")
        oci.wait_until(oci_dst_db_bkp_clt, oci_dst_db_bkp_clt.get_backup(oci_dst_db_bkp_copy.data.id), 'lifecycle_state', 'ACTIVE', max_wait_seconds=oci_max_wait_seconds)

except Exception as e:
    print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
    os.remove(regions_file)
    print(f"\n{datetime.datetime.now(timezone.utc)} FAILURE - Error copying backup to remote region: {oci_dst_region}")
    sys.exit(1)

# Cleanup and completion message
os.remove(regions_file)
print(f"{datetime.datetime.now(timezone.utc)} INFO - Copy Last Backup complete: {oci_src_last_bkp_id}\n")
