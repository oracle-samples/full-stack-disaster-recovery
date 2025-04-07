#!/usr/bin/python -x
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# Example script written by Antoun Moubarak, Cloud Architecture Specialist

import oci
import argparse
import json
import os
import sys
import time
import logging

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Update a DNS record for a HeatWave MySQL Database System.')
parser.add_argument("-c", "--config-file", required=True, help="Specify the JSON configuration file.")
parser.add_argument("-r", "--region", required=True, help="Specify the Region Identifier from the config file.")
parser.add_argument("-d", "--dns-name", required=True, help="Specify the DNS Name to update.")
parser.add_argument("-g", "--target", required=True, help="Specify the DNS Target value.")
parser.add_argument("-t", "--rtype", required=True, help="Specify the DNS Record type. Defaults CNAME.", type=str)
parser.add_argument("-T", "--ttl", help="Specify the TTL in seconds for the DNS record. Defaults to 300 seconds.", type=int, default=300)
args = parser.parse_args()

# Extract parsed arguments
config_file_name = args.config_file
oci_region = args.region
dns_name = args.dns_name
target = args.target
ttl = args.ttl
rtype = args.rtype

# Get the current directory of the script
current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Configure logging
logfilename = current_directory + "/logs/disaster_recovery.log"
logging.basicConfig(
    handlers=[
        logging.FileHandler(logfilename,'a'),
        logging.StreamHandler()
    ],
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logging.info(args)

def print_cmd():
    command = sys.argv[0]
    arguments = sys.argv[1:]
    logging.info(f"Executing the following command {command} with arguments {arguments}")

def prepare_regions_file(oci_region):
    regions_file = current_directory + "/" + os.path.basename(config_file_name).split('.')[0] + "_" + oci_region + "_update_dns." + time.strftime("%Y%m%d%H%M%S")
    with open(regions_file, "w") as regions:
        regions.write("[REGION]\n")
        regions.write("region = " + oci_region + "\n")
    return regions_file

def read_config_file(config_file_name):
    # Opening JSON file
    config_file = open(config_file_name)

    # returns JSON object as a dictionary
    data = json.load(config_file)
    
    # Closing file
    config_file.close()
    return data

def find_region_in_config(data, oci_region):
    # Iterating through the replicas list
    for index, item in enumerate(data["dns_details"]["regions"]):
        if item["region"] == oci_region:
            return index
    return -1

def update_dns():
    # Read the configuration file
    data = read_config_file(config_file_name)

    # Find Replica details from the config file
    index = find_region_in_config(data, oci_region)
    if index == -1:
        logging.error(f"Region {oci_region} not found in {config_file_name} file.")
        sys.exit(1)

    dns_zone_id = data["dns_details"]["regions"][index]["dns_zone_id"]

    # Prepare a temporary regions file for OCI SDK configuration
    region_file = prepare_regions_file(oci_region)

    # Set up OCI signer and configuration
    oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    oci_region_config = oci.config.from_file(file_location=region_file, profile_name="REGION")

    # Prepare DNS record update details
    update_domain_records = [
        oci.dns.models.RecordDetails(
            domain=dns_name,
            rtype=rtype,
            ttl=ttl,
            rdata=target
        )
    ]

    try:
        oci_dns_client = oci.dns.DnsClient(config=oci_region_config, signer=oci_signer)
        oci_dns_client.update_rr_set(
            dns_zone_id,
            dns_name,
            rtype=rtype,
            update_rr_set_details=oci.dns.models.UpdateRRSetDetails(items=update_domain_records),
        )
    except Exception as err:
        logging.error(f"{err}")
        os.remove(region_file)
        sys.exit(1)

    # Clean up temporary regions file
    os.remove(region_file)
    logging.info(f"Update DNS record {dns_name} with target {target} completed successfully in region {oci_region}.")

if __name__ == "__main__":
    print_cmd()
    update_dns()