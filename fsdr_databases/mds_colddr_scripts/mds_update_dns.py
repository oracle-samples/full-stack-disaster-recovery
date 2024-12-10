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
parser = argparse.ArgumentParser(description='Update a DNS record for the MDS Endpoint')
parser.add_argument("mds_label", help="System Label of the MySQL to get the Endpoint IP", type=str)
parser.add_argument("zone_name", help="The DNS Zone Name", type=str)
parser.add_argument("domain_name", help="The DNS record to be updated", type=str)
parser.add_argument("--remote", action='store_true', help="Update DNS in the Remote Region as well (Only for Switchover Scenario)")
args = parser.parse_args()
oci_src_db_system_label = args.mds_label
oci_zone_name = args.zone_name
oci_domain_name = args.domain_name

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
    oci_dst_region = row[4].split('.')[3]
    oci_src_view_id = row[5]
    oci_dst_view_id = row[6]
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

if oci_src_region == oci_dst_region:
  print("")
  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Local and Remote regions are the same! Review the config file...\n")
  sys.exit(1)

#if view_id_region1.split('.')[3] == oci_dst_region:
#  dst_view_id=view_id_region1
#  src_view_id=view_id_region2
#elif view_id_region2.split('.')[3] == oci_dst_region:
#  dst_view_id=view_id_region2
#  src_view_id=view_id_region1
#else:
#  print("")
#  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - Wrong Remote OCI Region for DNS update!!\n")
#  sys.exit(1)

# Preparing regions file for source and destination
regions_file=current_directory + "/regions_dns." + time.strftime("%Y%m%d%H%M%S")
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

#if oci_src_db_sys_details.data.lifecycle_state != "ACTIVE":
#  os.remove(regions_file)
#  print("")
#  print(time.strftime("%Y-%m-%d %H-%M-%S") + " FAILURE - MDS is not active in region " + oci_src_region + "\n")
#  sys.exit(1)

update_domain_records = [
    oci.dns.models.RecordDetails(
        domain=oci_domain_name,
        rtype='A',
        ttl=30,
        rdata=oci_src_db_sys_details.data.ip_address
    )
]

print("")
print(time.strftime("%Y%-m%-d %H-%M-%S") + " INFO - Updating DNS record " + oci_domain_name + " with IP " +oci_src_db_sys_details.data.ip_address + " in region " + oci_src_region + "\n")
oci_src_dns_client = oci.dns.DnsClient(config = oci_src_config, signer = oci_signer)
oci_src_dns_client.update_domain_records(
    oci_zone_name,
    oci_domain_name,
    oci.dns.models.UpdateDomainRecordsDetails(items=update_domain_records),
    view_id=oci_src_view_id
)

if args.remote is True:
  print(time.strftime("%Y%-m%-d %H-%M-%S") + " INFO - Updating DNS record " + oci_domain_name + " with IP " +oci_src_db_sys_details.data.ip_address + " in region " + oci_dst_region + "\n")
  oci_dst_dns_client = oci.dns.DnsClient(config = oci_dst_config, signer = oci_signer)
  oci_dst_dns_client.update_domain_records(
      oci_zone_name,
      oci_domain_name,
      oci.dns.models.UpdateDomainRecordsDetails(items=update_domain_records),
      view_id=oci_dst_view_id
  )

os.remove(regions_file)
