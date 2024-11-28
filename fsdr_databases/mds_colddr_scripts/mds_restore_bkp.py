#!/usr/bin/python -x
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
parser = argparse.ArgumentParser(description='Restore MySQL DB backup to another OCI region')
parser.add_argument("db_source_label", help="System Label of the Source MySQL system to be restored. System Label from the config file", type=str)
parser.add_argument("dest_subnet_id", help="Destination Subnet OCID", type=str)
parser.add_argument("dest_ad_number", nargs='?', const=1, default=1, help="Destination Availability Domain Number", type=int)
parser.add_argument("--config", action='store_true', help="Update config file with the new OCID of the restored MDS")
parser.add_argument("--terminate", action='store_true', help="Terminate the Source MDS after a Restore (Switchover scenario)")
args = parser.parse_args()
oci_src_db_system_label = args.db_source_label
oci_dst_subnet_id = args.dest_subnet_id
oci_dst_ad_number = args.dest_ad_number

#current_directory = os.getcwd()
current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
config_file = current_directory + "/config.py"

if oci_dst_ad_number not in [1, 2, 3]:
  print("Wrong AD number provided!.")
  sys.exit(1)

# Finding system details from the config file
mds_data = config.mdsdata
mds_head = config.mdshead

i = len(mds_data)

for x in range(i):
  if mds_data[x][0] == oci_src_db_system_label:
    oci_src_db_system_id=mds_data[x][1]
    oci_dst_db_comp_id = mds_data[x][2]
    oci_dst_bkp_comp_id = mds_data[x][2]
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

try:
  oci_dst_region = oci_dst_subnet_id.split('.')[3]
except:
  print("Destination Subnet : Bad Format!")
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
  print("Error geting the AD details in the destintion Region!")
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
    print("Unable to get if source DB has HeatWave enabled..")
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

  print("Restoring Last Backup id : " + oci_dst_last_bkp_id)

  oci_dst_db_create_dbs_wait_active = oci.wait_until(oci_dst_db_restore_clt, oci_dst_db_create_dbs_get_rsp, 'lifecycle_state', 'ACTIVE')

  if add_heat == 1:
    oci_dst_db_restore_clt.add_heat_wave_cluster(db_system_id=oci_dst_db_create_dbs_id,add_heat_wave_cluster_details=oci_dst_heat_details)

except:
  os.remove(regions_file)
  print("Error Restoring the Backup or No Backup found te be restored for MDS " + oci_src_db_system_id + " in region " + oci_dst_region + "!.")
  sys.exit(1)

if args.terminate is True:
  print("Terminating Source DB System...")
  oci_src_db_sys_dbs_terminate = oci_src_db_sys_clt.delete_db_system(oci_src_db_system_id)
  oci_src_db_sys_dbs_get_rsp = oci_src_db_sys_clt.get_db_system(oci_src_db_system_id)
  oci_src_db_sys_dbs_wait_terminate = oci.wait_until(oci_src_db_sys_clt, oci_src_db_sys_dbs_get_rsp, 'lifecycle_state', 'DELETED')

if args.config is True:
  print("Updating config file...")
  old_mds_ocid = oci_src_db_system_id
  new_mds_ocid = oci_dst_db_create_dbs_id

  with open(config_file, 'r') as file:
    data = file.read()
    data = data.replace(old_mds_ocid, new_mds_ocid)

  with open(config_file, 'w') as file:
    file.write(data)

os.remove(regions_file)
