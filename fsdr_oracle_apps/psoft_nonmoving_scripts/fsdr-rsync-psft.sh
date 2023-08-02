#!/bin/bash
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
#
# This script disables and enables cron jobs for PSFT rsync process
# during a switchover orchestrated by Full Stack DR.
#
# It will search crontab for a specific IP address and then either:
#   1. Disable cron jobs: comment the lines with specific IP by adding #FSDR as
#   first field
#
#   2. Enable cron jobs: uncomment the lines with #FSDR as first field
#
# ----
# How to add this script to Full Stack DR plans
# ----
# You need to create two Plan Groups for each switchover plan. The two plan groups
# should include two plan steps:
#
#   Plan Group: Stop PSFT at primary
#     Plan step 1: Disable rsync for PSFT (this script)
#     Plan step 2: Stop PSFT (your stop PSFT script)
#
#   Plan Group: Start PSFT at standby
#     Plan step 1: Enable rsync for PSFT (this script)
#     Plan step 2: Start PSFT (your start PSFT script)
#
# ----
# Examples
# ----
# Add the following script to Plan step 1 in the "Stop PSFT at primary" Plan group:
# Script: fsdr-rsync-psft disable 10.xxx.yyy.zzz
# User: psadm2
#
# Add the following script to Plan step 1 in the "Start PSFT at standby" Plan group:
# Script: fsdr-rsync-psft enable 10.xxx.yyy.zzz
# User: psadm2
#======================================================
# ----
# Some error trapping
# ----
SCRPT=$(basename $0)
if [ -z "$1" ]
then
        echo "ERROR: $SCRPT: Missing first argument that specifies task [disable|enable]"
        exit
fi

if [ -z "$2" ]
then
        echo "ERROR: $SCRPT: Missing second argument that specifies the IP that is hardcoded into the individual cron jobs."
        exit
fi

# ----
# The actual script
# ----
TASK=$1
PSFT_IP=$2
if [ "$TASK" == "disable" ]
then
        chk=$(crontab -l | grep "rsync_app" | grep '#FSDR')
        if [ -z "$chk" ]
        then
                echo "Disabling PSFT rsync jobs for $PSFT_IP in crontab"
                crontab -l | sed "/rsync_app/s/^/#FSDR /g" | crontab -
        else
                echo "PSFT rsync jobs for $PSFT_IP already disabled - continuing"
        fi
fi

if [ "$TASK" == "enable" ]
then
        chk=$(crontab -l | grep "rsync_app" | grep '#FSDR')
        if [ -n "$chk" ]
        then
                echo "Enabling PSFT rsync jobs for $PSFT_IP in crontab"
                crontab -l | sed "/#FSDR/s/^#FSDR //g" | crontab -
        else
                echo "PSFT rsync jobs for $PSFT_IP already enabled - continuing"
        fi
fi