#!/usr/bin/env -S python3 -x
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# This script copies the OCI Database with PostgreSQL configuration from Primary to Standby region.
# The "psql_create_bkp.py" needs to be run before copying the configuration.
# Example script written by Piotr Kurzynoga - Open Source Data Platform

import oci
import argparse
import os
import sys
import json
import logging
from datetime import timezone
import datetime
import psql_utils

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Create a Copy of a OCI Database with PostgreSQL configuration in a remote region')
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

def create_psql_config():
    #Get current time
    dt = datetime.datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Get the configuration OCID
    data = psql_utils.read_config_file(config_file_name)
    oci_dst_db_comp_id = data["psql_db_details"]["compartment_id"]
    oci_src_db_display_name = data["psql_db_details"]["display_name"]
    oci_src_db_system_id = data["psql_db_details"]["id"]
    oci_psql_config_id = data["psql_db_details"]["primary_config_id"]
    oci_src_region = data["psql_db_details"]["primary_region"]
    oci_dst_region = data["psql_db_details"]["standby_region"]

    regions_file = psql_utils.prepare_regions_file(oci_src_region,oci_dst_region,current_directory,base_config_file_name,script_name)

    # Set up OCI signer and configuration
    oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    oci_src_config = oci.config.from_file(file_location=regions_file, profile_name="SOURCE")
    oci_dst_config = oci.config.from_file(file_location=regions_file, profile_name="DESTINATION")

    # Read the configuration into a file for non-default values
    overridden_params = {}
    psql_config_file =  current_directory + "/" + f"psql_config_bk_{dt}.json"
    oci_src_db_system_client = oci.psql.PostgresqlClient(config=oci_src_config, signer=oci_signer)

    # OCI get PostgreSQL DB Systems details
    oci_src_db_sys_details = psql_utils.get_db_system_details(oci_src_db_system_id,oci_src_db_system_client)
    if not oci_src_db_sys_details:
        os.remove(regions_file)
        logging.error(f"Failed to retrieve PostgreSQL Database System details: {oci_src_db_system_id}")
        sys.exit(1)

    if oci_src_db_sys_details.data.config_id.split('.')[1] == "postgresqldefaultconfiguration":
        logging.info(f"PostgreSQL Database System {oci_src_db_display_name} is using default configuration: {oci_src_db_sys_details.data.config_id}")

        # Update the metadata with standby configuration
        data["psql_db_details"]["primary_config_id"] = ""
        data["psql_db_details"]["standby_config_id"] = ""
        update_file = psql_utils.update_config_file(config_file_name,data)
        if not update_file:
            os.remove(regions_file)
            logging.error(f"Failed to update {config_file_name}...")
            sys.exit(1)
        
    else:
        oci_psql_src_config = oci_src_db_system_client.get_configuration(oci_psql_config_id).data
        try:
            for item in oci_psql_src_config.configuration_details.items:
                key = item.config_key
                overridden_value =  item.overriden_config_value
                is_overridable = item.is_overridable
                if overridden_value and is_overridable:
                    overridden_params[key] = overridden_value

            config_overrides = [
                oci.psql.models.ConfigOverrides(config_key=k, overriden_config_value=v)
                for k, v in overridden_params.items()
            ]

            with open(psql_config_file, "w") as f:
                json.dump(overridden_params, f, indent=2)

            # Closing file
            f.close()
            logging.info(f"OCI PostgreSQL configuration backed up successfully in file {psql_config_file}.")
        except Exception as err:
            logging.error(f"{err}")
            os.remove(regions_file)
            logging.error("Failed during DB configuration fetch.")
            sys.exit(1)

        try:
            # Prepare target OCI PostgreSQL configuration
            override_collection = oci.psql.models.DbConfigurationOverrideCollection(items=config_overrides)

            create_config_args = {
                "display_name":oci_psql_src_config.display_name + "_DR",
                "description":oci_psql_src_config.description,
                "compartment_id":oci_dst_db_comp_id,
                "is_flexible":oci_psql_src_config.is_flexible,
                "db_version":oci_psql_src_config.db_version.split('.')[0],
                "shape":oci_psql_src_config.shape,
                "db_configuration_overrides":override_collection
            }

            if oci_psql_src_config.is_flexible:
                logging.info("Using flexible shape configuration.")
            else:
                create_config_args["instance_ocpu_count"] = int(oci_psql_src_config.instance_ocpu_count)
                create_config_args["instance_memory_size_in_gbs"] = int(oci_psql_src_config.instance_memory_size_in_gbs)
                logging.info("Using fixed shape configuration.")

            create_config_details = oci.psql.models.CreateConfigurationDetails(**create_config_args)

            # Create configuration in target region
            oci_dst_db_system_client = oci.psql.PostgresqlClient(config=oci_dst_config, signer=oci_signer)
            oci_psql_dst_config = oci_dst_db_system_client.create_configuration(create_config_details)
            oci_psql_dst_config_id = oci_psql_dst_config.data.id
            logging.info(f"OCI PostgreSQL DR configuration created {oci_psql_dst_config_id}")
            oci_psql_dst_config_status =oci_dst_db_system_client.get_configuration(oci_psql_dst_config_id)
            # Update the metadata with standby configuration
            data["psql_db_details"]["standby_config_id"] = oci_psql_dst_config_id
            update_file = psql_utils.update_config_file(config_file_name,data)
            if not update_file:
                os.remove(regions_file)
                logging.error(f"Failed to update {config_file_name}...")
                sys.exit(1)

            # Wait for configuration to be active
            oci_psql_dst_config_wait_active = oci.wait_until(
                oci_dst_db_system_client, oci_psql_dst_config_status, 'lifecycle_state', 'ACTIVE', max_wait_seconds=oci_max_wait_seconds
            )

            logging.info("OCI PostgreSQL DR configuration is now ACTIVE.")
        except Exception as err:
            logging.error(f"{err}")
            os.remove(regions_file)
            logging.error("Creation of OCI PostgreSQL DR configuration failed. Please re-create the configuration manually before proceeding.")
            sys.exit(1)

    # Clean up regions file
    os.remove(regions_file)


if __name__ == "__main__":
    psql_utils.print_cmd()
    create_psql_config()