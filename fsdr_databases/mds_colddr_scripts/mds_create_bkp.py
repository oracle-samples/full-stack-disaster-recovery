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

# Parsing Arguments
parser = argparse.ArgumentParser(description='Create a Manual MySQL DB backup')
parser.add_argument("db_source_label", help="System Label of the Source MySQL system. System Label from the config file", type=str)
parser.add_argument("--stop", action='store_true', help="Stop the Source MySQL DB before the Backup (Switchover scenario ONLY)")
args = parser.parse_args()
oci_src_db_system_label = args.db_source_label

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
    oci_src_db_system_id = row[1]
    oci_dst_db_comp_id = row[2]
    break

try:
  oci_src_db_system_id
except:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - MDS Label not found! Check the config file.\n")
  sys.exit(1)

try:
  oci_src_region = oci_src_db_system_id.split('.')[3]
except:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - MDS OCID : Bad Format!\n")
  sys.exit(1)

# Preparing regions file for source and destination
regions_file=current_directory + "/regions_createbkp." + time.strftime("%Y%m%d%H%M%S")
regions = open(regions_file,"w")
regions.write("[SOURCE]\n")
regions.write("region = " + oci_src_region + "\n")
regions.close()

oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
oci_src_config = oci.config.from_file(file_location=regions_file,profile_name="SOURCE")

try:
  # Get DB system details
  oci_src_db_sys_clt = oci.mysql.DbSystemClient(config = oci_src_config, signer = oci_signer)
  oci_src_db_sys_details = oci_src_db_sys_clt.get_db_system(oci_src_db_system_id)

except:
  os.remove(regions_file)
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Error retrieving DB system details!")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Check the provided arguments...")
  sys.exit(1)

if args.stop is True:
  oci_src_db_sys_stop_details = oci.mysql.models.StopDbSystemDetails(shutdown_type="FAST")
  oci_src_db_sys_stop = oci_src_db_sys_clt.stop_db_system(oci_src_db_system_id,oci_src_db_sys_stop_details)
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Stop MySQL DB System in progress : " + oci_src_db_sys_details.data.id)
  oci_src_db_sys_stop_get_rsp = oci_src_db_sys_clt.get_db_system(oci_src_db_system_id)
  oci_src_db_sys_stop_wait_inactive = oci.wait_until(oci_src_db_sys_clt, oci_src_db_sys_stop_get_rsp, 'lifecycle_state', 'INACTIVE')
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Stop MySQL DB System complete : " + oci_src_db_sys_details.data.id)

try:
  # Create Manual Backup
  oci_src_db_bkp_clt = oci.mysql.DbBackupsClient(config = oci_src_config, signer = oci_signer)
  
  dt = datetime.datetime.now(timezone.utc)

  oci_src_db_bkp_details = oci.mysql.models.CreateBackupDetails(display_name = oci_src_db_sys_details.data.display_name + ' Manual Backup ' + str(dt) , backup_type = 'INCREMENTAL', db_system_id = oci_src_db_system_id, description = oci_src_db_sys_details.data.display_name + ' Manual Backup ' + str(dt), retention_in_days = 7)

  oci_src_db_bkp_create = oci_src_db_bkp_clt.create_backup(create_backup_details = oci_src_db_bkp_details)
  oci_src_db_bkp_create_id = oci_src_db_bkp_create.data.id
  oci_src_db_bkp_get_rsp = oci_src_db_bkp_clt.get_backup(oci_src_db_bkp_create_id)
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Backup MySQL DB System in progress : " + oci_src_db_sys_details.data.id)
  oci_src_db_bkp_create_wait_active = oci.wait_until(oci_src_db_bkp_clt, oci_src_db_bkp_get_rsp, 'lifecycle_state', 'ACTIVE')
except:
  os.remove(regions_file)
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - ERROR during backup!")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Check the provided arguments...")
  sys.exit(1)

os.remove(regions_file)
print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Backup MySQL DB System complete : " + oci_src_db_sys_details.data.id + "\n")
