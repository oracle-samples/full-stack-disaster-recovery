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
parser = argparse.ArgumentParser(description='Terminate a MySQL DB system.')
parser.add_argument("db_source_label", help="System Label of the MySQL DB system from the config file.", type=str)
parser.add_argument("--force", action='store_true', help="Force termination even if delete protection is enabled.")
parser.add_argument("--skip", action='store_true', help="Skip final backup before deletion.")
parser.add_argument("-t", "--timeout", help = "Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.", type = int, default = 1200)
args = parser.parse_args()

# Extract arguments
oci_src_db_system_label = args.db_source_label
oci_max_wait_seconds = args.timeout

# Get the current script directory
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
        to_terminate_ocid = row[df.columns.get_loc("MYSQL_DB_TO_TERMINATE")]
        oci_src_region = row[df.columns.get_loc("STANDBY_REGION")]
        break

if not to_terminate_ocid:
    print(f"\n{datetime.datetime.now(timezone.utc)} FAILURE - MySQL OCID not found in the config file.\n")
    sys.exit(1)

# Prepare the regions file for OCI SDK configuration
regions_file = current_directory + "/regions_terminate_db." + time.strftime("%Y%m%d%H%M%S")
with open(regions_file, "w") as regions:
    regions.write("[SOURCE]\n")
    regions.write(f"region = {oci_src_region}\n")

# Set up OCI signer and configuration
oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
oci_src_config = oci.config.from_file(file_location=regions_file, profile_name="SOURCE")

try:
    # Initialize the MySQL DB system client
    oci_src_db_sys_clt = oci.mysql.DbSystemClient(config=oci_src_config, signer=oci_signer)

    # Retrieve details of the DB system to be terminated
    oci_src_db_sys_details = oci_src_db_sys_clt.get_db_system(to_terminate_ocid)
except Exception as e:
    print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
    os.remove(regions_file)
    print(f"\n{datetime.datetime.now(timezone.utc)} FAILURE - Error retrieving DB system details for OCID {to_terminate_ocid}")
    sys.exit(1)
    
# Handle force termination (disable delete protection if enabled)
if args.force:
    if oci_src_db_sys_details.data.deletion_policy.is_delete_protected:
        oci_src_deletion_policy_details = oci.mysql.models.UpdateDeletionPolicyDetails(is_delete_protected=False)
        oci_src_db_sys_update_details = oci.mysql.models.UpdateDbSystemDetails(deletion_policy=oci_src_deletion_policy_details)
        oci_src_db_sys_clt.update_db_system(db_system_id=to_terminate_ocid, update_db_system_details=oci_src_db_sys_update_details)

# Handle skipping the final backup
if args.skip:
    if oci_src_db_sys_details.data.deletion_policy.is_delete_protected:
        oci_src_deletion_policy_details = oci.mysql.models.UpdateDeletionPolicyDetails(final_backup="SKIP_FINAL_BACKUP")
        oci_src_db_sys_update_details = oci.mysql.models.UpdateDbSystemDetails(deletion_policy=oci_src_deletion_policy_details)
        oci_src_db_sys_clt.update_db_system(db_system_id=to_terminate_ocid, update_db_system_details=oci_src_db_sys_update_details)

try:
    # Initiate the termination of the MySQL DB system
    print(f"\n{datetime.datetime.now(timezone.utc)} INFO - Terminating MySQL DB System: {to_terminate_ocid}")
    oci_src_db_sys_clt.delete_db_system(to_terminate_ocid)

    # Wait for the termination process to complete
    oci_src_db_sys_dbs_get_rsp = oci_src_db_sys_clt.get_db_system(to_terminate_ocid)
    oci.wait_until(oci_src_db_sys_clt, oci_src_db_sys_dbs_get_rsp, 'lifecycle_state', 'DELETED', max_wait_seconds=oci_max_wait_seconds)
except Exception as e:
    print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
    os.remove(regions_file)
    print(f"\n{datetime.datetime.now(timezone.utc)} FAILURE - Error terminating MySQL DB System: {to_terminate_ocid}")
    sys.exit(1)

# Update the configuration file to reflect the deletion - Reopen because Headers were excluded
print(f"{datetime.datetime.now(timezone.utc)} INFO - Updating configuration file...")
with open(config_file_name, mode='r', newline='') as file:
    reader = csv.reader(file)
    rows = [row for row in reader]

# Modify the specific value
df = pandas.read_csv(config_file_name, header=0)
for row in rows:
    if row[df.columns.get_loc("MYSQL_DB_LABEL")] == oci_src_db_system_label:
        row[df.columns.get_loc("MYSQL_DB_TO_TERMINATE")] = ""
        break

# Write the updated configuration back to the file
with open(config_file_name, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(rows)

# Clean up temporary regions file
os.remove(regions_file)
print(f"{datetime.datetime.now(timezone.utc)} INFO - Termination of MySQL DB System complete: {to_terminate_ocid}\n")
