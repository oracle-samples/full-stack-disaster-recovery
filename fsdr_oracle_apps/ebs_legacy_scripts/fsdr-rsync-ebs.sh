#!/usr/bin/bash
#
# This script disables and enables cron jobs for EBS rsync process
# during a switchover orchestrated by Full Stack DR.
#
# It will search crontab for a specific IP address and then ether:
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
#   Plan Group: Stop EBS at primary
#     Plan step 1: Disable rsync for EBS (this script)
#     Plan step 2: Stop EBS (your stop EBS script)
#
#   Plan Group: Start EBS at standby
#     Plan step 1: Enable rsync for EBS (this script)
#     Plan step 2: Start EBS (your start EBS script)
#
# ----
# Examples
# ----
# Add the following script to Plan step 1 in the "Stop EBS at primary" Plan group:
# Script: fsdr-rsync-ebs disable 10.xxx.yyy.zzz
# User: oracle
#
# Add the following script to Plan step 1 in the "Start EBS at standby" Plan group:
# Script: fsdr-rsync-ebs enable 10.xxx.yyy.zzz
# User: oracle
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
EBS_IP=$2
if [ "$TASK" == "disable" ]
then
        chk=$(crontab -l | grep "$EBS_IP" | grep '#FSDR')
        if [ -z "$chk" ]
        then
                echo "Disabling EBS rsync jobs for $EBS_IP in crontab"
                crontab -l | sed "/$EBS_IP/s/^/#FSDR /g" | crontab -
        else
                echo "EBS rsync jobs for $EBS_IP already disabled - continuing"
        fi
fi

if [ "$TASK" == "enable" ]
then
        chk=$(crontab -l | grep "$EBS_IP" | grep '#FSDR')
        if [ -n "$chk" ]
        then
                echo "Enabling EBS rsync jobs for $EBS_IP in crontab"
                crontab -l | sed "/#FSDR /s/^#FSDR //g" | crontab -
        else
                echo "EBS rsync jobs for $EBS_IP already enabled - continuing"
        fi
fi
