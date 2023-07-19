#!/usr/bin/bash
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script disables and enables cron jobs for OAC (Oracle Analytics Cloud) snapshot
# process during a switchover or failover orchestrated by Full Stack DR.
#
# You will have set up a cronjob to call oac-create-snapshot.sh periodically. This script
# simply changes the one argument/parameter for oac-create-snapshot.sh from one region ID
# to another regions ID that you specify.
#
# ----
# Usage
# ----
# oac-chg-cron.sh <current region> <new region>
#
# ----
# How to add this script to Full Stack DR plans
# ----
# You need to create one Plan Group for each switchover or failover plan in the
# DR protection group at both regions. The script needs to be installed on the movable
# compute instance you added as a member of the DR protection group. The script can be
# installed in the same directory you install the OAC snapshot script oac-create-snapshot.sh.
#
# ----
# Examples
# ----
# Add following plan group to switchover & failover DR plans at PHX
#
# Plan Group: Switchover OAC snapshot to PHX (Standby)
#   Plan step 1: Run oac-chg-cron script at PHX
#   Local script: /WheverYouPutTheScript/oac-chg-cron.sh iad phx
#   User: root
#
# Add following plan group to switchover & failover DR plans at IAD
#
# Plan Group: Switchover OAC snapshot to IAD (Standby)
#   Plan step 1: Run oac-chg-cron script at IAD
#   Local script: /WheverYouPutTheScript/oac-chg-cron.sh phx iad
#   User: root
#======================================================

# ----
# Some error trapping
# ----
SCRPT=$(basename $0)
CRONJOB='oac-create-snapshot.sh' # The OAC snapshot script in crontab

if [ -z "$1" ]
then
	echo "ERROR: $SCRPT: Missing first argument that specifies the current OCI region ID"
	exit
fi 

if [ -z "$2" ]
then
	echo "ERROR: $SCRPT: Missing second argument that specifies the new OCI region ID"
	exit
fi 


# ====
# The actual script
# ====
CUR_REG=$1  # Search string for the current region
NEW_REG=$2  # String that will replace the search string when found
chk_string=$(crontab -l | grep "$CRONJOB" | grep -v '#' | awk '{print $(NF-1),$NF}')
chk_script=$(echo $chk_string | grep "$CRONJOB")
chk_region=$(echo $chk_string | grep "$CUR_REG")

# ----
# Warn user if the snapshot script is not found in the crontab
# ----
echo "$SCRPT: Searching for string in crontab: \"$CRONJOB $CUR_REG\""
echo "$SCRPT: Found string in crontab: \"$chk_string\""

if [ -z "$chk_script" ]
then
	echo "WARNING: $SCRPT: Update to OAC snapshot script in the crontab failed since \"$CRONJOB\" is not the crontab"
	exit 1
fi

# ----
# Warn user if the current region is not found as the 1st arg for 
# snapshot script in the crontab 
# ----
if [ -n "$chk_region" ]
then
	echo "$SCRPT: Changing \"$CRONJOB $CUR_REG\" to \"$CRONJOB $NEW_REG\" in the crontab"
	crontab -l | sed "/$CUR_REG/s//$NEW_REG/g" | crontab -

	echo "$SCRPT: Checking to see if crontab was updated with new value: \"$CRONJOB $NEW_REG\""
	chk_success=$(crontab -l | grep "$CRONJOB" | grep "$NEW_REG")
	if [ -n "$chk_success" ]
	then
		echo "$SCRPT: Confirmed crontab was updated with new value: \"$CRONJOB $NEW_REG\""
		exit 0
	elif [ -z "$chk_success" ]
	then
		echo "WARNING: $SCRPT: Update to crontab failed since the snapshot script was not updated with the value for the new region: \"$CRONJOB $NEW_REG\" is not in the crontab"
		exit 3

	fi
else
	echo "WARNING: $SCRPT: Update to crontab failed since the current region \"$CRONJOB $CUR_REG\" is not in the crontab" 
	exit 2
fi

