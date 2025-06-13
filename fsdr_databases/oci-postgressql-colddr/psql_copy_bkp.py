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
import psql_utils

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Copy PostgreSQL Database System backup to another OCI region')
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

def copy_bkp():
    # Read the configuration file
    data = psql_utils.read_config_file(config_file_name)

    oci_src_db_system_id = data["psql_db_details"]["id"]
    oci_src_bkp_comp_id = data["psql_db_details"]["compartment_id"]
    oci_dst_bkp_comp_id = data["psql_db_details"]["compartment_id"]
    oci_src_region = data["psql_db_details"]["primary_region"]
    oci_dst_region = data["psql_db_details"]["standby_region"]

    # Prepare a temporary regions file for OCI SDK configuration
    regions_file = psql_utils.prepare_regions_file(oci_src_region,oci_dst_region,current_directory,base_config_file_name,script_name)
    
    # Set up OCI signer and configuration
    oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    oci_src_config = oci.config.from_file(file_location=regions_file, profile_name="SOURCE")
    oci_dst_config = oci.config.from_file(file_location=regions_file, profile_name="DESTINATION")
    oci_src_db_bkp_clt = oci.psql.PostgresqlClient(config=oci_src_config, signer=oci_signer)
    oci_dst_db_bkp_clt = oci.psql.PostgresqlClient(config=oci_dst_config, signer=oci_signer)

    # OCI get PostgreSQL Database System details
    oci_src_db_sys_details = psql_utils.get_db_system_details(oci_src_db_system_id,oci_src_db_bkp_clt)
    if not oci_src_db_sys_details:
        os.remove(regions_file)
        logging.error(f"Failed to retrieve PostgreSQL Database System details: {oci_src_db_system_id}")
        sys.exit(1)

    # Fetch the list of backups for the source DB system
    try:
        oci_src_db_bkp_lst = oci_src_db_bkp_clt.list_backups(
            compartment_id=oci_src_bkp_comp_id,
            lifecycle_state="ACTIVE",
            id=oci_src_db_system_id,
            sort_by="timeCreated",
            sort_order="DESC"
        )

        # Extract details of the latest backup
        oci_src_last_bkp_id = oci_src_db_bkp_lst.data.items[0].id
        oci_src_last_bkp_name = oci_src_db_bkp_lst.data.items[0].display_name
        oci_src_last_bkp_cp_status = oci_src_db_bkp_lst.data.items[0].copy_status

        if oci_src_last_bkp_cp_status:
            for item in oci_src_last_bkp_cp_status:
                if item.region == oci_dst_region:
                    if item.state == "COPIED" or item.state == "COPYING":
                        try:
                            oci_dst_get_bkp_details = oci_dst_db_bkp_clt.get_backup(backup_id=item.backup_id)
                            if oci_dst_get_bkp_details:
                                os.remove(regions_file)
                                logging.info(f"Last Backup {oci_src_last_bkp_id} {item.state} to {oci_dst_region}")
                                sys.exit(0)
                        except Exception as err:
                            logging.info(f"Backup ID {item.backup_id} not found in region {oci_dst_region}")

        oci_src_bkp_cp_details = oci.psql.models.BackupCopyDetails(
            compartment_id=oci_dst_bkp_comp_id,
            regions=[str(oci_dst_region)],
            retention_period=oci_src_db_bkp_lst.data.items[0].retention_period
        )

        # Initiate backup copy to destination
        oci_dst_db_bkp_copy = oci_src_db_bkp_clt.backup_copy(backup_id=oci_src_last_bkp_id,backup_copy_details=oci_src_bkp_cp_details)
        logging.info(f"Copy Last Backup to region {oci_dst_region} in progress: {oci_src_last_bkp_id}")

        oci_src_db_bkp_status = oci_src_db_bkp_clt.get_backup(backup_id=oci_src_last_bkp_id)
        oci_src_db_bkp_cp_status = oci_src_db_bkp_status.data.copy_status
        for item in oci_src_db_bkp_cp_status:
            if item.region == oci_dst_region:
                oci_dst_db_bkp_id = item.backup_id
                while not oci_dst_db_bkp_id:
                    oci_src_db_bkp_status = oci_src_db_bkp_clt.get_backup(backup_id=oci_src_last_bkp_id)
                    oci_src_db_bkp_cp_status = oci_src_db_bkp_status.data.copy_status
                    for item in oci_src_db_bkp_cp_status:
                        if item.region == oci_dst_region:
                            if item.region == oci_dst_region:
                                oci_dst_db_bkp_id = item.backup_id

        oci.wait_until(oci_dst_db_bkp_clt, oci_dst_db_bkp_clt.get_backup(oci_dst_db_bkp_id), 'lifecycle_state', 'ACTIVE', max_wait_seconds=oci_max_wait_seconds)
    except Exception as err:
        logging.error(f"{err}")
        os.remove(regions_file)
        logging.error(f"Failed to copy backup to remote region: {oci_dst_region}")
        sys.exit(1)

    # Cleanup and completion message
    os.remove(regions_file)
    logging.info(f"Copy Last Backup to region {oci_dst_region} complete: {oci_src_last_bkp_id}")

if __name__ == "__main__":
    psql_utils.print_cmd()
    copy_bkp()
