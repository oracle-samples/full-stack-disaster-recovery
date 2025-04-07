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
parser = argparse.ArgumentParser(description='Terminate MySQL DB in the Standby OCI region during a Dry Run (Stop Drill plan).')
parser.add_argument("-c", "--config-file", required=True, help="Specify the JSON configuration file.")
parser.add_argument("-to", "--to-replica", required=True, help="Specify the replica Unique Name.")
parser.add_argument("--force", action='store_true', help="Force termination even if delete protection is enabled.")
parser.add_argument("--skip", action='store_true', help="Skip final backup before deletion.")
parser.add_argument("-t", "--timeout", help = "Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.", type = int, default = 1200)
args = parser.parse_args()

# Extracting arguments
config_file_name = args.config_file
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

def terminate_mds():
    # Read the configuration file
    data = read_config_file(config_file_name)

    # Find Replica details from the config file
    index = find_replica_in_config(data, replica_db_name)
    if index == -1:
        logging.error(f"Replica {replica_db_name} not found in {config_file_name} file.")
        sys.exit(1)
    
    to_terminate_ocid = data["replication_details"]["replicas"][index]["drill_mysql_id"]
    replica_region = data["replication_details"]["replicas"][index]["region"]

    if not to_terminate_ocid:
        logging.error(f"MySQL OCID not found in the config file.")
        sys.exit(1)

    # Prepare a temporary regions file for OCI SDK configuration
    regions_file = prepare_regions_file(replica_region,replica_region)
    
    # Initialize OCI configurations for source and destination regions
    oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    oci_replica_config = oci.config.from_file(file_location=regions_file, profile_name="REPLICA")

    # Retrieve and restore backup details
    replica_db_sys_details = get_db_system_details(to_terminate_ocid,oci_replica_config,oci_signer)
    if not replica_db_sys_details:
        os.remove(regions_file)
        logging.error(f"Failed to retrieve HeatWave MySQL Database System details: {to_terminate_ocid}")
        sys.exit(1)

    replica_db_sys_clt = oci.mysql.DbSystemClient(config=oci_replica_config, signer=oci_signer)

    # Handle force termination (disable delete protection if enabled)
    if args.force:
        if replica_db_sys_details.data.deletion_policy.is_delete_protected:
            replica_deletion_policy_details = oci.mysql.models.UpdateDeletionPolicyDetails(is_delete_protected=False)
            replica_db_sys_update_details = oci.mysql.models.UpdateDbSystemDetails(deletion_policy=replica_deletion_policy_details)
            replica_db_sys_clt.update_db_system(db_system_id=to_terminate_ocid, update_db_system_details=replica_db_sys_update_details)

    # Handle skipping the final backup
    if args.skip:
        if replica_db_sys_details.data.deletion_policy.is_delete_protected:
            replica_deletion_policy_details = oci.mysql.models.UpdateDeletionPolicyDetails(final_backup="SKIP_FINAL_BACKUP")
            replica_db_sys_update_details = oci.mysql.models.UpdateDbSystemDetails(deletion_policy=replica_deletion_policy_details)
            replica_db_sys_clt.update_db_system(db_system_id=to_terminate_ocid, update_db_system_details=replica_db_sys_update_details)

    try:
        # Initiate the termination of the MySQL DB system
        logging.info(f"Terminating MySQL DB System: {to_terminate_ocid}")
        replica_db_sys_clt.delete_db_system(to_terminate_ocid)

        # Wait for the termination process to complete
        replica_db_sys_dbs_get_rsp = replica_db_sys_clt.get_db_system(to_terminate_ocid)
        oci.wait_until(replica_db_sys_clt, replica_db_sys_dbs_get_rsp, 'lifecycle_state', 'DELETED', max_wait_seconds=oci_max_wait_seconds)
    except Exception as err:
        logging.error(f"{err}")
        os.remove(regions_file)
        logging.error(f"Failed to terminate MySQL DB System: {to_terminate_ocid}")
        sys.exit(1)

    # Update the configuration file to reflect the deletion
    logging.info(f"Updating {config_file_name} file...")

    data["replication_details"]["replicas"][index]["drill_mysql_id"] = ""

    update_file = update_config_file(config_file_name,data)
    if not update_file:
        os.remove(regions_file)
        logging.error(f"Failed to update {config_file_name}...")
        sys.exit(1)


    # Clean up temporary regions file
    os.remove(regions_file)
    logging.info(f"Termination of MySQL DB System complete: {to_terminate_ocid}")

if __name__ == "__main__":
    print_cmd()
    terminate_mds()