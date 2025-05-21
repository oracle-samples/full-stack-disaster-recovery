#!/bin/bash
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# Version: 5.1 (Enhanced Automation, Dynamic DB Node)
# Purpose: Configure DB tier utilities for EBS FSDR with enhanced automation

set -euo pipefail
set -x

# Arguments
P_APPS_UN=apps
SECRET_APPS_OCID="$1"
SECRET_SYSTEM_OCID="$2"
ENV_FILE_PATH="${3:-/u01/install/APPS}"

# Auto-detect instance number from hostname (or use 4th argument)
INSTANCE_NUM="${4:-}"

if [[ -z "$INSTANCE_NUM" ]]; then
    if [[ "$(hostname)" =~ 02 ]]; then
        INSTANCE_NUM=2
    else
        INSTANCE_NUM=1
    fi
fi

# Directories
export CUSTDIR=/home/oracle/fsdr/logs
mkdir -p "$CUSTDIR"
LOG_FILE="$CUSTDIR/dbtxkconfig_$(date +%Y%m%d_%H%M%S).log"
exec >> "$LOG_FILE" 2>&1

# Lightweight validation log
START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
echo "INFO: Script started at $START_TIME on host $(hostname)"
echo "INFO: Using instance number: $INSTANCE_NUM"

# Retrieve Secrets
export SECRET_APPS=$(oci secrets secret-bundle get --raw-output --secret-id "$SECRET_APPS_OCID" --query "data.\"secret-bundle-content\".content" | base64 -d)
export SECRET_SYSTEM=$(oci secrets secret-bundle get --raw-output --secret-id "$SECRET_SYSTEM_OCID" --query "data.\"secret-bundle-content\".content" | base64 -d)

# Source EBS Environment
if [[ -f "$ENV_FILE_PATH/EBSapps.env" ]]; then
    . "$ENV_FILE_PATH/EBSapps.env" run || {
        echo "ERROR: Failed to source environment file: $ENV_FILE_PATH/EBSapps.env" >&2
        exit 1
    }
    echo "INFO: Environment file sourced successfully: $ENV_FILE_PATH/EBSapps.env"
else
    echo "ERROR: Environment file not found: $ENV_FILE_PATH/EBSapps.env" >&2
    exit 1
fi

# Validate Context File
[[ -z "${CONTEXT_FILE:-}" || ! -f "$CONTEXT_FILE" ]] && {
    echo "ERROR: CONTEXT_FILE not properly set" >&2
    exit 1
}

# Get PDB Name from context
PDB_NAME=$(grep -oP '(?<=<global_db_name oa_var="s_dbSid">)[^<]+' "$CONTEXT_FILE")

# Dynamically fetch DB node using SQL
dbnode=$(sqlplus -s ${P_APPS_UN}/${SECRET_APPS}@$PDB_NAME <<EOF
set head off verify off feedback off trimspool on
Select trim(host_name) from gv\$instance Where instance_number = $INSTANCE_NUM;
exit;
EOF
)
dbnode="$(echo "$dbnode" | xargs)"

export ORACLE_HOME=/u01/app/oracle/product/19.0.0.0/dbhome_1
export PATH=$ORACLE_HOME/bin:$PATH

export SCRIPTDIR="$ORACLE_HOME/appsutil/bin"

# Prepare Remote Script
remote_script="/tmp/dbtxkconfig_remote.sh"
rm -f "$remote_script"

cat > "$remote_script" << 'REMOTE_SCRIPT_EOF'
#!/bin/bash
set -euo pipefail
set -x

current_time=$(date "+%Y.%m.%d-%H.%M.%S")

env_file="$ORACLE_HOME/${PDB_NAME}_$(hostname).env"
if [[ -f "$env_file" ]]; then
    . "$env_file"
else
    echo "ERROR: Environment file not found: $env_file" >&2
    exit 1
fi
mkdir -p "$CUSTDIR"

run_txk_utility() {
    local mode="$1"
    echo "INFO: Running $mode operation"

    if [[ "$mode" == "setUtlFileDir" ]]; then
        { echo "$SECRET_APPS"; echo "$SECRET_SYSTEM"; } | perl "$SCRIPTDIR/txkCfgUtlfileDir.pl" \
            -contextfile="$CONTEXT_FILE" -oraclehome="$ORACLE_HOME" -outdir="$CUSTDIR" \
            -mode="$mode" -servicetype=opc -promptmsg=hide
    else
        { echo "$SECRET_APPS"; } | perl "$SCRIPTDIR/txkCfgUtlfileDir.pl" \
            -contextfile="$CONTEXT_FILE" -oraclehome="$ORACLE_HOME" -outdir="$CUSTDIR" \
            -mode="$mode" -servicetype=opc -promptmsg=hide
    fi

    sleep 2
    local txklog
    txklog=$(find "$CUSTDIR" -type f -name 'txkCfgUtlfileDir.log' | head -1)

    if [[ -f "$txklog" ]] && \
       grep -q "ERRORCODE = 0" "$txklog"; then
        echo "INFO: $mode operation successful"
        cp "$txklog" "$CUSTDIR/txkCfgUtlfileDir_${mode}-${current_time}.log"
    else
        echo "ERROR: $mode operation failed"
        exit 1
    fi
}

run_txk_utility getUtlFileDir
run_txk_utility setUtlFileDir
run_txk_utility syncUtlFileDir

# Autoconfig Check
if grep -q "AutoConfig is exiting with status 0" "$CUSTDIR"/TXK_UTIL_DIR*/acfg_log_*.log; then
    echo "INFO: Autoconfig successful"
    cp "$CUSTDIR"/TXK_UTIL_DIR*/acfg_log_*.log "$CUSTDIR"
    rm -rf "$CUSTDIR"/TXK_UTIL_DIR*
else
    echo "ERROR: Autoconfig failed"
    exit 1
fi
REMOTE_SCRIPT_EOF

# Execute Remote Script
scp "$remote_script" "oracle@$dbnode:$(basename "$remote_script")"
ssh "oracle@$dbnode" "bash -s" << EOSSH
export SECRET_APPS='$SECRET_APPS'
export SECRET_SYSTEM='$SECRET_SYSTEM'
export PDB_NAME='$PDB_NAME'
export CONTEXT_FILE='$CONTEXT_FILE'
export ORACLE_HOME='$ORACLE_HOME'
export SCRIPTDIR='$SCRIPTDIR'
export CUSTDIR='$CUSTDIR'
bash "$(basename "$remote_script")"
EOSSH

remote_status=$?
if [[ $remote_status -ne 0 ]]; then
    echo "ERROR: DB tier configuration failed. Check logs on $dbnode:$CUSTDIR" >&2
    exit 1
else
    echo "INFO: DB tier configuration successful. Logs available at $CUSTDIR"
    exit 0
fi