#!/bin/bash

##############################################################################################################################
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script Resume or Pause OIC (Oracle Integration Cloud) instances in the both Regions
# process during a switchover or failover orchestrated by Full Stack DR.
#
# You will have  to call oic-start-stop.sh use Parameters start/stop lowercase 
# and Region ID IAD/PHX uppercase.
#
# ----
# Usage
# ----
# oic-start-stop.sh <start/stop> <region ID>
# 
# ----
# How to add this script to Full Stack DR plans
# ----
# You need to create one Plan Group for each switchover or failover plan in the
# DR protection group at both regions. The script needs to be installed on the movable
# compute instance you added as a member of the DR protection group. The script can be
# installed in the same directory you install the OIC scripts
#
# ----
# Examples
# ----
# Add following plan group to switchover & failover DR plans at PHX Viceversa
#
# Plan Group: Start OIC Instance on PHX (Standby)
#   Plan step 1: Run oic-start-stop script at PHX
#   Local script: /WheverYouPutTheScript/oic-start-stop.sh start PHX
#   User: opc
#
# Add following plan group to switchover & failover DR plans at IAD Viceversa
#
# Plan Group: Stop OIC Instance on IAD (Primary)
#   Plan step 1: Run oic-start-stop script at IAD
#   Local script: /WheverYouPutTheScript/oic-start-stop.sh stop IAD
#   User: opc
##############################################################################################################################

#oic_instanes_region_keys
region1=IAD
region2=PHX

#oic_instance_ocid_value
oic_instance_ocid_region1=xxxxxxxxx
oic_instance_ocid_region2=xxxxxxxxx

##############################################################################################################################

# Stop OIC Instance
stop_oic()
{
oci integration integration-instance stop --id $oic_instance_ocid --max-wait-seconds 1200 --wait-for-state SUCCEEDED --wait-interval-seconds 30 --profile $region| jq . > status.json
}

# Start OIC Instance
start_oic()
{
oci integration integration-instance start --id $oic_instance_ocid --max-wait-seconds 1200 --wait-for-state SUCCEEDED --wait-interval-seconds 30 --profile $region| jq . > status.json
}

# Check the status of the operation
check_status()
{
status=`jq .data.status status.json |sed -rn 's/(")([^"]+)(.*)/\2/p'`

if [ "$status" == "SUCCEEDED" ]; then
   echo ""
   echo "OIC instance operation is successfully completed."
else
   echo ""
   echo "OIC instance operation failed."
fi

# Cleanup the status.json file
rm -rf status.json
}

# Check if the option to create or update or delete passed as an argument in the cmd line argument
if [ -z ${1} ]; then
   echo "This script needs start|stop as a first argument."
   echo "Usage: $0 {start|stop} {region_code}"
   echo "Exiting......."
   exit
fi

if [ -z ${2} ]; then
   echo "This script needs an OCI Region code as a second argument. For example, IAD for ashburn and PHX for phoenix regions."
   echo "Usage: $0 {start|stop} {region_code}"
   echo "Exiting......."
   exit
fi

regioncode=$2

if [ "$region1" == "$regioncode" ]; then
        region=$region1
        oic_instance_ocid=$oic_instance_ocid_region1
elif [ "$region2" == "$regioncode" ]; then
        region=$region2
        oic_instance_ocid=$oic_instance_ocid_region2

else
        echo "Valid oci region code is not provided. Exiting......."
        exit
fi

# Check if the Integration Instance OCID provided or not.
if [ -z "$oic_instance_ocid" ]
then
    echo "Integration Instance ID not provided, exiting..."
        echo "Provide a valid ocid value of the Integration instance and run the script."
        exit
fi

echo "$1ing the OIC instance in the OCI region $2."

# Create log files directory
logDir=$PWD/logs

createLogsDir()
{
 if [ ! -d "$logDir" ]
  then
  mkdir $logDir
 fi
}

createLogsDir

echo "Log files created at $logDir."

# redirect stdout/stderr to a file
exec > "$logDir/start_stop_oic_$(date +"%Y%m%d_T%H%M%S").log" 2>&1

echo "-------------------------------------------------------------"
echo "  OIC instance operation selected is $1 for region $2."
echo "-------------------------------------------------------------"
echo ""

# Check the Option and perform the required operation
case "$1" in
  start)
    start_oic
    check_status
  ;;
  stop)
    stop_oic
    check_status
  ;;
  *)
  echo "Usage: $0 {start|stop} {region_code}"
  exit 1
  ;;
esac