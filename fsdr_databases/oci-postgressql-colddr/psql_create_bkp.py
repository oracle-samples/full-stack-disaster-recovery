#!/usr/bin/env -S python3 -x
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# Example script written by Antoun Moubarak, Cloud Architecture Specialist

import oci
import argparse
import os
import sys
import logging
from datetime import timezone
import datetime
import psql_utils

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Create a Manual PostgreSQL Database System backup')
parser.add_argument("-c", "--config-file", required=True, help="Specify the JSON configuration file.")
parser.add_argument("-t", "--timeout", help="Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.", type=int, default=1200)
args = parser.parse_args()

# Extract parsed arguments
config_file_name = args.config_file
oci_max_wait_seconds = args.timeout

# For generating the Regions file for the authentication
# Get the current directory of the script and the script name
current_directory = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.splitext(os.path.basename(__file__))[0]
# Get the base name of the config ficurrent directory of the script
base_config_file_name = os.path.basename(config_file_name).split('.')[0]

# Configure logging
logfilename = psql_utils.config_logging(current_directory,base_config_file_name)

logging.info(args)

def create_bkp():
    # Read the configuration file
    data = psql_utils.read_config_file(config_file_name)

    oci_src_db_system_id = data["psql_db_details"]["id"]
    oci_dst_db_comp_id = data["psql_db_details"]["compartment_id"]
    oci_src_region = data["psql_db_details"]["primary_region"]
    oci_dst_region = data["psql_db_details"]["standby_region"]

    regions_file = psql_utils.prepare_regions_file(oci_src_region,oci_dst_region,current_directory,base_config_file_name,script_name)

    # Set up OCI signer and configuration
    oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    oci_src_config = oci.config.from_file(file_location=regions_file, profile_name="SOURCE")
    oci_db_system_client = oci.psql.PostgresqlClient(config=oci_src_config, signer=oci_signer)
    
    # OCI get PostgreSQL DB Systems details
    oci_src_db_sys_details = psql_utils.get_db_system_details(oci_src_db_system_id,oci_db_system_client)
    if not oci_src_db_sys_details:
        os.remove(regions_file)
        logging.error(f"Failed to retrieve PostgreSQL Database System details: {oci_src_db_system_id}")
        sys.exit(1)

    if oci_src_db_sys_details.data.lifecycle_state != "ACTIVE":
        os.remove(regions_file)
        logging.error(f"PostgreSQL Database System {oci_src_db_sys_details.data.display_name} is not Active!")
        sys.exit(1) 

    logging.info(f"Refreshing {config_file_name} file with current setup.")

    data["psql_db_details"]["display_name"] = oci_src_db_sys_details.data.display_name
    # If using the default configuration, leave the primary_config_id key empty
    if oci_src_db_sys_details.data.config_id.split('.')[1] == "postgresqldefaultconfiguration":
        data["psql_db_details"]["primary_config_id"] = ""
    else:
        data["psql_db_details"]["primary_config_id"] = oci_src_db_sys_details.data.config_id

    data["psql_db_details"]["db_version"] = oci_src_db_sys_details.data.db_version.split('.')[0]
    data["psql_db_details"]["instance_count"] = int(oci_src_db_sys_details.data.instance_count)
    data["psql_db_details"]["instance_memory_size_in_gbs"] = int(oci_src_db_sys_details.data.instance_memory_size_in_gbs)
    data["psql_db_details"]["instance_ocpu_count"] = int(oci_src_db_sys_details.data.instance_ocpu_count)
    data["psql_db_details"]["shape"] = "PostgreSQL." + oci_src_db_sys_details.data.shape + "." + str(oci_src_db_sys_details.data.instance_ocpu_count) + "." + str(oci_src_db_sys_details.data.instance_memory_size_in_gbs) + "GB"
    data["psql_db_details"]["storage_details"]["iops"] = int(oci_src_db_sys_details.data.storage_details.iops)
    data["psql_db_details"]["storage_details"]["is_regionally_durable"] = oci_src_db_sys_details.data.storage_details.is_regionally_durable
    data["psql_db_details"]["storage_details"]["system_type"] = oci_src_db_sys_details.data.storage_details.system_type
    data["psql_db_details"]["management_policy"]["maintenance_window_start"] =  oci_src_db_sys_details.data.management_policy.maintenance_window_start
    try:
        data["psql_db_details"]["management_policy"]["backup_policy"]["backup_start"] = oci_src_db_sys_details.data.management_policy.backup_policy.backup_start.split(' ')[0]
        data["psql_db_details"]["management_policy"]["backup_policy"]["retention_days"] = oci_src_db_sys_details.data.management_policy.backup_policy.retention_days
        data["psql_db_details"]["management_policy"]["backup_policy"]["kind"] = oci_src_db_sys_details.data.management_policy.backup_policy.kind
        if not oci_src_db_sys_details.data.management_policy.backup_policy.copy_policy:
            data["psql_db_details"]["management_policy"]["backup_policy"]["copy_policy"]["compartment_id"] = ""
        else:
            data["psql_db_details"]["management_policy"]["backup_policy"]["copy_policy"]["compartment_id"] = oci_src_db_sys_details.data.management_policy.backup_policy.copy_policy.compartment_id
    except:
        logging.warning(f"Automatic backup NOT enabled on PostgreSQL Database System: {oci_src_db_system_id}")
        data["psql_db_details"]["management_policy"]["backup_policy"]["backup_start"] = ""
        data["psql_db_details"]["management_policy"]["backup_policy"]["retention_days"] = ""
        data["psql_db_details"]["management_policy"]["backup_policy"]["kind"] = "NONE"
        data["psql_db_details"]["management_policy"]["backup_policy"]["copy_policy"]["compartment_id"] = ""

    update_file = psql_utils.update_config_file(config_file_name,data)
    if not update_file:
        os.remove(regions_file)
        logging.error(f"Failed to update {config_file_name}...")
        sys.exit(1)

    try:
        # Create a manual backup of the PostgreSQL DB system
        # Get the current timestamp
        dt = datetime.datetime.now(timezone.utc)

        # Define backup details
        oci_src_db_bkp_details = oci.psql.models.CreateBackupDetails(
            display_name=f"{oci_src_db_sys_details.data.display_name} Manual Backup {dt}",
            compartment_id=oci_dst_db_comp_id,
            db_system_id=oci_src_db_system_id,
            description=f"{oci_src_db_sys_details.data.display_name} Manual Backup {dt}",
            retention_period=oci_src_db_sys_details.data.management_policy.backup_policy.retention_days
        )
        
        # Trigger the backup creation
        oci_src_db_bkp_create = oci_db_system_client.create_backup(create_backup_details=oci_src_db_bkp_details)
        
        backup_headers = oci_src_db_bkp_create.headers
        oci_src_db_bkp_create_id = backup_headers['Location'].rsplit('/', 1)[-1]
        oci_src_db_bkp_get_rsp = oci_db_system_client.get_backup(oci_src_db_bkp_create_id)
        logging.info(f"Backup in progress for PostgreSQL Database System: {oci_src_db_sys_details.data.id}")

        # Wait for the backup to become ACTIVE
        oci_src_db_bkp_create_wait_active = oci.wait_until(
            oci_db_system_client, oci_src_db_bkp_get_rsp, 'lifecycle_state', 'ACTIVE', max_wait_seconds=oci_max_wait_seconds
        )
        logging.info(f"Backup completed for PostgreSQL Database System: {oci_src_db_sys_details.data.id}")
    except Exception as err:
        logging.error(f"{err}")
        os.remove(regions_file)
        logging.error("Failed during backup creation. Check the provided arguments.")
        sys.exit(1)

    # Clean up temporary regions file
    os.remove(regions_file)
    logging.info(f"Backup process completed successfully for PostgreSQL Database System: {oci_src_db_sys_details.data.id}")

if __name__ == "__main__":
    psql_utils.print_cmd()
    create_bkp()
