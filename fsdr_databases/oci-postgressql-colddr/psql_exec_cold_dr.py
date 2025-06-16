#!/usr/bin/env -S python3 -x
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# Example script written by Antoun Moubarak, Cloud Architecture Specialist

import oci
import argparse
import os
import subprocess

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='This script acts as a control wrapper for executing specific OCI Disaster Recovery operation scripts such as switchover, failover, and drill.')
parser.add_argument("-c", "--config-file", required=True, help="Specify the JSON configuration file.")
parser.add_argument("dest_ad_number", nargs='?', const=1, default=1, help="Destination Availability Domain Number (Default value is 1 for AD1)", type=int)
parser.add_argument("-o", "--operation", help="Specify the operation type to execute. Default operation is drill (Dry Run).", choices=['drill', 'switchover', 'failover','terminate'], type = str, default = "drill")
parser.add_argument("-t", "--timeout", help = "Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.", type = int, default = 1200)
args = parser.parse_args()

# Extracting arguments
config_file_name = args.config_file
oci_dst_ad_number = str(args.dest_ad_number)
oci_max_wait_seconds = str(args.timeout)
oci_dr_operation = args.operation

# For generating the Regions file for the authentication
# Get the current directory of the script and the script name
current_directory = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.splitext(os.path.basename(__file__))[0]
base_config_file_name = os.path.basename(config_file_name)
config_file = current_directory + "/config/" + base_config_file_name

create_backup = current_directory + "/psql_create_bkp.py"
copy_backup = current_directory + "/psql_copy_bkp.py"
copy_config = current_directory + "/psql_copy_config.py"
restore_backup = current_directory + "/psql_restore_bkp.py"
terminate_db = current_directory + "/psql_terminate_db.py"

if oci_dr_operation == "switchover" or oci_dr_operation == "drill":
    cmd = ["python3", create_backup, "-c", config_file, "-t", oci_max_wait_seconds]
    result = subprocess.run(cmd)

    if result.returncode == 0:
        cmd = ["python3", copy_config, "-c", config_file, "-t", oci_max_wait_seconds]
        result = subprocess.run(cmd)

        if result.returncode == 0:
            cmd = ["python3", copy_backup, "-c", config_file, "-t", oci_max_wait_seconds]
            result = subprocess.run(cmd)

            if result.returncode == 0:
                cmd = ["python3", restore_backup, "-c", config_file, "-o", oci_dr_operation, oci_dst_ad_number, "-t", oci_max_wait_seconds]
                result = subprocess.run(cmd)

elif oci_dr_operation == "failover":
    cmd = ["python3", restore_backup, "-c", config_file, "-o", oci_dr_operation, oci_dst_ad_number, "-t", oci_max_wait_seconds]
    result = subprocess.run(cmd)

elif oci_dr_operation == "terminate":
    cmd = ["python3", terminate_db, "-c", config_file, "-t", oci_max_wait_seconds]
    result = subprocess.run(cmd)