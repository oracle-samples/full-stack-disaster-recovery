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

# Parsing Arguments
parser = argparse.ArgumentParser(description='Copy MySQL DB backup to another OCI region')
parser.add_argument("db_source_label", help="System Label of the Source MySQL system to be copied. System Label from the config file", type=str)
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
    oci_src_bkp_comp_id = row[2]
    oci_dst_bkp_comp_id = row[2]
    oci_dst_region = row[4].split('.')[3]
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
regions_file=current_directory + "/regions_copy." + time.strftime("%Y%m%d%H%M%S")
regions = open(regions_file,"w")
regions.write("[SOURCE]\n")
regions.write("region = " + oci_src_region + "\n")
regions.write("[DESTINATION]\n")
regions.write("region = " + oci_dst_region + "\n")
regions.close()

oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
oci_src_config = oci.config.from_file(file_location=regions_file,profile_name="SOURCE")
oci_dst_config = oci.config.from_file(file_location=regions_file,profile_name="DESTINATION")

try:
  # Get DB system details
  oci_src_db_sys_clt = oci.mysql.DbSystemClient(config = oci_src_config, signer = oci_signer)
  oci_src_db_sys_details = oci_src_db_sys_clt.get_db_system(oci_src_db_system_id)
except:
  os.remove(regions_file)
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Error retrieving DB system details! Check the config file.\n")
  sys.exit(1)

try:
  # Get a list of DB System backups
  oci_src_db_bkp_clt = oci.mysql.DbBackupsClient(config = oci_src_config, signer = oci_signer)
  oci_src_db_bkp_lst = oci_src_db_bkp_clt.list_backups(compartment_id = oci_src_bkp_comp_id, lifecycle_state = "ACTIVE", db_system_id = oci_src_db_system_id, sort_by = "timeUpdated", sort_order = "DESC")

  # Last Updated backup ID
  oci_src_last_bkp_id = oci_src_db_bkp_lst.data[0].id
  oci_src_last_bkp_name = oci_src_db_bkp_lst.data[0].display_name

  if oci_src_db_sys_details.data.is_heat_wave_cluster_attached is True:
    oci_src_db_sys_heat_details = oci_src_db_sys_clt.get_heat_wave_cluster(oci_src_db_system_id)
    oci_src_heat_clus_size = oci_src_db_sys_heat_details.data.cluster_size
    oci_src_heat_clus_shape = oci_src_db_sys_heat_details.data.shape_name
    oci_src_bkp_cp_details = oci.mysql.models.CopyBackupDetails(compartment_id = oci_dst_bkp_comp_id, display_name = oci_src_last_bkp_name + " from " + oci_src_region, source_backup_id = oci_src_last_bkp_id, source_region = oci_src_region, description = "Source Backup : " + oci_src_last_bkp_id + " copied from " + oci_src_region + " region. oci_src_heat=YES oci_src_heat_clus_size=" + str(oci_src_heat_clus_size) + " oci_src_heat_clus_shape=" + oci_src_heat_clus_shape)
  else:
    oci_src_bkp_cp_details = oci.mysql.models.CopyBackupDetails(compartment_id = oci_dst_bkp_comp_id, display_name = oci_src_last_bkp_name + " from " + oci_src_region, source_backup_id = oci_src_last_bkp_id, source_region = oci_src_region, description = 'Source Backup : ' + oci_src_last_bkp_id + ' copied from ' + oci_src_region + ' region. oci_src_heat=NO')

  # Copy Last Backup to Destination
  oci_dst_db_bkp_clt = oci.mysql.DbBackupsClient(config = oci_dst_config, signer = oci_signer)

  try:
    # OCI Previous ACTIVE Copied Backup
    oci_dst_prv_bkp_rsp = oci_dst_db_bkp_clt.list_backups(compartment_id = oci_src_bkp_comp_id, db_system_id = oci_src_db_system_id, lifecycle_state = "ACTIVE", sort_by = "timeUpdated", sort_order = "DESC")
    oci_dst_prv_last_bkp_id = oci_dst_prv_bkp_rsp.data[0].id
    oci_dst_prv_last_bkp_details = oci_dst_db_bkp_clt.get_backup(oci_dst_prv_last_bkp_id)
    oci_dst_prv_last_bkp_orig_source = oci_dst_prv_last_bkp_details.data.original_source_backup_id

    if oci_dst_prv_last_bkp_orig_source != oci_src_last_bkp_id:
      oci_dst_db_bkp_copy = oci_dst_db_bkp_clt.copy_backup(copy_backup_details = oci_src_bkp_cp_details)
      oci_dst_db_bkp_copy_id = oci_dst_db_bkp_copy.data.id
      oci_dst_db_bkp_get_rsp = oci_dst_db_bkp_clt.get_backup(oci_dst_db_bkp_copy_id)
      print("")
      print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Copy Last Backup in progress : " + oci_src_last_bkp_id)

      oci_dst_db_bkp_copy_wait_active = oci.wait_until(oci_dst_db_bkp_clt, oci_dst_db_bkp_get_rsp, 'lifecycle_state', 'ACTIVE')
    else:
      print("")
      print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Last Backup already copied : " + oci_src_last_bkp_id)
  except:
    print("")
    print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - No Previous Backup found!")
    oci_dst_db_bkp_copy = oci_dst_db_bkp_clt.copy_backup(copy_backup_details = oci_src_bkp_cp_details)
    oci_dst_db_bkp_copy_id = oci_dst_db_bkp_copy.data.id
    oci_dst_db_bkp_get_rsp = oci_dst_db_bkp_clt.get_backup(oci_dst_db_bkp_copy_id)
    print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Copy Last Backup in progress : " + oci_src_last_bkp_id)
    oci_dst_db_bkp_copy_wait_active = oci.wait_until(oci_dst_db_bkp_clt, oci_dst_db_bkp_get_rsp, 'lifecycle_state', 'ACTIVE')
except:
  os.remove(regions_file)
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Error copying backup remote region : " + oci_dst_region + "\n")
  sys.exit(1)

os.remove(regions_file)
print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Copy Last Backup complete : " + oci_src_last_bkp_id + "\n")
