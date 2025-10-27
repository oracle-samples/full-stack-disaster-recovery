#!/bin/bash

# Define log file with date and time
LOG_FILE="db-switchover-iad-phx-$(date +%Y%m%d_%H%M%S).log"

# Define Python script and argument
PYTHON_SCRIPT="full_stack_dr_non_std_db_handler.py"
ARGUMENT="--database_ocid="ocid1.database.oc1.phx.yyyy" --vault_ocid="ocid1.vaultsecret.oc1.phx.yyyy" --region="us-phoenix-1" --primary_db_unique_name="xxxx" --standby_db_unique_name="xxxx" --drpg_ocid="ocid1.drprotectiongroup.oc1.phx.xxxxx" --db_operation="SWITCHOVER" --auth_type=INSTANCE_PRINCIPAL"
# Execute Python script and log output
echo "Executing Python script: $PYTHON_SCRIPT with argument: $ARGUMENT" | tee -a $LOG_FILE
/usr/bin/python3 $PYTHON_SCRIPT $ARGUMENT 2>&1 | tee -a $LOG_FILE