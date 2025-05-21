#!/bin/bash
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
#==============================================================
# Script: fndnodeclean-fsdr.sh
# Purpose: Run FND Node Cleanup for EBS FSDR on the Applications PDB
# Author: Chandra Dharanikota
# Version: 2.0
#==============================================================

set -euo pipefail
set -x

# Constants
P_APPS_UN="apps"

# Input Parameters
SECRET_APPS_OCID="$1"                 # Secret OCID for APPS password
CDB_NAME="$2"                          # CDB Name to derive the environment file
ENV_FILE_PATH="${3:-/u01/install/APPS}" # Optional, default /u01/install/APPS
INSTANCE_NUM="${4:-}"                  # Optional, detect dynamically if not provided

# Auto-detect instance number if not provided
if [[ -z "$INSTANCE_NUM" ]]; then
    if [[ "$(hostname)" =~ 02 ]]; then
        INSTANCE_NUM=2
    else
        INSTANCE_NUM=1
    fi
fi

# Setup Logging
export CUSTDIR=/home/oracle/fsdr/logs
mkdir -p "$CUSTDIR"
LOG_FILE="$CUSTDIR/fndnodeclean_$(date +%Y%m%d_%H%M%S).log"
exec >> "$LOG_FILE" 2>&1

# Lightweight validation log
START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
echo "INFO: Script started at $START_TIME on host $(hostname)"
echo "INFO: Using instance number: $INSTANCE_NUM"

# Retrieve Secret
export SECRET_APPS=$(oci secrets secret-bundle get --raw-output --secret-id "$SECRET_APPS_OCID" --query "data.\"secret-bundle-content\".content" | base64 -d)

# Source Apps Tier Environment
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

# Fetch DB Node
DB_NODE=$(sqlplus -s ${P_APPS_UN}/${SECRET_APPS}@$PDB_NAME <<EOF
set head off verify off feedback off trimspool on
Select trim(host_name) from gv\$instance Where instance_number = $INSTANCE_NUM;
exit;
EOF
)
DB_NODE="$(echo "$DB_NODE" | xargs)"

export ORACLE_HOME=/u01/app/oracle/product/19.0.0.0/dbhome_1
export PATH=$ORACLE_HOME/bin:$PATH

# Prepare Remote Script
temp_remote_script="/tmp/fndnodeclean_remote.sh"
rm -f "$temp_remote_script"

cat > "$temp_remote_script" << REMOTE_SCRIPT_EOF
#!/bin/bash
set -euo pipefail
set -x

# Setup CDB Environment
cdb_env_file="\$ORACLE_HOME/${CDB_NAME}_\$(hostname).env"
if [[ -f "\$cdb_env_file" ]]; then
    . "\$cdb_env_file"
    echo "INFO: CDB Environment sourced from \$cdb_env_file."
else
    echo "ERROR: CDB Environment file not found: \$cdb_env_file" >&2
    exit 1
fi

# Check PDB status
pdb_status=$(sqlplus -s / as sysdba <<SQL
    set pages 0 feedback off verify off heading off echo off
    select open_mode from v\$pdbs where name = '${PDB_NAME}';
    exit
SQL
)
pdb_status="$(echo "$pdb_status" | xargs)"
echo "INFO: Current PDB Status: \$pdb_status"
pdb_status="\$(echo "\$pdb_status" | xargs)"

if [[ "\$pdb_status" == "MOUNTED" ]]; then
    echo "INFO: Opening PDB \$PDB_NAME READ WRITE..."
    sqlplus -s / as sysdba <<-SQL
        alter pluggable database \$PDB_NAME open read write instances=all services=all;
        exit
SQL
fi

# Setup PDB Environment
pdb_env_file="\$ORACLE_HOME/${PDB_NAME}_\$(hostname).env"
if [[ -f "\$pdb_env_file" ]]; then
    . "\$pdb_env_file"
    echo "INFO: PDB Environment sourced from \$pdb_env_file."
else
    echo "ERROR: PDB Environment file not found: \$pdb_env_file" >&2
    exit 1
fi

# Run FND Node Cleanup
echo "INFO: Running FND Node Cleanup..."
sqlplus -s \${P_APPS_UN}/\${SECRET_APPS}@\${PDB_NAME} <<-CLEAN
    WHENEVER SQLERROR EXIT FAILURE;
    EXEC fnd_net_services.remove_system ('\$PDB_NAME');
    EXEC fnd_conc_clone.setup_clean;
    EXEC ad_zd_fixer.clear_valid_nodes_info;
    COMMIT;
CLEAN
REMOTE_SCRIPT_EOF

# Execute Remote Script
scp "$temp_remote_script" "oracle@$DB_NODE:$(basename "$temp_remote_script")"
ssh "oracle@$DB_NODE" "bash -s" << EOSSH
export SECRET_APPS='$SECRET_APPS'
export PDB_NAME='$PDB_NAME'
export CDB_NAME='$CDB_NAME'
export CONTEXT_FILE='$CONTEXT_FILE'
export ORACLE_HOME='$ORACLE_HOME'
export P_APPS_UN='$P_APPS_UN'
bash "$(basename "$temp_remote_script")"
EOSSH

remote_status=$?
if [[ $remote_status -ne 0 ]]; then
    echo "ERROR: FND node cleanup failed on $DB_NODE. Check logs at $CUSTDIR" >&2
    exit 1
else
    echo "INFO: FND node cleanup completed successfully. Logs available at $CUSTDIR"
    exit 0
fi