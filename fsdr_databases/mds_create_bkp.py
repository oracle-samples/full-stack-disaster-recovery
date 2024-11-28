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
import time
from datetime import timezone 
import datetime 
import config

# Parsing Arguments
parser = argparse.ArgumentParser(description='Create a Manual MySQL DB backup')
parser.add_argument("db_source_label", help="System Label of the Source MySQL system. System Label from the config file", type=str)
args = parser.parse_args()
oci_src_db_system_label = args.db_source_label

current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Finding system details from the config file
mds_data = config.mdsdata
mds_head = config.mdshead

i = len(mds_data)

for x in range(i):
  if mds_data[x][0] == oci_src_db_system_label:
    oci_src_db_system_id = mds_data[x][1]
    oci_src_bkp_comp_id = mds_data[x][2]
    break

try:
  oci_src_db_system_id
except:
  print("MDS Label not found! Check the config file.")
  sys.exit(1)

try:
  oci_src_region = oci_src_db_system_id.split('.')[3]
except:
  print("MDS OCID : Bad Format!")
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
  print("Error retrieving DB system details!")
  print("Check the provided arguments...")
  sys.exit(1)

try:
  # Create Manual Backup
  oci_src_db_bkp_clt = oci.mysql.DbBackupsClient(config = oci_src_config, signer = oci_signer)
  
  dt = datetime.datetime.now(timezone.utc)

  oci_src_db_bkp_details = oci.mysql.models.CreateBackupDetails(display_name = oci_src_db_sys_details.data.display_name + ' Manual Backup ' + str(dt) , backup_type = 'INCREMENTAL', db_system_id = oci_src_db_system_id, description = oci_src_db_sys_details.data.display_name + ' Manual Backup ' + str(dt), retention_in_days = 7)

  oci_src_db_bkp_create = oci_src_db_bkp_clt.create_backup(create_backup_details = oci_src_db_bkp_details)
  oci_src_db_bkp_create_id = oci_src_db_bkp_create.data.id
  oci_src_db_bkp_get_rsp = oci_src_db_bkp_clt.get_backup(oci_src_db_bkp_create_id)
  print("Backup in progress for DB system: " + oci_src_db_sys_details.data.display_name)
  oci_src_db_bkp_create_wait_active = oci.wait_until(oci_src_db_bkp_clt, oci_src_db_bkp_get_rsp, 'lifecycle_state', 'ACTIVE')
except:
  os.remove(regions_file)
  print("Error during backup!")
  print("Check the provided arguments...")
  sys.exit(1)

os.remove(regions_file)
