#!/bin/bash

##############################################################################################################################
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script Resume or Pause OAC (Oracle Analytics Cloud) instances in the both Regions
# process during a switchover or failover orchestrated by Full Stack DR.
#
# You will have  to call oac-start-stop.sh use Parameters start/stop lowercase 
# and Region ID IAD/PHX uppercase.
#
# ----
# Usage
# ----
# oac-start-stop.sh <start/stop> <region ID>
# 
# ----
# How to add this script to Full Stack DR plans
# ----
# You need to create one Plan Group for each switchover or failover plan in the
# DR protection group at both regions. The script needs to be installed on the movable
# compute instance you added as a member of the DR protection group. The script can be
# installed in the same directory you install the OAC scripts
#
# ----
# Examples
# ----
# Add following plan group to switchover & failover DR plans at PHX Viceversa
#
# Plan Group: Start OAC Instance on PHX (Standby)
#   Plan step 1: Run oac-start-stop script at PHX
#   Local script: /WheverYouPutTheScript/oac-start-stop.sh start PHX
#   User: opc
#
# Add following plan group to switchover & failover DR plans at IAD Viceversa
#
# Plan Group: Stop OAC Instance on IAD (Primary)
#   Plan step 1: Run oac-start-stop script at IAD
#   Local script: /WheverYouPutTheScript/oac-start-stop.sh stop IAD
#   User: opc
##############################################################################################################################

#oac_instanes_region_keys
region1=IAD
region2=PHX

#oac_instance_ocid_value
oac_instance_ocid_region1=xxxxxxxxx
oac_instance_ocid_region2=xxxxxxxxx

##############################################################################################################################

# Stop OAC Instance
stop_oac()
{
oci analytics analytics-instance stop --analytics-instance-id $oac_instance_ocid --max-wait-seconds 1200 --wait-for-state SUCCEEDED --wait-interval-seconds 30 --profile $region| jq . > status.json
}

# Start OAC Instance
start_oac()
{
oci analytics analytics-instance start --analytics-instance-id $oac_instance_ocid --max-wait-seconds 1200 --wait-for-state SUCCEEDED --wait-interval-seconds 30 --profile $region| jq . > status.json
}

# Check the status of the operation
check_status()
{
status=`jq .data.status status.json |sed -rn 's/(")([^"]+)(.*)/\2/p'`

if [ "$status" == "SUCCEEDED" ]; then
   echo ""
   echo "OAC instance operation is successfully completed."
else
   echo ""
   echo "OAC instance operation failed."
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
        oac_instance_ocid=$oac_instance_ocid_region1
elif [ "$region2" == "$regioncode" ]; then
        region=$region2
        oac_instance_ocid=$oac_instance_ocid_region2

else
        echo "Valid oci region code is not provided. Exiting......."
        exit
fi

# Check if the Analytics Instance OCID provided or not.
if [ -z "$oac_instance_ocid" ]
then
    echo "Analytics Instance ID not provided, exiting..."
        echo "Provide a valid ocid value of the analytics instance and run the script."
        exit
fi

echo "$1ing the OAC instance in the OCI region $2."

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
exec > "$logDir/start_stop_oac_$(date +"%Y%m%d_T%H%M%S").log" 2>&1

echo "-------------------------------------------------------------"
echo "  OAC instance operation selected is $1 for region $2."
echo "-------------------------------------------------------------"
echo ""

# Check the Option and perform the required operation
case "$1" in
  start)
    start_oac
    check_status
  ;;
  stop)
    stop_oac
    check_status
  ;;
  *)
  echo "Usage: $0 {start|stop} {region_code}"
  exit 1
  ;;
esac

