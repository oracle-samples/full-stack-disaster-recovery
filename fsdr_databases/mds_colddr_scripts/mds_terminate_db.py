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

# Parsing Arguments
parser = argparse.ArgumentParser(description='Terminate MySQL DB')
parser.add_argument("db_source_label", help="System Label of the MySQL DB system. System Label from the config file", type=str)
#group = parser.add_mutually_exclusive_group()
#group.add_argument("--source", action='store_true', help="Terminate Source MySQL DB after a Restore (Switchover scenario)")
#group.add_argument("--drill", action='store_true', help="Terminate Target MySQL DB after a Restore (Dry Run scenario)")
args = parser.parse_args()
oci_src_db_system_label = args.db_source_label

#if not (args.source or args.drill):
#  parser.error('No action requested, add --source or --drill')

current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Finding system details from the config file
config_file_name = current_directory + "/config.csv"

# Read the data from the config file
with open(config_file_name, mode='r', newline='') as file:
  reader = csv.reader(file)
  rows = [row for row in reader]

# Search for the MySQL Label
for row in rows:
  if row[0] == oci_src_db_system_label:
    to_terminate_ocid = row[7]

try:
  to_terminate_ocid
except:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILIRE - MySQL OCID not found in file the config file.\n")
  sys.exit(1)

try:
  oci_src_region = to_terminate_ocid.split('.')[3]
except:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILIRE - MDS OCID : Bad Format!\n")
  sys.exit(1)

# Preparing regions file for source and destination
regions_file=current_directory + "/regions_terminate." + time.strftime("%Y%m%d%H%M%S")
regions = open(regions_file,"w")
regions.write("[SOURCE]\n")
regions.write("region = " + oci_src_region + "\n")
regions.close()

oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
oci_src_config = oci.config.from_file(file_location=regions_file,profile_name="SOURCE")

try:
  # Get DB system details
  oci_src_db_sys_clt = oci.mysql.DbSystemClient(config = oci_src_config, signer = oci_signer)
  oci_src_db_sys_details = oci_src_db_sys_clt.get_db_system(to_terminate_ocid)
except:
  os.remove(regions_file)
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILIRE - Error retrieving DB system details " + to_terminate_ocid)
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILIRE - Check the provided arguments...\n")
  sys.exit(1)

try:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Terminating MySQL DB System in progress : " + to_terminate_ocid)
  oci_src_db_sys_dbs_terminate = oci_src_db_sys_clt.delete_db_system(to_terminate_ocid)
  oci_src_db_sys_dbs_get_rsp = oci_src_db_sys_clt.get_db_system(to_terminate_ocid)
  oci_src_db_sys_dbs_wait_terminate = oci.wait_until(oci_src_db_sys_clt, oci_src_db_sys_dbs_get_rsp, 'lifecycle_state', 'DELETED')
except:
  os.remove(regions_file)
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILIRE - Error Terminating MySQL DB System : " +  to_terminate_ocid + "\n")
  sys.exit(1)

print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Updating config file...")
with open(config_file_name, mode='r', newline='') as file:
  reader = csv.reader(file)
  rows = [row for row in reader]

# Modify the specific value
for row in rows:
  if row[0] == oci_src_db_system_label:
    row[7] = ""
    break

# Write the modified data back to the file
with open(config_file_name, mode='w', newline='') as file:
  writer = csv.writer(file)
  writer.writerows(rows)

os.remove(regions_file)
print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Terminating MySQL DB System complete : " + to_terminate_ocid + "\n")
