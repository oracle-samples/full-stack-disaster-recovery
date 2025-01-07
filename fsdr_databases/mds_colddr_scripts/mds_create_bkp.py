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
parser = argparse.ArgumentParser(description='Create a Manual MySQL DB backup')
parser.add_argument("db_source_label", help="System Label of the Source MySQL system. System Label from the config file", type=str)
parser.add_argument("--stop", action='store_true', help="Stop the Source MySQL DB before the Backup (Switchover scenario ONLY)")
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
    next(reader, None)  # Skip the headers
    rows = [row for row in reader]

# Use pandas to search for the MySQL DB label in the config file
df = pandas.read_csv(config_file_name, header=0)
for row in rows:
    if row[df.columns.get_loc("MYSQL_DB_LABEL")] == oci_src_db_system_label:
        oci_src_db_system_id = row[df.columns.get_loc("MYSQL_DB_OCID")]
        oci_dst_db_comp_id = row[df.columns.get_loc("COMPARTMENT_OCID")]
        oci_src_region = row[df.columns.get_loc("PRIMARY_REGION")]
        break

# Verify that the MySQL DB label was found
try:
    oci_src_db_system_id
except NameError:
    print("\n{datetime.datetime.now(timezone.utc)} ERROR: MySQL DB Label not found! Check the config file.")
    sys.exit(1)

# Prepare a temporary regions file for OCI SDK configuration
regions_file = current_directory + "/regions_create_bkp." + time.strftime("%Y%m%d%H%M%S")
with open(regions_file, "w") as regions:
    regions.write("[SOURCE]\n")
    regions.write("region = " + oci_src_region + "\n")

# Set up OCI signer and configuration
oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
oci_src_config = oci.config.from_file(file_location=regions_file, profile_name="SOURCE")

try:
    # Initialize the DB System client and fetch DB system details
    oci_src_db_sys_clt = oci.mysql.DbSystemClient(config=oci_src_config, signer=oci_signer)
    oci_src_db_sys_details = oci_src_db_sys_clt.get_db_system(oci_src_db_system_id)
except Exception as e:
    print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
    os.remove(regions_file)
    print("\n{datetime.datetime.now(timezone.utc)} FAILURE: Error retrieving DB system details! Check the config file.")
    sys.exit(1)

# Stop the MySQL DB system if the --stop argument is provided
if args.stop:
    try:
        oci_src_db_sys_stop_details = oci.mysql.models.StopDbSystemDetails(shutdown_type="FAST")
        oci_src_db_sys_stop = oci_src_db_sys_clt.stop_db_system(oci_src_db_system_id, oci_src_db_sys_stop_details)
        print(f"\n{datetime.datetime.now(timezone.utc)} INFO: Stopping MySQL DB System: {oci_src_db_sys_details.data.id}")

        # Wait for the DB system to reach the INACTIVE state
        oci_src_db_sys_stop_get_rsp = oci_src_db_sys_clt.get_db_system(oci_src_db_system_id)
        oci_src_db_sys_stop_wait_inactive = oci.wait_until(
            oci_src_db_sys_clt, oci_src_db_sys_stop_get_rsp, 'lifecycle_state', 'INACTIVE', max_wait_seconds=oci_max_wait_seconds
        )
        print(f"{datetime.datetime.now(timezone.utc)} INFO: MySQL DB System stopped: {oci_src_db_sys_details.data.id}")
    except Exception as e:
        print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
        os.remove(regions_file)
        sys.exit(1)

try:
    # Create a manual backup of the MySQL DB system
    oci_src_db_bkp_clt = oci.mysql.DbBackupsClient(config=oci_src_config, signer=oci_signer)

    # Get the current timestamp
    dt = datetime.datetime.now(timezone.utc)

    # Define backup details
    oci_src_db_bkp_details = oci.mysql.models.CreateBackupDetails(
        display_name=f"{oci_src_db_sys_details.data.display_name} Manual Backup {dt}",
        backup_type='INCREMENTAL',
        db_system_id=oci_src_db_system_id,
        description=f"{oci_src_db_sys_details.data.display_name} Manual Backup {dt}",
        retention_in_days=oci_src_db_sys_details.data.backup_policy.retention_in_days
    )

    # Trigger the backup creation
    oci_src_db_bkp_create = oci_src_db_bkp_clt.create_backup(create_backup_details=oci_src_db_bkp_details)
    oci_src_db_bkp_create_id = oci_src_db_bkp_create.data.id
    oci_src_db_bkp_get_rsp = oci_src_db_bkp_clt.get_backup(oci_src_db_bkp_create_id)
    print(f"\n{datetime.datetime.now(timezone.utc)} INFO: Backup in progress for MySQL DB System: {oci_src_db_sys_details.data.id}")

    # Wait for the backup to become ACTIVE
    oci_src_db_bkp_create_wait_active = oci.wait_until(
        oci_src_db_bkp_clt, oci_src_db_bkp_get_rsp, 'lifecycle_state', 'ACTIVE', max_wait_seconds=oci_max_wait_seconds
    )
    print(f"{datetime.datetime.now(timezone.utc)} INFO: Backup completed for MySQL DB System: {oci_src_db_sys_details.data.id}")
except Exception as e:
    print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
    os.remove(regions_file)
    print("\n{datetime.datetime.now(timezone.utc)} FAILURE: Error during backup creation. Check the provided arguments.")
    sys.exit(1)

# Clean up temporary regions file
os.remove(regions_file)
print(f"{datetime.datetime.now(timezone.utc)} INFO: Backup process completed successfully for MySQL DB System: {oci_src_db_sys_details.data.id}\n")
