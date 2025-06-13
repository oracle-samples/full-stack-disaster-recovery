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
parser = argparse.ArgumentParser(description='Create a PostgreSQL Database System another OCI region from the last available backup')
parser.add_argument("-c", "--config-file", required=True, help="Specify the JSON configuration file.")
parser.add_argument("dest_ad_number", nargs='?', const=1, default=1, help="Destination Availability Domain Number (Default value is 1 for AD1)", type=int)
parser.add_argument("-o", "--operation", help="Specify the operation type to execute. Default operation is drill (Dry Run).", choices=['drill', 'switchover', 'failover'], type = str, default = "drill")
parser.add_argument("-t", "--timeout", help = "Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.", type = int, default = 1200)
args = parser.parse_args()

# Extracting arguments
config_file_name = args.config_file
oci_dst_ad_number = args.dest_ad_number
oci_max_wait_seconds = args.timeout
oci_dr_operation = args.operation

# For generating the Regions file for the authentication
# Get the current directory of the script and the script name
current_directory = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.splitext(os.path.basename(__file__))[0]
# Get the base name of the config ficurrent directory of the script
base_config_file_name = os.path.basename(config_file_name).split('.')[0]

# Configure logging
logfilename = psql_utils.config_logging(current_directory,base_config_file_name)

logging.info(args)

def restore_bkp():
    # Read the configuration file
    data = psql_utils.read_config_file(config_file_name)

    oci_src_db_system_id = data["psql_db_details"]["id"]
    oci_dst_db_comp_id = data["psql_db_details"]["compartment_id"]
    oci_dst_bkp_comp_id = data["psql_db_details"]["compartment_id"]
    oci_src_region = data["psql_db_details"]["primary_region"]
    oci_dst_region = data["psql_db_details"]["standby_region"]
    oci_src_subnet_id = data["psql_db_details"]["primary_subnet_id"]
    oci_dst_subnet_id = data["psql_db_details"]["standby_subnet_id"]

    oci_dst_db_display_name = data["psql_db_details"]["display_name"]
    oci_dst_db_config_id = data["psql_db_details"]["standby_config_id"]
    oci_dst_db_version = data["psql_db_details"]["db_version"]
    oci_dst_db_username = data["psql_db_details"]["admin_user"]
    oci_dst_db_secret_id = data["psql_db_details"]["standby_admin_secrect_id"]
    oci_dst_db_instance_count = data["psql_db_details"]["instance_count"]
    oci_dst_db_memory_size = data["psql_db_details"]["instance_memory_size_in_gbs"]
    oci_dst_db_ocpu_count = data["psql_db_details"]["instance_ocpu_count"]
    oci_dst_db_shape = data["psql_db_details"]["shape"]
    oci_dst_db_iops = data["psql_db_details"]["storage_details"]["iops"]
    oci_dst_db_is_regionally_durable = data["psql_db_details"]["storage_details"]["is_regionally_durable"]
    oci_dst_db_system_type = str(data["psql_db_details"]["storage_details"]["system_type"])
    oci_dst_db_bkp_start = str(data["psql_db_details"]["management_policy"]["backup_policy"]["backup_start"])
    oci_dst_db_bkp_kind = data["psql_db_details"]["management_policy"]["backup_policy"]["kind"]
    oci_dst_db_bkp_retention_days = data["psql_db_details"]["management_policy"]["backup_policy"]["retention_days"]
    oci_dst_db_bkp_cp_compartment_id = data["psql_db_details"]["management_policy"]["backup_policy"]["copy_policy"]["compartment_id"]
    oci_dst_db_maintenance_window_start = data["psql_db_details"]["management_policy"]["maintenance_window_start"]

    # Validate destination availability domain number
    if oci_dst_ad_number not in [1, 2, 3]:
        logging.error(f"Wrong AD number provided!")
        sys.exit(1)

    # Prepare a temporary regions file for OCI SDK configuration
    regions_file = psql_utils.prepare_regions_file(oci_src_region,oci_dst_region,current_directory,base_config_file_name,script_name)
    
    # Initialize OCI configurations for source and destination regions
    oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    oci_dst_config = oci.config.from_file(file_location=regions_file, profile_name="DESTINATION")
    oci_dst_db_sys_clt = oci.psql.PostgresqlClient(config=oci_dst_config, signer=oci_signer)
    oci_dst_identity_client = oci.identity.IdentityClient(config=oci_dst_config, signer=oci_signer)

    # Retrieve destination region's availability domain details
    try:
        oci_dst_ad_list = oci_dst_identity_client.list_availability_domains(compartment_id=oci_dst_db_comp_id)
        oci_dst_ad = oci_dst_ad_list.data[oci_dst_ad_number - 1].name
    except Exception as err:
        logging.error(f"{err}")
        os.remove(regions_file)
        logging.error(f"Failed to get the AD details in the destination region!")
        sys.exit(1)

    # Retrieve and restore backup details
    try:
        # Retrieve the latest active backup for the source DB system
        oci_dst_db_bkp_lst = oci_dst_db_sys_clt.list_backups(
            compartment_id=oci_dst_db_comp_id,
            lifecycle_state="ACTIVE",
            id=oci_src_db_system_id,
            sort_by="timeCreated",
            sort_order="DESC"
        )

        # Extract details of the latest backup
        oci_dst_last_bkp_id = oci_dst_db_bkp_lst.data.items[0].id
        oci_dst_last_bkp_name = oci_dst_db_bkp_lst.data.items[0].display_name
        oci_dst_db_system_bkp_source_details = oci.psql.models.BackupSourceDetails(backup_id=oci_dst_last_bkp_id,source_type="BACKUP",is_having_restore_config_overrides=False)
        
        oci_dst_db_system_network_details = oci.psql.models.NetworkDetails(
            subnet_id = oci_dst_subnet_id
        )
        
        if oci_dst_db_bkp_retention_days == "":
            oci_dst_db_system_mgmt_details = oci.psql.models.ManagementPolicyDetails(
                maintenance_window_start = oci_dst_db_maintenance_window_start,
                backup_policy = oci.psql.models.DailyBackupPolicy(backup_start=oci_dst_db_bkp_start,kind=oci_dst_db_bkp_kind)
            )
        elif oci_dst_db_bkp_cp_compartment_id != "" and oci_dr_operation == "switchover":
            oci_dst_db_system_copy_policy = oci.psql.models.BackupCopyPolicy(
                compartment_id = oci_dst_db_bkp_cp_compartment_id,
                retention_period = oci_dst_db_bkp_retention_days,
                regions = [oci_src_region]
            )

            oci_dst_db_system_mgmt_details = oci.psql.models.ManagementPolicyDetails(
                maintenance_window_start = oci_dst_db_maintenance_window_start,
                backup_policy = oci.psql.models.DailyBackupPolicy(backup_start=oci_dst_db_bkp_start,retention_days=oci_dst_db_bkp_retention_days,kind=oci_dst_db_bkp_kind,copy_policy=oci_dst_db_system_copy_policy)
            )
        else:
            oci_dst_db_system_mgmt_details = oci.psql.models.ManagementPolicyDetails(
                maintenance_window_start = oci_dst_db_maintenance_window_start,
                backup_policy = oci.psql.models.DailyBackupPolicy(backup_start=oci_dst_db_bkp_start,retention_days=oci_dst_db_bkp_retention_days,kind=oci_dst_db_bkp_kind)
            )

        oci_dst_db_system_storage_details = oci.psql.models.OciOptimizedStorageDetails(
            system_type = oci_dst_db_system_type,
            is_regionally_durable = oci_dst_db_is_regionally_durable,
            iops = oci_dst_db_iops,
            availability_domain = oci_dst_ad
        )

        oci_dst_db_system_credentials = oci.psql.models.Credentials(
            username = oci_dst_db_username,
            password_details = oci.psql.models.VaultSecretPasswordDetails(password_type="VAULT_SECRET",secret_id=oci_dst_db_secret_id,secret_version="1")
        )

        if oci_dr_operation == "drill":
            oci_dst_db_display_name = data["psql_db_details"]["display_name"] + "_drill"

        # handle if oci_dst_db_config_id is empty
        if oci_dst_db_config_id:
            oci_dst_db_system_create_details = oci.psql.models.CreateDbSystemDetails(
                compartment_id = oci_dst_db_comp_id,
                db_version = oci_dst_db_version,
                config_id = oci_dst_db_config_id,
                display_name = oci_dst_db_display_name,
                instance_count = oci_dst_db_instance_count,
                instance_memory_size_in_gbs = oci_dst_db_memory_size,
                instance_ocpu_count = oci_dst_db_ocpu_count,
                shape = oci_dst_db_shape,
                network_details = oci_dst_db_system_network_details,
                management_policy = oci_dst_db_system_mgmt_details,
                credentials = oci_dst_db_system_credentials,
                storage_details = oci_dst_db_system_storage_details,
                source = oci_dst_db_system_bkp_source_details
            )
        else:
            oci_dst_db_system_create_details = oci.psql.models.CreateDbSystemDetails(
                compartment_id = oci_dst_db_comp_id,
                db_version = oci_dst_db_version,
                display_name = oci_dst_db_display_name,
                instance_count = oci_dst_db_instance_count,
                instance_memory_size_in_gbs = oci_dst_db_memory_size,
                instance_ocpu_count = oci_dst_db_ocpu_count,
                shape = oci_dst_db_shape,
                network_details = oci_dst_db_system_network_details,
                management_policy = oci_dst_db_system_mgmt_details,
                credentials = oci_dst_db_system_credentials,
                storage_details = oci_dst_db_system_storage_details,
                source = oci_dst_db_system_bkp_source_details            
            )

        #print(oci_dst_db_system_create_details)

        # Initiate restoration
        oci_dst_db_create_dbs = oci_dst_db_sys_clt.create_db_system(oci_dst_db_system_create_details)
        oci_dst_db_create_dbs_id = oci_dst_db_create_dbs.data.id
        oci_dst_db_create_dbs_get_rsp = oci_dst_db_sys_clt.get_db_system(oci_dst_db_create_dbs_id)

        if oci_dr_operation == "drill":
            logging.info(f"Drill Operation: Restore Last Backup in progress: {oci_dst_last_bkp_id} in region {oci_dst_region}")
        elif oci_dr_operation == "switchover":
            logging.info(f"Switchover Operation: Restore Last Backup in progress: {oci_dst_last_bkp_id} in region {oci_dst_region}")
        else:
            logging.info(f"Failover Operation: Restore Last Backup in progress: {oci_dst_last_bkp_id} in region {oci_dst_region}")

        # Wait for restoration to complete
        oci_dst_db_create_dbs_wait_active = oci.wait_until(
            oci_dst_db_sys_clt,
            oci_dst_db_create_dbs_get_rsp,
            'lifecycle_state',
            'ACTIVE',
            max_wait_seconds=oci_max_wait_seconds
        )

    except Exception as err:
        logging.error(f"{err}")
        os.remove(regions_file)
        logging.error(f"Failed to restore the Backup or No Backup found te be restored for PostgreSQL Database System {oci_src_db_system_id} in region {oci_dst_region}")
        sys.exit(1)

    # Update Configuration JSON file
    logging.info(f"Updating {config_file_name} file...")

    new_primary_region = oci_dst_region
    new_primary_subnet = oci_dst_subnet_id

    # Update values based on scenario
    if oci_dr_operation == "drill":
        data["psql_db_details"]["psql_db_to_terminate_id"] = oci_dst_db_create_dbs_id
        data["psql_db_details"]["psql_config_to_terminate_id"] = oci_dst_db_config_id
    elif oci_dr_operation == "switchover":
        old_psql_id = data["psql_db_details"]["id"]
        data["psql_db_details"]["id"] = oci_dst_db_create_dbs_id
        data["psql_db_details"]["psql_db_to_terminate_id"] = old_psql_id
        data["psql_db_details"]["psql_config_to_terminate_id"] = data["psql_db_details"]["primary_config_id"]
        data["psql_db_details"]["standby_region"] = data["psql_db_details"]["primary_region"]
        data["psql_db_details"]["primary_region"] = new_primary_region
        data["psql_db_details"]["standby_subnet_id"] = data["psql_db_details"]["primary_subnet_id"]
        data["psql_db_details"]["primary_subnet_id"] = new_primary_subnet
        data["psql_db_details"]["standby_admin_secrect_id"] = data["psql_db_details"]["primary_admin_secrect_id"]
        data["psql_db_details"]["primary_admin_secrect_id"] = oci_dst_db_secret_id
        data["psql_db_details"]["standby_config_id"] = data["psql_db_details"]["primary_config_id"]
        data["psql_db_details"]["primary_config_id"] = oci_dst_db_config_id

    else:
        data["psql_db_details"]["id"] = oci_dst_db_create_dbs_id
        data["psql_db_details"]["standby_region"] = data["psql_db_details"]["primary_region"]
        data["psql_db_details"]["primary_region"] = new_primary_region
        data["psql_db_details"]["standby_subnet_id"] = data["psql_db_details"]["primary_subnet_id"]
        data["psql_db_details"]["primary_subnet_id"] = new_primary_subnet
        data["psql_db_details"]["standby_admin_secrect_id"] = data["psql_db_details"]["primary_admin_secrect_id"]
        data["psql_db_details"]["primary_admin_secrect_id"] = oci_dst_db_secret_id
        data["psql_db_details"]["standby_config_id"] = data["psql_db_details"]["primary_config_id"]
        data["psql_db_details"]["primary_config_id"] = oci_dst_db_config_id

    update_file = psql_utils.update_config_file(config_file_name,data)
    if not update_file:
        os.remove(regions_file)
        logging.error(f"Failed to update {config_file_name}...")
        sys.exit(1)

    # Clean up temporary files
    os.remove(regions_file)
    if oci_dr_operation == "drill":
        logging.info(f"Drill Operation: Restore Last Backup for PostgreSQL Database System complete: {oci_dst_db_create_dbs_id} in region {oci_dst_region}")
        logging.info(f"To end the Drill, run the terminate script to delete this restored PostgreSQL Database System in region {oci_dst_region}")
    elif oci_dr_operation == "switchover":
        logging.info(f"Switchover Operation: Restore Last Backup for PostgreSQL Database System complete: {oci_dst_db_create_dbs_id} in region {oci_dst_region}")
        logging.info(f"Run the terminate script to delete the source PostgreSQL Database System in region {oci_src_region}")
    else:
        logging.info(f"Failover Operation: Restore Last Backup for PostgreSQL Database System complete: {oci_dst_db_create_dbs_id} in region {oci_dst_region}")

if __name__ == "__main__":
    psql_utils.print_cmd()
    restore_bkp()
