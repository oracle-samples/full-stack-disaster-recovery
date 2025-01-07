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
import pandas

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Update a DNS record for the MDS Endpoint')
parser.add_argument("mds_label", help="System Label of the MySQL to get the Endpoint IP", type=str)
parser.add_argument("zone_name", help="The DNS Zone Name", type=str)
parser.add_argument("domain_name", help="The DNS record to be updated", type=str)
group = parser.add_mutually_exclusive_group()
group.add_argument("--switch", action='store_true', help="Update DNS in the Source and Remote Region as well (Only for Switchover Scenario)")
group.add_argument("--drill", action='store_true', help="Update DNS in the Remote Region Only (Only for Dry Run Scenario)")
args = parser.parse_args()

# Extract arguments
oci_src_db_system_label = args.mds_label
oci_zone_name = args.zone_name
oci_domain_name = args.domain_name

# Get the current directory of the script
current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Config file containing system details
config_file_name = current_directory + "/config.csv"

# Read the data from the config file
# The config file is expected to have headers and contain details about various MySQL DB systems.
with open(config_file_name, mode='r', newline='') as file:
    reader = csv.reader(file)
    next(reader, None)  # Skip the headers
    rows = [row for row in reader]

# Use pandas to search for the MySQL DB label in the config file
df = pandas.read_csv(config_file_name, header=0)

# Extract region and DNS view details based on the scenario
if args.drill:
    for row in rows:
        if row[df.columns.get_loc("MYSQL_DB_LABEL")] == oci_src_db_system_label:
            oci_src_db_system_id = row[df.columns.get_loc("MYSQL_DB_TO_TERMINATE")]
            oci_src_region = row[df.columns.get_loc("STANDBY_REGION")]
            oci_dst_region = row[df.columns.get_loc("PRIMARY_REGION")]
            oci_src_view_id = row[df.columns.get_loc("STANDBY_DNS_VIEW_OCID")]
            oci_dst_view_id = row[df.columns.get_loc("PRIMARY_DNS_VIEW_OCID")]
            break
else:
    for row in rows:
        if row[df.columns.get_loc("MYSQL_DB_LABEL")] == oci_src_db_system_label:
            oci_src_db_system_id = row[df.columns.get_loc("MYSQL_DB_OCID")]
            oci_src_region = row[df.columns.get_loc("PRIMARY_REGION")]
            oci_dst_region = row[df.columns.get_loc("STANDBY_REGION")]
            oci_src_view_id = row[df.columns.get_loc("PRIMARY_DNS_VIEW_OCID")]
            oci_dst_view_id = row[df.columns.get_loc("STANDBY_DNS_VIEW_OCID")]
            break

# Validate extracted details
try:
    oci_src_db_system_id
except NameError:
    print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: MySQL DB Label not found! Check the config file.")
    sys.exit(1)

if oci_src_region == oci_dst_region:
    print(f"\n{datetime.datetime.now(timezone.utc)} FAILURE - Local and Remote regions are the same! Review the config file...")
    sys.exit(1)

# Prepare a temporary regions file for OCI SDK configuration
regions_file = current_directory + "/regions_update_dns." + time.strftime("%Y%m%d%H%M%S")
with open(regions_file, "w") as regions:
    regions.write("[SOURCE]\n")
    regions.write(f"region = {oci_src_region}\n")
    regions.write("[DESTINATION]\n")
    regions.write(f"region = {oci_dst_region}\n")
    
# Set up OCI signer and configurations
oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
oci_src_config = oci.config.from_file(file_location=regions_file, profile_name="SOURCE")
oci_dst_config = oci.config.from_file(file_location=regions_file, profile_name="DESTINATION")

try:
    # Retrieve DB system details
    oci_src_db_sys_clt = oci.mysql.DbSystemClient(config=oci_src_config, signer=oci_signer)
    oci_src_db_sys_details = oci_src_db_sys_clt.get_db_system(oci_src_db_system_id)
except Exception as e:
    print(f"\n{datetime.datetime.now(timezone.utc)} ERROR: {e}")
    os.remove(regions_file)
    print(f"\n{datetime.datetime.now(timezone.utc)} FAILURE - Error retrieving DB system details! Check the config file.")
    sys.exit(1)

# Prepare DNS record update details
update_domain_records = [
    oci.dns.models.RecordDetails(
        domain=oci_domain_name,
        rtype='A',
        ttl=30,
        rdata=oci_src_db_sys_details.data.ip_address
    )
]

# Update DNS record in the source region
print(f"\n{datetime.datetime.now(timezone.utc)} INFO - Updating DNS record {oci_domain_name} with IP {oci_src_db_sys_details.data.ip_address} in region {oci_src_region}\n")
oci_src_dns_client = oci.dns.DnsClient(config=oci_src_config, signer=oci_signer)
oci_src_dns_client.update_domain_records(
    oci_zone_name,
    oci_domain_name,
    oci.dns.models.UpdateDomainRecordsDetails(items=update_domain_records),
    view_id=oci_src_view_id
)

# If switch is specified, update DNS record in the destination region
if args.switch:
    print(f"{datetime.datetime.now(timezone.utc)} INFO - Updating DNS record {oci_domain_name} with IP {oci_src_db_sys_details.data.ip_address} in region {oci_dst_region}\n")
    oci_dst_dns_client = oci.dns.DnsClient(config=oci_dst_config, signer=oci_signer)
    oci_dst_dns_client.update_domain_records(
        oci_zone_name,
        oci_domain_name,
        oci.dns.models.UpdateDomainRecordsDetails(items=update_domain_records),
        view_id=oci_dst_view_id
    )

# Clean up temporary regions file
os.remove(regions_file)
