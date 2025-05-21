#!/bin/bash
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
#==============================================================
# Script: autoconfigapps.sh
# Purpose: Run AutoConfig on Applications Tier for EBS FSDR with secret handling
# Author: Chandra Dharanikota
# Version: 2.0
#==============================================================

set -euo pipefail

# Arguments
SECRET_APPS_OCID="$1"
ENV_FILE_PATH="${2:-/u01/install/APPS}"

# Fetch secret
SECRET_APPS=$(oci secrets secret-bundle get --raw-output --secret-id "$SECRET_APPS_OCID" --query "data.\"secret-bundle-content\".content" | base64 -d) || {
    echo "ERROR: Failed to fetch APPS password secret."
    exit 1
}

# Environment setup
if [[ -f "$ENV_FILE_PATH/EBSapps.env" ]]; then
    . "$ENV_FILE_PATH/EBSapps.env" run
else
    echo "ERROR: Environment file not found at $ENV_FILE_PATH/EBSapps.env"
    exit 1
fi

# Run AutoConfig
echo "INFO: Running AutoConfig..."
{ echo "$SECRET_APPS"; } | "$ADMIN_SCRIPTS_HOME/adautocfg.sh" || {
    echo "ERROR: AutoConfig failed."
    exit 1
}

echo "INFO: AutoConfig completed successfully."
