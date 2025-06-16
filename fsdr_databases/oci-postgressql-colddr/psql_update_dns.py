#!/usr/bin/env -S python3 -x
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# Example script written by Antoun Moubarak, Cloud Architecture Specialist

import oci
import argparse
import os
import sys
import logging
from datetime import timezone
import psql_utils

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Update a DNS record for the MDS Endpoint')
parser.add_argument("-c", "--config-file", required=True, help="Specify the JSON configuration file.")
parser.add_argument("-d", "--domain_name", required=True, help="The DNS record to be updated", type=str)
parser.add_argument("-o", "--operation", help="Specify the operation type to execute. Default operation is startdrill (Dry Run).", choices=['startdrill', 'stopdrill','switchover', 'failover'], type = str, default = "startdrill")
parser.add_argument("-t", "--ttl", help="Specify the TTL in seconds for the DNS record. Default to 300 seconds.", type=int, default=300)
args = parser.parse_args()

# Extract arguments
config_file_name = args.config_file
oci_domain_name = args.domain_name
ttl = args.ttl
oci_dr_operation = args.operation

# For generating the Regions file for the authentication
# Get the current directory of the script and the script name
current_directory = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.splitext(os.path.basename(__file__))[0]
# Get the base name of the config ficurrent directory of the script
base_config_file_name = os.path.basename(config_file_name).split('.')[0]
config_file = current_directory + "/config/" + os.path.basename(config_file_name)

# Configure logging
logfilename = psql_utils.config_logging(current_directory,base_config_file_name)

logging.info(args)

def update_dns():
    # Read the configuration file
    data = psql_utils.read_config_file(config_file)

    # Extract region and DNS view details based on the scenario
    if oci_dr_operation == "startdrill":
        oci_src_db_system_id = data["psql_db_details"]["psql_db_to_terminate_id"]
        oci_src_region = data["psql_db_details"]["standby_region"]
        oci_dst_region = data["psql_db_details"]["standby_region"]
        for index, item in enumerate(data["dns_details"]["regions"]):
            if item["region"] == data["psql_db_details"]["standby_region"]:
                dns_src_zone_id = data["dns_details"]["regions"][index]["dns_zone_id"]
    else:
        oci_src_db_system_id = data["psql_db_details"]["id"]
        oci_src_region = data["psql_db_details"]["primary_region"]
        oci_dst_region = data["psql_db_details"]["standby_region"]
        for index, item in enumerate(data["dns_details"]["regions"]):
            if item["region"] == data["psql_db_details"]["primary_region"]:
                dns_src_zone_id = data["dns_details"]["regions"][index]["dns_zone_id"]
            elif item["region"] == data["psql_db_details"]["standby_region"]:
                dns_dst_zone_id = data["dns_details"]["regions"][index]["dns_zone_id"]

    # Prepare a temporary regions file for OCI SDK configuration
    regions_file = psql_utils.prepare_regions_file(oci_src_region,oci_dst_region,current_directory,base_config_file_name,script_name)
    
    # Set up OCI signer and configurations
    oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    oci_src_config = oci.config.from_file(file_location=regions_file, profile_name="SOURCE")
    oci_dst_config = oci.config.from_file(file_location=regions_file, profile_name="DESTINATION")
    oci_src_db_system_client = oci.psql.PostgresqlClient(config=oci_src_config, signer=oci_signer)

    # Retrieve DB system details
    oci_src_db_sys_details = psql_utils.get_db_system_details(oci_src_db_system_id,oci_src_db_system_client)

    #print(oci_src_db_sys_details.data)

    if not oci_src_db_sys_details:
        os.remove(regions_file)
        logging.error(f"Failed to retrieve PostgreSQL Database System details: {oci_src_db_system_id}")
        sys.exit(1)

    # Prepare DNS record update details
    update_domain_records = [
        oci.dns.models.RecordDetails(
            domain=oci_domain_name,
            rtype='A',
            ttl=ttl,
            rdata=oci_src_db_sys_details.data.network_details.primary_db_endpoint_private_ip
        )
    ]

    # Update DNS record in the source region
    if oci_dr_operation != "stopdrill":
        logging.info(f"Updating DNS record {oci_domain_name} with IP {oci_src_db_sys_details.data.network_details.primary_db_endpoint_private_ip} in region {oci_src_region}")
        oci_src_dns_client = oci.dns.DnsClient(config=oci_src_config, signer=oci_signer)
        oci_src_dns_client.update_domain_records(
            dns_src_zone_id,
            oci_domain_name,
            oci.dns.models.UpdateDomainRecordsDetails(items=update_domain_records)
        )
    else:
        logging.info(f"Updating DNS record {oci_domain_name} with IP {oci_src_db_sys_details.data.network_details.primary_db_endpoint_private_ip} in region {oci_dst_region}")
        oci_dst_dns_client = oci.dns.DnsClient(config=oci_dst_config, signer=oci_signer)
        oci_dst_dns_client.update_domain_records(
            dns_dst_zone_id,
            oci_domain_name,
            oci.dns.models.UpdateDomainRecordsDetails(items=update_domain_records)
        )


    # If switch is specified, update DNS record in the destination region
    if oci_dr_operation == "switchover":
        logging.info(f"Updating DNS record {oci_domain_name} with IP {oci_src_db_sys_details.data.network_details.primary_db_endpoint_private_ip} in region {oci_dst_region}")
        oci_dst_dns_client = oci.dns.DnsClient(config=oci_dst_config, signer=oci_signer)
        oci_dst_dns_client.update_domain_records(
            dns_dst_zone_id,
            oci_domain_name,
            oci.dns.models.UpdateDomainRecordsDetails(items=update_domain_records)
        )

    # Clean up temporary regions file
    os.remove(regions_file)
    logging.info(f"Update DNS record {oci_domain_name} with target {oci_src_db_sys_details.data.network_details.primary_db_endpoint_private_ip} completed successfully.")

if __name__ == "__main__":
    psql_utils.print_cmd()
    update_dns()
