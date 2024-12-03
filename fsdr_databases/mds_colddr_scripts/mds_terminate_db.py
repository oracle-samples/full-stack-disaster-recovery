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
import time
import config

# Parsing Arguments
parser = argparse.ArgumentParser(description='Terminate MySQL DB')
group = parser.add_mutually_exclusive_group()
group.add_argument("--source", action='store_true', help="Terminate Source MySQL DB after a Restore (Switchover scenario)")
group.add_argument("--drill", action='store_true', help="Terminate Target MySQL DB after a Restore (Dry Run scenario)")
args = parser.parse_args()

current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

if args.source is True:
  to_terminate_file = current_directory + "/source"

if args.drill is True:
  to_terminate_file = current_directory + "/drill"

if os.path.isfile(to_terminate_file) is False:
  print(to_terminate_file + " Not found!")
  sys.exit(1)

to_terminate = open(to_terminate_file,"r")

try:
  to_terminate_ocid_read = to_terminate.read()
  to_terminate_ocid = to_terminate_ocid_read.replace('\n', '')
except:
  print("MySQL OCID not found in file: " + to_terminate_file + " !")
  sys.exit(1)

try:
  oci_src_region = to_terminate_ocid.split('.')[3]
except:
  print("MDS OCID : Bad Format!")
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
  print("Error retrieving DB system details " + to_terminate_ocid + " !")
  print("Check the provided arguments...")
  sys.exit(1)

try:
  print("Terminating DB System: " + to_terminate_ocid)
  oci_src_db_sys_dbs_terminate = oci_src_db_sys_clt.delete_db_system(to_terminate_ocid)
  oci_src_db_sys_dbs_get_rsp = oci_src_db_sys_clt.get_db_system(to_terminate_ocid)
  oci_src_db_sys_dbs_wait_terminate = oci.wait_until(oci_src_db_sys_clt, oci_src_db_sys_dbs_get_rsp, 'lifecycle_state', 'DELETED')
except:
  os.remove(regions_file)
  print("Error Terminating MySQL DB " +  to_terminate_ocid + " !")
  sys.exit(1)

os.remove(regions_file)
os.remove(to_terminate_file)
print("Terminating MySQL DB " + to_terminate_ocid + " Complete!")
