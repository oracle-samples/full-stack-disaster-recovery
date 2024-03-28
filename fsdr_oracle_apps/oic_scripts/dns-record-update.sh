#!/bin/bash

##############################################################################################################################
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script is used to update the DNS Zone record
# during a switchover or failover orchestrated by Full Stack DR.
#
# You will have  to call dns_record_update.sh use Parameters Region ID IAD/PHX uppercase.
#
# ----
# Usage
# ----
# dns_record_update.sh <region ID>
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
#oic_instance_ocid_value
oic_instance_host_region1=xxxxxxxxxxx
oic_instance_host_region2=xxxxxxxxxxx
#DNS Zone Values
dns_region=IAD
zone_name=xxxxxxxxxxx
domain=xxxxxxxxxxx
r_type=CNAME
ttl=30
##############################################################################################################################

# Check if the option to create or update or delete passed as an argument in the cmd line argument
if [ -z ${1} ]; then
   echo "This script needs an OCI Region code as an argument. For example, IAD for ashburn and PHX for phoenix regions."
   echo "Usage: $0 {region_code}"
   echo "Exiting......."
   exit
fi

regioncode=$1

if [ "$region1" == "$regioncode" ]; then
        oic_instance_host=$oic_instance_host_region1
elif [ "$region2" == "$regioncode" ]; then
        oic_instance_host=$oic_instance_host_region2

else
        echo "Valid oci region code is not provided. Exiting......."
        exit
fi
oci dns record rrset update --profile $dns_region --zone-name-or-id $zone_name --domain $domain --rtype $r_type --items '[{"domain":"'${domain}'","rdata":"'${oic_instance_host}'","rtype":"'${r_type}'","ttl":'${ttl}'}]' --force
