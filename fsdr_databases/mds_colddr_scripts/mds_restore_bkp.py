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
parser = argparse.ArgumentParser(description='Restore MySQL DB backup to another OCI region')
parser.add_argument("db_source_label", help="System Label of the Source MySQL system to be restored. System Label from the config file", type=str)
parser.add_argument("dest_ad_number", nargs='?', const=1, default=1, help="Destination Availability Domain Number", type=int)
parser.add_argument("--config", action='store_true', help="Update config file with the new OCID of the restored MySQL DB System")
group = parser.add_mutually_exclusive_group()
group.add_argument("--switch", action='store_true', help="TAG the Source MySQL DB to be terminated after a Restore (Switchover scenario)")
group.add_argument("--drill", action='store_true', help="TAG the Target MySQL DB to be terminated after a Restore (Dry Run scenario)")
args = parser.parse_args()
oci_src_db_system_label = args.db_source_label
oci_dst_ad_number = args.dest_ad_number

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
    oci_dst_bkp_comp_id = row[2]
    oci_src_subnet_id = row[3]
    oci_dst_subnet_id = row[4]
    break

if args.switch and not args.config:
    parser.error('--config argument is required with --switch')
if args.drill and not args.config:
    parser.error('--config argument is required with --drill')

if oci_dst_ad_number not in [1, 2, 3]:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Wrong AD number provided!\n")
  sys.exit(1)

try:
  oci_src_db_system_id
except:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - MySQL DB System Label not found! Check the config file.\n")
  sys.exit(1)

try:
  oci_src_region = oci_src_db_system_id.split('.')[3]
except:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - MySQL DB System OCID : Bad Format!\n")
  sys.exit(1)

try:
  oci_dst_region = oci_dst_subnet_id.split('.')[3]
except:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Destination Subnet : Bad Format!\n")
  sys.exit(1)

# Preparing regions file for source and destination
regions_file=current_directory + "/regions_restore." + time.strftime("%Y%m%d%H%M%S")
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
  oci_dst_identity_client = oci.identity.IdentityClient(config = oci_dst_config, signer = oci_signer)
  oci_dst_ad_list = oci_dst_identity_client.list_availability_domains(compartment_id=oci_dst_db_comp_id)
  oci_dst_ad = oci_dst_ad_list.data[oci_dst_ad_number-1].name
except:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Error geting the AD details in the destintion Region!\n")
  sys.exit(1)

try:
  try:
    # Get DB system details
    oci_src_db_sys_clt = oci.mysql.DbSystemClient(config = oci_src_config, signer = oci_signer)
    oci_src_db_sys_details = oci_src_db_sys_clt.get_db_system(oci_src_db_system_id)

    if oci_src_db_sys_details.data.is_heat_wave_cluster_attached is True:
      oci_src_db_sys_heat_details = oci_src_db_sys_clt.get_heat_wave_cluster(oci_src_db_system_id)
      add_heat=1
      oci_src_heat_clus_size = oci_src_db_sys_heat_details.data.cluster_size
      oci_src_heat_clus_shape = oci_src_db_sys_heat_details.data.shape_name
      oci_dst_heat_details = oci.mysql.models.AddHeatWaveClusterDetails(cluster_size = oci_src_heat_clus_size,shape_name=oci_src_heat_clus_shape)
    else:
      add_heat=0
  except:
    print("")
    print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Unable to get if source DB has HeatWave enabled.\n")
    add_heat=0

  # Get a list of DB System backups
  oci_dst_db_bkp_clt = oci.mysql.DbBackupsClient(config = oci_dst_config, signer = oci_signer)
  oci_dst_db_bkp_lst = oci_dst_db_bkp_clt.list_backups(compartment_id = oci_dst_db_comp_id, lifecycle_state = "ACTIVE", db_system_id = oci_src_db_system_id, sort_by = "timeUpdated", sort_order = "DESC")
  oci_dst_last_bkp_id = oci_dst_db_bkp_lst.data[0].id
  oci_dst_last_bkp_name = oci_dst_db_bkp_lst.data[0].display_name
  oci_dst_last_bkp_db_details = oci_dst_db_bkp_clt.get_backup(oci_dst_last_bkp_id)
  oci_dst_last_db_name = oci_dst_last_bkp_db_details.data.db_system_snapshot.display_name
  oci_dst_last_bkp_db_name = oci_dst_last_db_name
  oci_dst_shape = oci_dst_last_bkp_db_details.data.db_system_snapshot.shape_name

  oci_dst_db_restore_model = oci.mysql.models.CreateDbSystemSourceFromBackupDetails(backup_id=oci_dst_last_bkp_id,source_type="BACKUP")
  oci_dst_db_create_dbsystem_details = oci.mysql.models.CreateDbSystemDetails(availability_domain=oci_dst_ad, compartment_id=oci_dst_db_comp_id,source=oci_dst_db_restore_model,display_name=oci_dst_last_bkp_db_name,subnet_id=oci_dst_subnet_id, shape_name=oci_dst_shape, description="Restored from backup : " + oci_dst_last_bkp_name + " of DB system " + oci_dst_last_db_name + ". Backup ID: " + oci_dst_last_bkp_id)
  oci_dst_db_restore_clt = oci.mysql.DbSystemClient(config = oci_dst_config, signer = oci_signer)

  oci_dst_db_create_dbs = oci_dst_db_restore_clt.create_db_system(oci_dst_db_create_dbsystem_details)
  oci_dst_db_create_dbs_id = oci_dst_db_create_dbs.data.id
  oci_dst_db_create_dbs_get_rsp = oci_dst_db_restore_clt.get_db_system(oci_dst_db_create_dbs_id)

  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Restore Last Backup in progress : " + oci_dst_last_bkp_id)

  oci_dst_db_create_dbs_wait_active = oci.wait_until(oci_dst_db_restore_clt, oci_dst_db_create_dbs_get_rsp, 'lifecycle_state', 'ACTIVE')

  if add_heat == 1:
    oci_dst_db_restore_clt.add_heat_wave_cluster(db_system_id=oci_dst_db_create_dbs_id,add_heat_wave_cluster_details=oci_dst_heat_details)

except:
  os.remove(regions_file)
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Error Restoring the Backup or No Backup found te be restored for MySQL DB System " + oci_src_db_system_id + " in region " + oci_dst_region + "\n")
  sys.exit(1)

if args.config is True:
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Updating config file...")
  with open(config_file_name, mode='r', newline='') as file:
    reader = csv.reader(file)
    rows = [row for row in reader]

# Modify the specific value 
  for row in rows:
    if row[0] == oci_src_db_system_label:
      new_primary_subnet = row[4]
      row[4] = row[3]
      row[3] = new_primary_subnet
      new_primary_dns_view = row[6]
      row[6] = row[5]
      row[5] = new_primary_dns_view
      break

  if args.switch is True:
    old_mds_id = row[1]
    row[1] = oci_dst_db_create_dbs_id
    row[7] = old_mds_id
  elif args.drill is True:
    row[1] = oci_dst_db_create_dbs_id
    row[7] = oci_dst_db_create_dbs_id
  else:
    row[1] = oci_dst_db_create_dbs_id

# Write the modified data back to the file 
  with open(config_file_name, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(rows)

os.remove(regions_file)
print(time.strftime("%Y-%m-%d %H-%M-%S") + " INFO - Restore Last Backup MySQL DB System complete: " + oci_dst_db_create_dbs_id + "\n")
