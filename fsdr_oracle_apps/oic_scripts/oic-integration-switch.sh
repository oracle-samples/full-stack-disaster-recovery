#!/bin/bash

##############################################################################################################################
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script is used to activate or deactivate integrations in OIC (Oracle Integration Cloud) instances in both Regions
# process during a switchover or failover orchestrated by Full Stack DR.
#
# You will have  to call oic-integration-switch.sh by passing parameters activate / deactivate
# and Region ID IAD/PHX uppercase
# ----
# Prerequisite
# ----
# Config file integrations.json should be updated automatically/manually to contain latest integration list
#
# ----
# Usage
# ----
# oic-integration-switch.sh <activate / deactivate> <region ID>
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
json_file="/home/opc/oic-scripts/integrations.json"

# OIC host
oic_host_region1="xxxxxxxxxxx"
oic_host_region2="xxxxxxxxxxx"



idcs_url=xxxxxxxxxxx

# Client Application Config
client_id_region1=xxxxxxxxxxx
scope_region1=xxxxxxxxxxx

client_id_region2=xxxxxxxxxxx
scope_region2=xxxxxxxxxxx

#vault information for extracting client secret
secret_ocid_region1=xxxxxxxxxxx
secret_ocid_region2=xxxxxxxxxxx

##############################################################################################################################


# Check if the region passed as an argument in the cmd line argument
if [ -z ${1} ] || ([ "${1}" != "activate" ] && [ "${1}" != "deactivate" ]); then
   echo "This script needs activate or deactivate as first argument. For example, activate to activate the integrations."
   echo "Usage: $0 <activate / deactivate> <region ID>"
   echo "Exiting......."
   exit 1
fi

if [ -z ${2} ]; then
   echo "This script needs an OCI Region code as a second argument. For example, IAD for ashburn and PHX for phoenix regions."
   echo "Usage: $0 <activate / deactivate> <region ID>"
   echo "Exiting......."
   exit 1
fi

regioncode=$2
actioncode=$1
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

if [ "$actioncode" == "activate" ]; then
        data='{"status":"ACTIVATED"}'
elif [ "$actioncode" == "deactivate" ]; then
         data='{"status":"CONFIGURED","stopScheduleForDeactivation":"true"}'
else
        echo "Valid first arguement is not provided. Exiting......."
        exit
fi


# Function to call the API and handle errors
activate_integration() {
  local integration_id="$1"
  local version="$2"
echo "Starting to ${actioncode} ${integration_id} ${version}"
  local api_url="${oic_host}/ic/api/integration/v1/integrations/${integration_id}%7C${version}"


 if response=$(curl -X POST -H "Authorization: Bearer ${access_token}" -H "Content-Type:application/json" -H "X-HTTP-Method-Override:PATCH" -d "${data}" "${api_url}"); then
          echo "Integration successfully ${actioncode}d. Response:"
          echo "$response"
     else
          echo "Error: Failed to make the POST request. Check the error message below:"
          echo "$response"
          exit 1
     fi
}

json=$(curl -s  --request POST "${idcs_url}/oauth2/v1/token" -H "Content-Type:application/x-www-form-urlencoded" -d "grant_type=client_credentials&client_id=${client_id}&client_secret=${client_secret}&scope=${scope}")
# Read access token from environment variable (replace with your secure storage method)
access_token=$(echo "$json" | jq -r '.access_token')

# Check ifaccess token is provied
if [[ -z "$access_token" ]]; then
  echo "Error: Unable to get the access token"
  exit 1
fi

# Check  JSON file exists
if [[ ! -f "$json_file" ]]; then
  echo "Error: JSON file '$json_file' not found."
  exit 1
fi

# Read integrations and versions from JSON securely

jq -c '.integrations[]' "$json_file" | while read integration; do
  # Extract integration name and version securely using jq
  integration_name=$(echo "$integration" | jq -r '.name')
  version=$(echo "$integration" | jq -r '.version')

  # Call the API for each integration and version
  activate_integration "$integration_name" "$version"
done

echo "Successfully called API for all integrations in the JSON file."
