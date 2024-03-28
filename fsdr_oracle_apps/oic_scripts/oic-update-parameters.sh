#!/bin/bash

##############################################################################################################################
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script is used to update the scheduled parameters of OIC integrations for OIC (Oracle Integration Cloud) instances in both Regions
# process during a switchover or failover orchestrated by Full Stack DR.
#
# You will have  to call oic-update-parameters.sh use Region ID IAD/PHX uppercase 
#
# ----
# Prerequisite
# ----
# Config file integration_parameters.json should be updated automatically/manually to contain latest scheduled parameters
#
# ----
# Usage
# ----
# oic-update-parameters.sh <region ID>
# 
# ----
# How to add this script to Full Stack DR plans
# ----
# You need to create one Plan Group for each switchover or failover plan in the
# DR protection group at both regions. The script needs to be installed on the movable
# compute instance you added as a member of the DR protection group. The script can be
# installed in the same directory you install the OIC scripts
#
##############################################################################################################################
#oic_instanes_region_keys
region1=IAD
region2=PHX


# Replace with the path to your JSON file containing integration name, version and corresponding scheduled parameters
json_file="/home/opc/oic-scripts/integration_parameters.json"

# OIC host
oic_host_region1="https://oic-iad-maasoftdev-ia.integration.ocp.oraclecloud.com"
oic_host_region2="https://oic-phx-maasoftdev-px.integration.ocp.oraclecloud.com"



idcs_url=https://idcs-2eba0c47bf18468db4173a88032cc558.identity.oraclecloud.com

# Client Application Config
client_id_region1=75702769e1654e78bd54fc2ba808992a
scope_region1=https://D8884B50ABCD4FFE8AFE5255A0121DA9.integration.ocp.oraclecloud.com:443urn:opc:resource:consumer::all

client_id_region2=81106edb276a4abbaee8b90794acde12
scope_region2=https://CA6B9454C8644D47A3F8C4C4850B361D.integration.ocp.oraclecloud.com:443urn:opc:resource:consumer::all

#vault information for extracting client secret
secret_ocid_region1=ocid1.vaultsecret.oc1.iad.amaaaaaahmwiikaal2e4wp6tujtjebblgzfxxd66tkltmr7x6okynfpq6jhq
secret_ocid_region2=ocid1.vaultsecret.oc1.phx.amaaaaaahmwiikaarguseptq6bcljgdhy5bxgextcde4ndm3czaljrcum23a

##############################################################################################################################


# Check if the region passed as an argument in the cmd line argument
if [ -z ${1} ]; then
   echo "This script needs an OCI Region code as a second argument. For example, IAD for ashburn and PHX for phoenix regions."
   echo "Usage: $0 {region_code}"
   echo "Exiting......."
   exit 1
fi

regioncode=$1

if [ "$region1" == "$regioncode" ]; then
        region=$region1
        oic_host=$oic_host_region1
        client_id=$client_id_region1
        scope=$scope_region1
        client_secret=$(oci secrets secret-bundle get --profile ${region1} --raw-output --secret-id "${secret_ocid_region1}" --query "data.\"secret-bundle-content\".content" | base64 -d)
elif [ "$region2" == "$regioncode" ]; then
        region=$region2
        oic_host=$oic_host_region2
        client_id=$client_id_region2
        scope=$scope_region2
        client_secret=$(oci secrets secret-bundle get --profile ${region2} --raw-output --secret-id "${secret_ocid_region2}" --query "data.\"secret-bundle-content\".content" | base64 -d)
else
        echo "Valid oci region code is not provided. Exiting......."
        exit
fi
# Function to call the API and handle errors
updated_scheduled_integration() {
  local integration_id="$1"
  local version="$2"
  local parameters="$3"


echo "Updating Scheduled parameters for ${integration_id} ${version}"
  local api_url="${oic_host}/ic/api/integration/v1/integrations/${integration_id}%7C${version}/schedule/parameters"

 
formatted_parameters=$(echo "$parameters" | jq -c .)
data="{\"parameters\":${formatted_parameters}}"


 if response=$(curl -X PATCH -H "Authorization: Bearer ${ACCESS_TOKEN}" -H "Content-Type:application/json"  -d "${data}" "${api_url}" ); then
          echo "Activation was successful. Response:"
          echo "$response"
     else
          echo "Error: Failed to make the POST request. Check the error message below:"
          echo "$response"
          exit 1
     fi
}


#Generation Access token
json=$(curl -s  --request POST "${idcs_url}/oauth2/v1/token" -H "Content-Type:application/x-www-form-urlencoded" -d "grant_type=client_credentials&client_id=${client_id}&client_secret=${client_secret}&scope=${scope}")
#Extracting access token from the response of api
ACCESS_TOKEN=$(echo "$json" | jq -r '.access_token')

# Check if access token is extracted
if [[ -z "$ACCESS_TOKEN" ]]; then
  echo "Error: Unable to get the access token"
  exit 1
fi

# Check  JSON file exists
if [[ ! -f "$json_file" ]]; then
  echo "Error: JSON file '$json_file' not found."
  exit 1
fi

# Read integrations and scheduled parameters from JSON securely



jq -c '.integrations[]' "$json_file" | while read integration; do
  # Extract integration name and version and parameters  securely using jq
  integration_name=$(echo "$integration" | jq -r '.name')
  version=$(echo "$integration" | jq -r '.version')
  parameters=$(echo "$integration" | jq -r '.parameters')
  # Call the API for each integration and version
  updated_scheduled_integration "$integration_name" "$version" "$parameters"
done

echo "Successfully Updated Scheduled parameters for all integrations in the JSON file."
