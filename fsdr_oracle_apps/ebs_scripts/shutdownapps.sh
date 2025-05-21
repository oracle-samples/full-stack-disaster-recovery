#!/bin/bash
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
#==============================================================
# Script: shutdownapps.sh
# Purpose: Shutdown Applications Tier for EBS FSDR with secret handling
# Author: Chandra Dharanikota
# Version: 2.0
#==============================================================

set -euo pipefail

# Arguments
SECRET_APPS_OCID="$1"
SECRET_WEBLOGIC_OCID="$2"
ENV_FILE_PATH="${3:-/u01/install/APPS}"

# Fetch secrets
SECRET_APPS=$(oci secrets secret-bundle get --raw-output --secret-id "$SECRET_APPS_OCID" --query "data.\"secret-bundle-content\".content" | base64 -d) || {
    echo "ERROR: Failed to fetch APPS password."
    exit 1
}

SECRET_WEBLOGIC=$(oci secrets secret-bundle get --raw-output --secret-id "$SECRET_WEBLOGIC_OCID" --query "data.\"secret-bundle-content\".content" | base64 -d) || {
    echo "ERROR: Failed to fetch WebLogic password."
    exit 1
}

# Environment setup
if [[ -f "$ENV_FILE_PATH/EBSapps.env" ]]; then
    . "$ENV_FILE_PATH/EBSapps.env" run
else
    echo "ERROR: Environment file not found at $ENV_FILE_PATH/EBSapps.env"
    exit 1
fi

# Stop Apps Tier
echo "INFO: Shutting down Applications tier..."
{ echo apps; echo "$SECRET_APPS"; echo "$SECRET_WEBLOGIC"; } | "$ADMIN_SCRIPTS_HOME/adstpall.sh" -nopromptmsg || {
    echo "ERROR: Shutdown failed."
    exit 1
}

echo "INFO: Applications tier shutdown completed."