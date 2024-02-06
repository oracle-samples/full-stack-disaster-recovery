#!/bin/bash
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script should be installed on each compute node where you
# need Full Stack DR to change IP addresses in OCI DNS

# Required parameters:
#
# Example script written by Greg King, Full Stack DR (example, not for production)
# ============================================================================
declare params_qty=$#  #  number of params passed from command line
declare params_exp=3  #  number of expected params
declare scrpt  # name of this script
declare scrpt_path  # path where this script lives
declare dns_key  # Region in which DNS zone lives
declare dns_zone  # OCI DNS zone name
declare drpg_ocid # OCID of standby DRPG
declare drpg_key  # region key of standby DRPG
declare dns_fqdn  # the actual domain name assisgned to SOA record in the DNS zone
declare loghost  # hostname where logs are written
declare logstrng  # first string written to log
declare LOGFILE  # global scope
declare JSON_CUR  # file name the CLI get commands will write to
declare JSON_NEW  # file name to contain our changes for CLI update commnads
declare TIMESTMP  # date time for file names and messages


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
  elif [ "$params_qty" == 1 ]
  then
    prtUsage 1
    exit 2
  elif [ "$params_qty" == 2 ]
  then
    prtUsage 2
    exit 3
  fi

  echo -e "INFO: Found all $params_exp required command line parameters. The following parameters were passed to the command line:" | tee -a "${LOGFILE}"

  # ----
  # Log the values of command line parameters
  # ----
  declare param1="\tDNS region: $dns_key"
  declare param2="\n\tDNS zone: $dns_zone"
  declare param3="\n\tDRPG OCID: $drpg_ocid"

  echo -e "$param1 $param2 $param3" | tee -a "${LOGFILE}"
}

# ============================================================================
# Usage message
# ============================================================================
prtUsage () {
  declare str1 str2 str3

  if [ "$1" -eq 0 ]
  then
    str1="FAIL: missing all required command line parameters (see below)."
    echo -e "\n$str1"
  fi

  if [ "$1" -eq 1 ]
  then
    str1="FAIL: only one parameter was supplied; missing 2nd & 3rd required command line parameters (see below)."
    echo -e "\n$str1"
  fi

  if [ "$1" -eq 2 ]
  then
    str1="FAIL: only two parameters were supplied; missing 3rd required command line parameters (see below)."
    echo -e "\n$str1"
  fi

  echo -e "\nUsage: $scrpt <dns zone region> <dns zone OCID> <DR protection group OCID>"

str1="
This will update IP addresses for one or more moving compute instances belonging to a public zone in OCI DNS.
This script only operates on public zones. Private zones are managed by OCI and cannot be
modified using the OCI CLI.  Only compute instances that are 'moving' between regions need to have their IPs updated in
OCI DNS public zones after a failover or switchover.
"

str2="Install this script on any moving or non-moving compute instance (VM) that is a member of a Full Stack DR protection group.
Ensure that the OCI CLI is installed and working on any compute instance where this script is installed.

Add this script to a Full Stack DR user-defined plan group in all failover and switchover plans
belonging to the DR protection groups in both regions. The plan group should probably be called right after
the built-in DR plan group to launch 'moving' compute at the standby region. Do not add this to DR drills.
This script assumes all compute instances are in the same compartment and DNS zone. You
can simply add multiple steps in a single Full Stack DR plan group
to update DNS for compute instances in different compartments and/or public DNS zones.
"

str3="You need to specify a minimum of four command line parameters\; the position of each parameter is significant:

Required parameters:

  - DNS region key:  The region key of the standby region (IE: ams, iad, ord, phx, etc.)

  - DNS zone name:  Name of the public DNS zone containing records to be modified (IE: myDNSzone)

  - DRPG OCID:  OCID for the DR protection group containing VMs. Note that this script will

  Examples:

  $scrpt iad mydomain ocid1.drprotectiongroup.oc1.iad.12345678

  $scrpt phx mydnszone ocid1.drprotectiongroup.oc1.phx.87654321
"

  fmt -g 75 <<<"${str1}"
  fmt -g 75 <<<"${str2}"
  fmt -t  <<<"${str3}"
}

# ============================================================================
# CLI update command using JSON_NEW
# ============================================================================
updDns () {
  declare dns_fqdn  # the actual domain name in OCI DNS
  declare drpg_key  # region key where DRPG exists (phx, iad, etc.)
  declare drpg_name  # DRPG display name
  declare ocid_list  # all VMs & LB that are members of a DRPG
  declare membr_ocid  # OCID of each VM or LB
  declare membr_type  # is it a VM or LB
  declare errcnt=0  # counter to track all failures, if any
  declare chk=0  # used to check return val from CLI command executions

  echo -e "INFO: Gathering initial data [updDns]" | tee -a "${LOGFILE}"

  # ----
  # Ensure DNS zone is correct and return the FQDN associated with the DNS zone
  # ----
  echo -e "  INFO: Retrieving FQDN for DNS zone: $dns_zone [updDns]" | tee -a "${LOGFILE}"
  dns_fqdn=$(cliGetDnsFQDN "$dns_zone" "$dns_key")  # set global var dns_fqdn

  if [ -n "$dns_fqdn" ]; then
      echo -e "  INFO: Found FQDN for DNS zone: $dns_fqdn [updDns]" | tee -a "${LOGFILE}"
  else
    echo -e "  FAIL: Exiting: Could not find FQDN for DNS zone. Ensure DNS zone name is correct: $dns_zone [updDns]" | tee -a "${LOGFILE}"
    exit 1
  fi

  # ----
  # Get DRPG name and region key (CLI functions need region key throughout the script)
  # ----
  drpg_key=$(cliGetRegionKeyFromOcid "$drpg_ocid")  # get region key where DRPG exists (phx, iad, etc.)
  ocid_type=$(echo "$drpg_ocid" | awk -F. '{print $2}')  # ensure 3rd param is protection group

  if [ "$ocid_type" != 'drprotectiongroup' ]; then
    echo -e "  FAIL: Exiting: The third parameter passed to this script must be a protection group OCID. Incorrect OCID type was provided: $ocid_type [updDns]" | tee -a "${LOGFILE}"
    exit 1
  fi

  echo -e "  INFO: Retrieving name of DRPG in $drpg_key: $drpg_ocid [updDns]" | tee -a "${LOGFILE}"
  drpg_name=$(cliGetDrpgName "$drpg_ocid" "$drpg_key")  # get DRPG display name

  if [ -n "$drpg_name" ]; then
      echo -e "  INFO: Found name of DRPG: $drpg_name [updDns]" | tee -a "${LOGFILE}"
  else
    echo -e "  FAIL: Exiting: Could not find name of DRPG: $drpg_ocid [updDns]" | tee -a "${LOGFILE}"
    exit 1
  fi

  # ----
  # Get list of OCIDs for compute and load balancers
  # ----
  echo -e "  INFO: Retrieving list of compute and load balancers that are members of DRPG: $drpg_name [updDns]" | tee -a "${LOGFILE}"
  ocid_list=$(cliGetComputeOcidAll "$drpg_ocid" "$drpg_key")  # get all VMs & LB that are members of a DRPG

  # ----
  # Replace the old IP found in JSON_NEW file with the new IP
  # ----
  for membr_ocid in $ocid_list; do
    membr_type=$(echo "$membr_ocid" | awk -F. '{print $2}')

    # ----
    # Call appropriate function for member type (IE: VM or LB)
    # ----
    if [ "$membr_type" == 'instance' ]; then
      echo -e "INFO: Beginning IP change for compute instance in DRPG: $drpg_name [updDns]" | tee -a "${LOGFILE}"
      chk=0
      updDnsForVM "$membr_ocid" "$drpg_key" "$drpg_name"
      chk=$?

      [[ "$chk" -ne 0 ]] && errcnt=$((errcnt+1))
    elif [ "$membr_type" == 'loadbalancer' ]; then
      echo -e "INFO: Beginning IP change for load balancer in DRPG: $drpg_name [updDns]" | tee -a "${LOGFILE}"
      chk=0
      updDnsForLB "$membr_ocid" "$drpg_key" "$drpg_name" "$dns_fqdn"
      chk=$?

      [[ "$chk" -ne 0 ]] && errcnt=$((errcnt+1))
    fi
  done

  if [ "$errcnt" -eq 0 ]; then
    echo -e "INFO: Successfully completed all IP address updates for OCI DNS zone ${dns_zone} [updDns]" | tee -a "${LOGFILE}"
  else
    echo -e "FAIL: Failed to complete IP address updates for OCI DNS zone ${dns_zone} [updDns]" | tee -a "${LOGFILE}"
 fi

 return "$errcnt"
}

# ============================================================================
# Function to update IP in public DNS for a single load balancer
# ============================================================================
updDnsForLB () {
  declare lb_ocid=$1
  declare drpg_key=$2
  declare drpg_name=$3
  declare lb_name
  declare lb_fqdn
  declare new_ip_addr
  declare old_ip_addr
  declare chk=0

  lb_fqdn=$(cliGetLbFQDN "$lb_ocid" "$drpg_key")
  lb_name=$(basename "$lb_fqdn")

  echo -e "  INFO: Processing load balancer: $lb_fqdn [updDnsForLB]" | tee -a "${LOGFILE}"

  # ----
  # Get IP from primary VNIC attached to the compute instance
  # ----
  echo -e "  INFO: Finding IP currently associated with $lb_fqdn [cliGetLbIPFromOcid]" | tee -a "${LOGFILE}"
  new_ip_addr=$(cliGetLbIPFromOcid "$lb_ocid" "$drpg_key")
  chk=$?

  if [ "$chk" -eq 0 ]; then
    echo -e "  INFO: Found IP currently associated with $lb_name: $new_ip_addr [updDnsForLB]" | tee -a "${LOGFILE}"
  elif [ "$chk" -eq 255 ]; then
    echo -e "  FAIL: Failed to find IP currently associated with $lb_name [updDnsForLB]" | tee -a "${LOGFILE}"
    return 1  # stop processing this compute instance
  fi

  # ----
  # Get current IP for load balancer from DNS record
  # ----
  if [ -n "$new_ip_addr" ]; then
    echo -e "  INFO: Finding old IP currently assigned to $lb_name in DNS zone: $dns_zone [cliGetIPFromDNS]" | tee -a "${LOGFILE}"
    old_ip_addr=$(cliGetIPFromDNS "$lb_fqdn" "$dns_zone" "$dns_key")  # find old IP in DNS record
    chk=$?

    if [ "$chk" -eq 0 ]; then
      echo -e "  INFO: Found IP currently associated with $lb_name in DNS: $old_ip_addr [updDnsForLB]" | tee -a "${LOGFILE}"
    else
      echo -e "  INFO: Skipping IP change. No DNS record was found for $lb_name in DNS zone: $dns_zone [updDnsForLB]" | tee -a "${LOGFILE}"
      return 0  # stop processing this compute instance
    fi
  fi

  # ----
  # Skip further update if old and new IPs match
  # ----
  if [ "$old_ip_addr" == "$new_ip_addr" ]; then
    echo -e "  INFO: Skipping IP change. Current IP in DNS is already correct for $lb_name: $new_ip_addr [updDnsForLB]" | tee -a "${LOGFILE}"
    return 0  # stop processing this compute instance
  fi

  # ----
  # Get the DNS record for the load balancer in the form of a JSON file
  # ----
  if [ "$chk" -eq 0 ]; then
    echo -e "  INFO: Creating JSON file from DNS record for ${lb_name} in DNS zone: ${dns_zone} [cliWrtDnsRecordToJson]" | tee -a "${LOGFILE}"
    cliWrtDnsRecordToJson "$lb_fqdn" "$dns_zone" "$dns_key" "$JSON_CUR" # write current DNS record to JSON_CUR file
    chk=$?

    if [ "$chk" -eq 0 ]; then
      echo -e "  INFO: Found DNS record for ${lb_fqdn} [updDnsForLB]" | tee -a "${LOGFILE}"
    else
      echo -e "  FAIL: Cannot find DNS record for ${lb_name} in DRPG: ${drpg_name} [updDnsForLB]"  | tee -a "${LOGFILE}"
      errcnt=$((errcnt+1))
      return 1  # stop processing this compute instance
    fi
  fi

  # ----
  # Create a new JSON file from the one created cliGetDnsRecord that we can
  # update with new IP addresses
  # ----
  if [ "$chk" -eq 0 ]; then
    echo -e "  INFO: Preparing json file that will be used to update DNS record for ${lb_name} [jsonBldNew]" | tee -a "${LOGFILE}"
    jsonBldNew # prepare JSON_NEW format file for oci record update command
    chk=$?

    if [ "$chk" -eq 0 ]; then
      echo -e "  INFO: Completed creating & formatting new json file: $JSON_NEW [updDnsForLB]" | tee -a "${LOGFILE}"
    else
      echo -e "  FAIL: Failed to create new json file: $JSON_NEW [updDnsForLB]" | tee -a "${LOGFILE}"
      errcnt=$((errcnt+1))
      return 1  # stop processing this compute instance
    fi
  fi

  # ----
  # Update the JSON file by replacing old IP with new IP
  # ----
  if [ "$chk" -eq 0 ]; then
    echo -e "  INFO: Changing IP for $lb_name from $old_ip_addr to $new_ip_addr in json file: $JSON_NEW [jsonModNew]" | tee -a "${LOGFILE}"
    jsonModNew "${old_ip_addr}" "${new_ip_addr}"   # replace old IP with new IP in JSON_NEW
    chk=$?

    if [ "$chk" -eq 0 ]; then
     echo -e "  INFO: Completed changing IP addresses in json file; everything is ready to update DNS [updDnsForLB]" | tee -a "${LOGFILE}"
    elif [ "$chk" -eq 1 ]; then
      echo -e "  FAIL: Failed to change IP address in json file; the \"sed\" substitution failed [updDnsForLB]" | tee -a "${LOGFILE}"
      errcnt=$((errcnt+1))
      return 1  # stop processing this compute instance
    elif [ "$chk" -eq 2 ]; then
      echo -e "  INFO: Skipping: The new IP address for $lb_fqdn ($new_ip_addr) is already set correctly for DNS zone $dns_zone [updDnsForLB]" | tee -a "${LOGFILE}"
      return 0  # stop processing this compute instance
    fi
  fi

  # ----
  # Use CLI to send the modified JSON file back to OCI DNS to update the DNS record
  # for the compute instance
  # ----
  if [ "$chk" -eq 0 ]; then
    echo -e "  INFO: Beginning DNS update for $lb_fqdn in zone: ${dns_zone} [cliUpdDnsRecord]" | tee -a "${LOGFILE}"
    cliUpdDnsRecord "$lb_fqdn" "$dns_key" "$dns_zone"
    chk=$?

    if [ "$chk" -eq 0 ]; then
      echo -e "  INFO: CLI update command successfully sent IP address for $lb_fqdn to OCI DNS zone: ${dns_zone} [updDnsForLB]" | tee -a "${LOGFILE}"
    else
      echo -e "  FAIL: CLI update command failed to send IP address for $lb_fqdn} to OCI DNS zone: ${dns_zone} [updDnsForLB]" | tee -a "${LOGFILE}"
      errcnt=$((errcnt+1))
      return 1  # stop processing this compute instance
    fi
  fi
}

# ============================================================================
# Function to update IP in public DNS for a single compute instance
# ============================================================================
updDnsForVM () {
  declare srvr_ocid=$1
  declare drpg_key=$2
  declare drpg_name=$3
  declare srvr_name
  declare srvr_fqdn
  declare new_ip_addr
  declare old_ip_addr
  declare chk=0

  srvr_name=$(cliGetComputeName "$srvr_ocid" "$drpg_key")
  srvr_fqdn="${srvr_name}.${dns_fqdn}"

  echo -e "  INFO: Processing compute instance: $srvr_name [updDnsForVM]" | tee -a "${LOGFILE}"

  # ----
  # Get IP from primary VNIC attached to the compute instance
  # ----
  echo -e "  INFO: Finding IP currently associated with primary VNIC attached to $srvr_name [cliGetIPFromVNIC]" | tee -a "${LOGFILE}"
  new_ip_addr=$(cliGetIPFromVNIC "$srvr_ocid" "$drpg_key")

  if [ -n "$new_ip_addr" ]; then
    echo -e "  INFO: Found IP currently associated with primary VNIC for $srvr_name: $new_ip_addr [updDnsForVM]" | tee -a "${LOGFILE}"
  else
    echo -e "  FAIL: Failed to find IP currently associated with primary VNIC for $srvr_name [updDnsForVM]" | tee -a "${LOGFILE}"
    return 1  # stop processing this compute instance
  fi

  # ----
  # Get current IP for compute instance from DNS record
  # ----
  if [ -n "$new_ip_addr" ]; then
    echo -e "  INFO: Finding old IP currently assigned to $srvr_name in DNS zone: $dns_zone [cliGetIPFromDNS]" | tee -a "${LOGFILE}"
    old_ip_addr=$(cliGetIPFromDNS "$srvr_fqdn" "$dns_zone" "$dns_key")  # find old IP in DNS record

    if [ -n "$old_ip_addr" ]; then
      echo -e "  INFO: Found IP currently associated with $srvr_name in DNS: $old_ip_addr [updDnsForVM]" | tee -a "${LOGFILE}"
    else
      echo -e "  INFO: Skipping IP change. No DNS record was found for $srvr_name in DNS zone: $dns_zone [updDnsForVM]" | tee -a "${LOGFILE}"
      return 0  # stop processing this compute instance
    fi
  fi

  # ----
  # Skip further update if old and new IPs match
  # ----
  if [ "$old_ip_addr" == "$new_ip_addr" ]; then
    echo -e "  INFO: Skipping IP change. Current IP in DNS is already correct for $srvr_name: $new_ip_addr [updDnsForVM]" | tee -a "${LOGFILE}"
    return 0  # stop processing this compute instance
  fi

  # ----
  # Get the DNS record for the VNIC in the form of a JSON file
  # ----
  if [ "$chk" -eq 0 ]; then
    echo -e "  INFO: Creating JSON file from  DNS record for ${srvr_name} in DNS zone: ${dns_zone} [cliWrtDnsRecordToJson]" | tee -a "${LOGFILE}"
    cliWrtDnsRecordToJson "$srvr_fqdn" "$dns_zone" "$dns_key" "$JSON_CUR" # get current DNS record for VM and store in JSON_OLD file
    chk=$?

    if [ "$chk" -eq 0 ]; then
      echo -e "  INFO: Found DNS record for ${srvr_fqdn} [updDnsForVM]" | tee -a "${LOGFILE}"
    else
      echo -e "  FAIL: Cannot find DNS record for ${srvr_name} in compartment: ${drpg_name} [updDnsForVM]"  | tee -a "${LOGFILE}"
      errcnt=$((errcnt+1))
      return 1  # stop processing this compute instance
    fi
  fi

  # ----
  # Create a new JSON file from the one created cliGetDnsRecord that we can
  # update with new IP addresses
  # ----
  if [ "$chk" -eq 0 ]; then
    echo -e "  INFO: Preparing json file that will be used to update DNS record for ${srvr_name} [jsonBldNew]" | tee -a "${LOGFILE}"
    jsonBldNew # prepare JSON_NEW format file for oci record update command
    chk=$?

    if [ "$chk" -eq 0 ]; then
      echo -e "  INFO: Completed creating & formatting new json file: $JSON_NEW [updDnsForVM]" | tee -a "${LOGFILE}"
    else
      echo -e "  FAIL: Failed to create new json file: $JSON_NEW [updDnsForVM]" | tee -a "${LOGFILE}"
      errcnt=$((errcnt+1))
      return 1  # stop processing this compute instance
    fi
  fi

  # ----
  # Update the JSON file by replacing old IP with new IP
  # ----
  if [ "$chk" -eq 0 ]; then
    echo -e "  INFO: Changing IP for $srvr_name from $old_ip_addr to $new_ip_addr in json file: $JSON_NEW [jsonModNew]" | tee -a "${LOGFILE}"
    jsonModNew "${old_ip_addr}" "${new_ip_addr}"   # replace old IP with new IP in JSON_NEW
    chk=$?

    if [ "$chk" -eq 0 ]; then
     echo -e "  INFO: Completed changing IP addresses in json file; everything is ready to update DNS [updDnsForVM]" | tee -a "${LOGFILE}"
    elif [ "$chk" -eq 1 ]; then
      echo -e "  FAIL: Failed to change IP address in json file; the \"sed\" substitution failed [updDnsForVM]" | tee -a "${LOGFILE}"
      errcnt=$((errcnt+1))
      return 1  # stop processing this compute instance
    elif [ "$chk" -eq 2 ]; then
      echo -e "  INFO: Skipping: The new IP address for $srvr_name ($new_ip_addr) is already set correctly for DNS zone $dns_zone [updDnsForVM]" | tee -a "${LOGFILE}"
      return 0  # stop processing this compute instance
    fi
  fi

  # ----
  # Use CLI to send the modified JSON file back to OCI DNS to update the DNS record
  # for the compute instance
  # ----
  if [ "$chk" -eq 0 ]; then
    echo -e "  INFO: Beginning DNS update for ${srvr_name} in zone: ${dns_zone} [cliUpdDnsRecord]" | tee -a "${LOGFILE}"
    cliUpdDnsRecord "$srvr_fqdn" "$dns_key" "$dns_zone"
    chk=$?

    if [ "$chk" -eq 0 ]; then
      echo -e "  INFO: CLI update command successfully sent IP address for ${srvr_name} to OCI DNS zone: ${dns_zone} [updDnsForVM]" | tee -a "${LOGFILE}"
    else
      echo -e "  FAIL: CLI update command failed to send IP address for ${srvr_name} to OCI DNS zone: ${dns_zone} [updDnsForVM]" | tee -a "${LOGFILE}"
      errcnt=$((errcnt+1))
      return 1  # stop processing this compute instance
    fi
  fi
}

# ============================================================================
# The script starts here
# ============================================================================
scrpt=$(basename $0)
scrpt_path=$(dirname $0)
dns_key=$1  # Region in which DNS zone lives
dns_zone=$2  # OCI DNS zone name
drpg_ocid=$3 # OCID of standby DRPG
loghost=$(hostname)
logstrng="Full Stack DR is beginning IP changes in DNS: ${TIMESTMP}"

TIMESTMP=$(date +'%Y%m%d-%H%M%S')
LOGFILE="/tmp/${scrpt}_${TIMESTMP}.log"
JSON_CUR="/tmp/${scrpt}_${TIMESTMP}_${drpg_key}_get.json"
JSON_NEW="/tmp/${scrpt}_${TIMESTMP}_${drpg_key}_upt.json"

# ----
# Includes
# ----
source ${scrpt_path}/fsdr-cli.func  # common bash functions used by many different scripts
source ${scrpt_path}/fsdr-cli-cust.func  # overload bash functions in fsdr-cli.func with custom modifications

# ----
# Start
# ----
logInit "$loghost" "$logstrng"    # Create logfile
chkCmdParams # Perform basic sanity checks for command line params
updDns       # use CLI command to update DNS records with new IPs
exit $?