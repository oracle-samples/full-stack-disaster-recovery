#!/bin/bash
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script should be installed on any OCI compute instance hosting Linux
# that has the latest OCI CLI installed

# Required parameters:
#
# Example script written by Greg King, Full Stack DR (example, not for production)
# ============================================================================
declare params_qty=$#  #  number of params passed from command line
declare params_exp=1  #  number of expected params
declare scrpt
declare scrpt_path
declare TIMESTMP
declare drpg_ocid  # OCID of standby DRPG
declare loghost  # hostname where logs are written
declare logstrng  # first string written to log
declare LOGFILE  # global scope write script progress to log

# ============================================================================
# Ensure required parameters were passed
# ============================================================================
chkCmdParams () {
  # ----
  # Ensure all required params were passed on command line
  # ----
  echo -e "INFO: Ensuring command line parameters were passed to $scrpt [chkCmdParams]" | tee -a "${LOGFILE}"

  if [ "$params_qty" == 0 ]
  then
    prtUsage 0
    exit 1
  fi

  echo -e "INFO: Found the $params_exp required command line parameter. The following parameter was passed to the command line:" | tee -a "${LOGFILE}"

  # ----
  # Log the values of command line parameters
  # ----
  declare param1="\tDRPG OCID: $drpg_ocid"

  echo -e "$param1" | tee -a "${LOGFILE}"
}

# ============================================================================
# Usage message
# ============================================================================
prtUsage () {
  declare str1 str2 str3

  if [ "$1" -eq 0 ]
  then
    str1="FAIL: missing one required command line parameter (see below)."
    echo -e "\n$str1"
  fi

    echo -e "\nUsage: $scrpt <DR protection group OCID>"

str1="
This will back up the specified DR protection group and all DR plans that are associated with the protection group.
The backups are simply the object data in JSON format as collected by OCI CLI disaster recovery get commands.  The
logs and backups are stored in /tmp/
"

str2="
This script only backs up the DR protection group and DR plans in a single region. You have to run this script once
for each region.
"

str3="You only need to specify one command line parameter:

Required parameter:

  - Param 1: DRPG OCID - OCID for the target DR protection group

  Examples:

  $scrpt ocid1.drprotectiongroup.oc1.iad.12345678

  $scrpt ocid1.drprotectiongroup.oc1.phx.87654321
"

  fmt -g 75 <<<"${str1}"
  fmt -g 75 <<<"${str2}"
  fmt -t  <<<"${str3}"
}

# ============================================================================
# Main function that drives DR plan backups
# ============================================================================
bkpPlans () {
  declare drpg_ocid=$1
  declare bkup_path  # subdirectory to contain all json files
  declare drpg_key  # region DRPG can be found
  declare drpg_bkup  # ensure no spaces in drpg name used for file name
  declare drpg_name  # string used for logging
  declare drpg_rcrd  # object data for DRPG (json data)
  declare drpl_list  # list of all plans belonging to a DRPG
  declare drpl_ocid  # plan OCID
  declare drpl_rcrd  # object data for DR plan (json data)
  declare errcnt=0

  # ----
  # Get info about the DRPG
  # ----
  drpg_key=$(cliGetRegionKeyFromOcid "$drpg_ocid")  # get region key where DRPG exists (phx, iad, etc.)
  echo "INFO: Gathering data about DRPG in $drpg_key: $drpg_ocid [cliGetDrpgName]" | tee -a $LOGFILE
  drpg_name=$(cliGetDrpgName $drpg_ocid $drpg_key)
  drpg_bkup=$(echo "$drpg_name" | sed s/\ /-/)
  bkup_path="/tmp/${scrpt}-${TIMESTMP}-${drpg_bkup}.bkup"

  if [ -n "$drpg_name" ]; then
    echo "INFO: Found DRPG: $drpg_name [bkpPlans]" | tee -a $LOGFILE
  else
    echo "FAIL: Exiting: No DRPG with this OCID was found in $drpg_key: $drpg_ocid [bkpPlans]" | tee -a $LOGFILE
    exit 1
  fi

  # ----
  # Back up the DRPG itself.  This just calls a CLI get command to write object data
  # to a file in json format
  # ----
  echo "INFO: All backups are being written to: $bkup_path [bkpPlans]" | tee -a $LOGFILE
  mkdir $bkup_path

  echo "INFO: Getting object data for DRPG in JSON format: $drpg_name [cliGetDrpgRecordJson]" | tee -a $LOGFILE
  drpg_rcrd=$(cliGetDrpgRecordJson "$drpg_ocid" "$drpg_key")

  if [ -n "$drpg_rcrd" ]; then
    echo "INFO: Adding JSON backup file to: $bkup_path [bkpPlans]" | tee -a $LOGFILE
    mv "$drpg_rcrd" "$bkup_path"
  else
    echo "FAIL: Exiting: Something went wrong with backup of DRPG: $drpg_name [bkpPlans]" | tee -a $LOGFILE
    exit 2
  fi

  # ----
  # Get list of DR plans, if any
  # ----
  if [ -n "$drpg_name" ]; then
    echo "INFO: Getting list of DR plans associated with DRPG in $drpg_key: $drpg_name [cliGetDrpgPlans]" | tee -a $LOGFILE
    drpl_list=$(cliGetDrpgPlans $drpg_ocid $drpg_key)

    if [ -n "$drpl_list" ]; then
      echo "INFO: Found list of DR plans contained in DRPG: $drpg_name [bkpPlans]" | tee -a $LOGFILE
    else
      echo "INFO: Skipping plan group backups since no DR plans were found for DRPG in $drpg_key: $drpg_name [bkpPlans]" | tee -a $LOGFILE
    fi
  fi

  # ----
  # Back up each DR plan assocated with the DRPG.  This just calls a CLI get command to write object data
  # to a file in json format
  # ----
  if [ -n "$drpl_list" ]; then
    echo "INFO: Backing up all DR plans associated with DRPG in $drpg_key: $drpg_name [bkpPlans]" | tee -a $LOGFILE

    for drpl_ocid in $drpl_list; do
      echo "  INFO: Getting object data for DR plan in JSON format: $drpl_ocid [cliGetDrpgRecordJson]" | tee -a $LOGFILE
      drpl_rcrd=$(cliGetDrPlanRecordJson "$drpl_ocid" "$drpg_key")

      if [ -n "$drpl_rcrd" ]; then
        echo "  INFO: Adding JSON backup file to: $bkup_path [bkpPlans]" | tee -a $LOGFILE
        mv "$drpl_rcrd" "$bkup_path"
      else
        echo "  WARN: Skipping: Something went wrong with backup of DR plan: $drpl_ocid [bkpPlans]" | tee -a $LOGFILE
        errcnt=$((errcnt+1))
      fi
    done
  fi

  # ----
  # Report status of backup operation
  # ----
  if [ "$errcnt" -eq 0 ]; then
    echo -e "INFO: Successfully completed all backups of: $drpg_name [bkpPlans]" | tee -a "${LOGFILE}"
  else
    echo -e "WARN: Not all DR plans were backed up: The following number of DR plans were not backed up: $errcnt [bkpPlans]" | tee -a "${LOGFILE}"
 fi

 return "$errcnt"
}

# ============================================================================
# The script starts here
# ============================================================================
scrpt=$(basename $0)
scrpt_path=$(dirname $0)
drpg_ocid=$1
TIMESTMP=$(date +'%Y%m%d-%H%M%S')
loghost=$(hostname)
logstrng="Full Stack DR is beginning backup of DR protection group on: ${TIMESTMP}"
LOGFILE="/tmp/${scrpt}-${TIMESTMP}.log"

# ----
# Includes
# ----
source ${scrpt_path}/fsdr-cli.func  # common bash functions used by many different scripts
source ${scrpt_path}/fsdr-cli-cust.func  # overload bash functions in fsdr-cli.func with custom modifications

# ----
# Start
# ----
logInit "$loghost" "$logstrng"    # Create logfile
chkCmdParams  # Perform basic sanity checks for command line params
bkpPlans "$drpg_ocid"  # perform the backup
exit $?