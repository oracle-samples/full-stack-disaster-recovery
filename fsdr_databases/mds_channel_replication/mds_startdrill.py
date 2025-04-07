#!/usr/bin/python -x
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# Example script written by Antoun Moubarak, Cloud Architecture Specialist

import oci
import argparse
import os
import sys
import json
import time
import logging
from datetime import timezone
import datetime

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Restore MySQL DB backup in the Standby OCI region during a Dry Run (Start Drill plan).')
parser.add_argument("-c", "--config-file", required=True, help="Specify the JSON configuration file.")
parser.add_argument("-to", "--to-replica", required=True, help="Specify the replica Unique Name.")
parser.add_argument("dest_ad_number", nargs='?', const=1, default=1, help="Destination Availability Domain Number (Default value is 1 for AD1)", type=int)
parser.add_argument("-b", "--backup", action='store_true', help="Do a backup of the replica MySQL DB before the restore. (If Automatic Backup not enabled).")
parser.add_argument("-t", "--timeout", help = "Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.", type = int, default = 1200)
args = parser.parse_args()

# Extracting arguments
config_file_name = args.config_file
replica_dst_ad_number = args.dest_ad_number
replica_db_name = args.to_replica
oci_max_wait_seconds = args.timeout

current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Configure logging
logfilename = current_directory + "/logs/disaster_recovery.log"
logging.basicConfig(
    handlers=[
        logging.FileHandler(logfilename,'a'),
        logging.StreamHandler()
    ],
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logging.info(args)

def print_cmd():
    command = sys.argv[0]
    arguments = sys.argv[1:]
    logging.info(f"Executing the following command {command} with arguments {arguments}")

def prepare_regions_file(primary_region,replica_region):
    regions_file = current_directory + "/" + os.path.basename(config_file_name).split('.')[0] + "_regions_" + os.path.basename(__file__).split('.')[0] + "." + time.strftime("%Y%m%d%H%M%S")
    with open(regions_file, "w") as regions:
        regions.write("[PRIMARY]\n")
        regions.write("region = " + primary_region + "\n")
        regions.write("[REPLICA]\n")
        regions.write("region = " + replica_region + "\n")
    return regions_file

def read_config_file(config_file_name):
    # Opening JSON file
    config_file = open(config_file_name)

    # returns JSON object as a dictionary
    data = json.load(config_file)

    # Closing file
    config_file.close()
    return data

def update_config_file(config_file_name,data):
    # Opening JSON file
    with open(config_file_name, 'w') as file:
        json.dump(data, file, indent=4)

    # Closing file
    file.close()
    return 1

def find_replica_in_config(data, replica_db_name):
    # Iterating through the replicas list
    for index, item in enumerate(data["replication_details"]["replicas"]):
        if item["db_unique_name"] == replica_db_name:
            return index
    return -1

def get_db_system_details(db_system_id,oci_region_config,oci_signer):
    try:
        # Initialize the DB System client and fetch DB system details
        oci_db_system_client = oci.mysql.DbSystemClient(config=oci_region_config, signer=oci_signer)
        oci_db_system_details = oci_db_system_client.get_db_system(db_system_id)
        return oci_db_system_details
    except Exception as err:
        logging.error(f"{err}")
        return None

def create_bkp(db_system_id,oci_region_config,oci_signer):
    oci_db_sys_details = get_db_system_details(db_system_id,oci_region_config,oci_signer)
    if not oci_db_sys_details:
        logging.error(f"Failed to retrieve HeatWave MySQL Database System details for backup: {db_system_id}")
        return None
        
    try:
        # Create a manual backup of the MySQL DB system
        oci_db_bkp_clt = oci.mysql.DbBackupsClient(config=oci_region_config, signer=oci_signer)

        # Get the current timestamp
        dt = datetime.datetime.now(timezone.utc)

        # Define backup details
        oci_db_bkp_details = oci.mysql.models.CreateBackupDetails(
            display_name=f"{oci_db_sys_details.data.display_name} Manual Backup {dt}",
            backup_type='FULL',
            db_system_id=db_system_id,
            description=f"{oci_db_sys_details.data.display_name} Manual Backup {dt}",
            retention_in_days=1
        )

        # Trigger the backup creation
        oci_db_bkp_create = oci_db_bkp_clt.create_backup(create_backup_details=oci_db_bkp_details)
        oci_db_bkp_create_id = oci_db_bkp_create.data.id
        oci_db_bkp_get_rsp = oci_db_bkp_clt.get_backup(oci_db_bkp_create_id)
        logging.info(f"Backup in progress for MySQL DB System: {oci_db_sys_details.data.id}")

        # Wait for the backup to become ACTIVE
        oci_db_bkp_create_wait_active = oci.wait_until(
            oci_db_bkp_clt, oci_db_bkp_get_rsp, 'lifecycle_state', 'ACTIVE', max_wait_seconds=oci_max_wait_seconds
        )
        logging.info(f"Backup completed for MySQL DB System: {oci_db_sys_details.data.id}")
        return 1
    except Exception as err:
        logging.error(f"{err}")
        logging.error("Failed during backup creation. Check the provided arguments.")
        return None

def restore_bkp():
    # Read the configuration file
    data = read_config_file(config_file_name)

    # Find Replica details from the config file
    index = find_replica_in_config(data, replica_db_name)
    if index == -1:
        logging.error(f"Replica {replica_db_name} not found in {config_file_name} file.")
        sys.exit(1)

    replica_region = data["replication_details"]["replicas"][index]["region"]
    replica_db_id = data["replication_details"]["replicas"][index]["id"]
    replica_db_compartment_id = data["replication_details"]["replicas"][index]["compartment_id"]

    # Validate destination availability domain number
    if replica_dst_ad_number not in [1, 2, 3]:
        logging.error(f"Wrong AD number provided!")
        sys.exit(1)

    # Prepare a temporary regions file for OCI SDK configuration
    regions_file = prepare_regions_file(replica_region,replica_region)
    
    # Initialize OCI configurations for source and destination regions
    oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    oci_replica_config = oci.config.from_file(file_location=regions_file, profile_name="REPLICA")

    # Retrieve destination region's availability domain details
    try:
        replica_dst_identity_client = oci.identity.IdentityClient(config=oci_replica_config, signer=oci_signer)
        replica_dst_ad_list = replica_dst_identity_client.list_availability_domains(compartment_id=replica_db_compartment_id)
        replica_dst_ad = replica_dst_ad_list.data[replica_dst_ad_number - 1].name
    except Exception as err:
        logging.error(f"{err}")
        os.remove(regions_file)
        logging.error(f"Failed to get the AD details in the Standby region!")
        sys.exit(1)

    # Retrieve and restore backup details
    replica_db_sys_details = get_db_system_details(replica_db_id,oci_replica_config,oci_signer)
    if not replica_db_sys_details:
        os.remove(regions_file)
        logging.error(f"Failed to retrieve HeatWave MySQL Database System details: {replica_db_id}")
        sys.exit(1)

    replica_db_subnet_id = replica_db_sys_details.data.subnet_id

    # Create a Full backup
    if args.backup:
        replica_create_bkp = create_bkp(replica_db_id,oci_replica_config,oci_signer)
        if not replica_create_bkp:
            os.remove(regions_file)
            logging.error(f"Failed to create a backup for the HeatWave MySQL Database System: {replica_db_id}")
            sys.exit(1)

    try:
        # Retrieve the latest active backup for the source DB system
        replica_db_bkp_clt = oci.mysql.DbBackupsClient(config=oci_replica_config, signer=oci_signer)
        replica_db_bkp_lst = replica_db_bkp_clt.list_backups(
            compartment_id=replica_db_compartment_id,
            lifecycle_state="ACTIVE",
            db_system_id=replica_db_id,
            sort_by="timeUpdated",
            sort_order="DESC"
        )
        
        replica_last_bkp_id = replica_db_bkp_lst.data[0].id  
        replica_last_bkp_name = replica_db_bkp_lst.data[0].display_name

        replica_last_bkp_db_details = replica_db_bkp_clt.get_backup(replica_last_bkp_id)

        replica_last_db_name = replica_last_bkp_db_details.data.db_system_snapshot.display_name
        replica_last_bkp_db_name = replica_last_db_name + "_drill"

        replica_shape = replica_last_bkp_db_details.data.db_system_snapshot.shape_name
        replica_data_storage_size_in_gbs = replica_last_bkp_db_details.data.db_system_snapshot.data_storage_size_in_gbs
        replica_ha_enabled = replica_last_bkp_db_details.data.db_system_snapshot.is_highly_available

        replica_deletion_policy_details = oci.mysql.models.CreateDeletionPolicyDetails(
            automatic_backup_retention = replica_last_bkp_db_details.data.db_system_snapshot.deletion_policy.automatic_backup_retention,
            final_backup = replica_last_bkp_db_details.data.db_system_snapshot.deletion_policy.final_backup,
            is_delete_protected = replica_last_bkp_db_details.data.db_system_snapshot.deletion_policy.is_delete_protected
        )   

        replica_data_storage_details = oci.mysql.models.DataStorageDetails(
            is_auto_expand_storage_enabled = replica_last_bkp_db_details.data.db_system_snapshot.data_storage.is_auto_expand_storage_enabled,
            max_storage_size_in_gbs = replica_last_bkp_db_details.data.db_system_snapshot.data_storage.max_storage_size_in_gbs
        )

        replica_backup_policy_details = oci.mysql.models.CreateBackupPolicyDetails(
            is_enabled = False
        )

        # Prepare DB system creation details for restoration
        replica_db_restore_model = oci.mysql.models.CreateDbSystemSourceFromBackupDetails(
            backup_id = replica_last_bkp_id,
            source_type="BACKUP"
        )

        replica_db_create_dbsystem_details = oci.mysql.models.CreateDbSystemDetails(
            availability_domain = replica_dst_ad,
            compartment_id = replica_db_compartment_id,
            source = replica_db_restore_model,
            display_name = replica_last_bkp_db_name,
            subnet_id = replica_db_subnet_id,
            shape_name = replica_shape,
            backup_policy = replica_backup_policy_details,
            data_storage = replica_data_storage_details,
            data_storage_size_in_gbs = replica_data_storage_size_in_gbs,
            deletion_policy = replica_deletion_policy_details,
            is_highly_available = replica_ha_enabled,
            description=f"Dry Run opeartion, Heatwave MySQL restored from backup: {replica_last_bkp_name}. Backup ID: {replica_last_bkp_id}"
        )
        replica_db_restore_clt = oci.mysql.DbSystemClient(config=oci_replica_config, signer=oci_signer)

        # Initiate restoration
        replica_db_create_dbs = replica_db_restore_clt.create_db_system(replica_db_create_dbsystem_details)
        replica_db_create_dbs_id = replica_db_create_dbs.data.id
        replica_db_create_dbs_get_rsp = replica_db_restore_clt.get_db_system(replica_db_create_dbs_id)

        logging.info(f"Drill Operation: Restore Last Backup in progress: {replica_last_bkp_id} in region {replica_region}")

        # Wait for restoration to complete
        replica_db_create_dbs_wait_active = oci.wait_until(
            replica_db_restore_clt,
            replica_db_create_dbs_get_rsp,
            'lifecycle_state',
            'ACTIVE',
            max_wait_seconds=oci_max_wait_seconds
        )

    except Exception as err:
        logging.error(f"{err}")
        os.remove(regions_file)
        logging.error(f"Failed to restore the Backup or No Backup found te be restored for MySQL DB System {replica_db_id} in region {replica_region}")
        sys.exit(1)

    # Update Configuration JSON file
    logging.info(f"Updating {config_file_name} file...")

    # Update values based on scenario
    data["replication_details"]["replicas"][index]["drill_mysql_id"] = replica_db_create_dbs_id

    update_file = update_config_file(config_file_name,data)
    if not update_file:
        os.remove(regions_file)
        logging.error(f"Failed to update {config_file_name}...")
        sys.exit(1)

    # Clean up temporary files
    os.remove(regions_file)
    logging.info(f"Drill Operation: Restore Last Backup MySQL DB System complete: {replica_db_create_dbs_id} in region {replica_region}")
    logging.info(f"To end the Drill, run the stop drill script to delete this restored MySQL System in region {replica_region}")

if __name__ == "__main__":
    print_cmd()
    restore_bkp()