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
import psql_utils

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Terminate a PostgreSQL Database System.')
parser.add_argument("-c", "--config-file", required=True, help="Specify the JSON configuration file.")
parser.add_argument("-t", "--timeout", help = "Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.", type = int, default = 1200)
args = parser.parse_args()

# Extract arguments
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

def terminate_psql():
    # Read the configuration file
    data = psql_utils.read_config_file(config_file_name)

    to_terminate_ocid = data["psql_db_details"]["psql_db_to_terminate_id"]
    oci_src_region = data["psql_db_details"]["standby_region"]
    oci_dst_region = data["psql_db_details"]["standby_region"]

    if not to_terminate_ocid:
        logging.error(f"PostgreSQL Database System OCID not found in the config file.")
        sys.exit(1)

    # Prepare the regions file for OCI SDK configuration
    regions_file = psql_utils.prepare_regions_file(oci_src_region,oci_dst_region,current_directory,base_config_file_name,script_name)

    # Set up OCI signer and configuration
    oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    oci_src_config = oci.config.from_file(file_location=regions_file, profile_name="SOURCE")
    oci_src_db_sys_clt = oci.psql.PostgresqlClient(config=oci_src_config, signer=oci_signer)

    # OCI get PostgreSQL DB Systems details
    oci_src_db_sys_details = psql_utils.get_db_system_details(to_terminate_ocid,oci_src_db_sys_clt)
    if not oci_src_db_sys_details:
        os.remove(regions_file)
        logging.error(f"Failed to retrieve PostgreSQL Database System details: {to_terminate_ocid}")
        sys.exit(1)

    try:
        # Initiate the termination of the PostgreSQL DB system
        logging.info(f"Terminating PostgreSQL Database System: {to_terminate_ocid}")
        delete_db_system_response = oci_src_db_sys_clt.delete_db_system(db_system_id=to_terminate_ocid)

        # Wait for the termination process to complete
        oci_src_db_sys_dbs_get_rsp = oci_src_db_sys_clt.get_db_system(to_terminate_ocid)
        oci.wait_until(oci_src_db_sys_clt, oci_src_db_sys_dbs_get_rsp, 'lifecycle_state', 'DELETED', max_wait_seconds=oci_max_wait_seconds)
    except Exception as err:
        logging.error(f"{err}")
        os.remove(regions_file)
        logging.error(f"Failed to terminate PostgreSQL Database System: {to_terminate_ocid}")
        sys.exit(1)

    # Delete the remaining Configuration for OCI PostgreSQL
    config_to_terminate=data["psql_db_details"]["psql_config_to_terminate_id"]

    if config_to_terminate:
        try: 
            #Begin deletion of configuration
            logging.info(f"Terminating PostgreSQL Configuration: {config_to_terminate}")
            delete_config_response = oci_src_db_sys_clt.delete_configuration(configuration_id=config_to_terminate)
        except Exception as err:
            logging.error(f"{err}")
            os.remove(regions_file)
            logging.error(f"Failed to terminate PostgreSQL Configuration: {config_to_terminate}")
            sys.exit(1)

    
    # Update the configuration file to reflect the deletion
    logging.info(f"Updating {config_file_name} file...")

    data["psql_db_details"]["psql_db_to_terminate_id"] = ""
    data["psql_db_details"]["psql_config_to_terminate_id"] = ""
    update_file = psql_utils.update_config_file(config_file_name,data)
    if not update_file:
        os.remove(regions_file)
        logging.error(f"Failed to update {config_file_name}...")
        sys.exit(1)


    # Clean up temporary regions file
    os.remove(regions_file)
    logging.info(f"Termination of PostgreSQL Database System complete: {to_terminate_ocid}")

if __name__ == "__main__":
    psql_utils.print_cmd()
    terminate_psql()
