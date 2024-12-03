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
import config

# Parsing Arguments
parser = argparse.ArgumentParser(description='Update a DNS record for the MDS Endpoint')
parser.add_argument("mds_label", help="System Label of the MySQL to get the Endpoint IP", type=str)
parser.add_argument("zone_name", help="The DNS Zone Name", type=str)
parser.add_argument("domain_name", help="The DNS record to be updated", type=str)
parser.add_argument("remote_region", help="Remote OCI Region (Old Primary)", type=str)
parser.add_argument("--remote", action='store_true', help="Update DNS in the Remote Region as well (Only for Switchover Scenario)")
args = parser.parse_args()
oci_src_db_system_label = args.mds_label
oci_zone_name = args.zone_name
oci_domain_name = args.domain_name
oci_dst_region = args.remote_region

current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Finding system details from the config file
mds_data = config.mdsdata
mds_head = config.mdshead

i = len(mds_data)

for x in range(i):
  if mds_data[x][0] == oci_src_db_system_label:
    oci_src_db_system_id = mds_data[x][1]
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

if oci_src_region == oci_dst_region:
  print("Local and Remote regions are the same! Review the command arguments or the config file...")
  sys.exit(1)

if config.view_id[0].split('.')[3] == oci_dst_region:
  dst_view_id=config.view_id[0]
  src_view_id=config.view_id[1]
elif config.view_id[1].split('.')[3] == oci_dst_region:
  dst_view_id=config.view_id[1]
  src_view_id=config.view_id[0]
else:
  print("Wrong Remote OCI Region for DNS update!!")
  sys.exit(1)

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
  print("Error retrieving DB system details! Check the config file.")
  sys.exit(1)

if oci_src_db_sys_details.data.lifecycle_state != "ACTIVE":
  print("MDS is not active")
  sys.exit(1)

update_domain_records = [
    oci.dns.models.RecordDetails(
        domain=oci_domain_name,
        rtype='A',
        ttl=30,
        rdata=oci_src_db_sys_details.data.ip_address
    )
]

oci_src_dns_client = oci.dns.DnsClient(config = oci_src_config, signer = oci_signer)
oci_src_dns_client.update_domain_records(
    oci_zone_name,
    oci_domain_name,
    oci.dns.models.UpdateDomainRecordsDetails(items=update_domain_records),
    view_id=src_view_id
)

if args.remote is True:
  oci_dst_dns_client = oci.dns.DnsClient(config = oci_dst_config, signer = oci_signer)
  oci_dst_dns_client.update_domain_records(
      oci_zone_name,
      oci_domain_name,
      oci.dns.models.UpdateDomainRecordsDetails(items=update_domain_records),
      view_id=dst_view_id
  )

os.remove(regions_file)
