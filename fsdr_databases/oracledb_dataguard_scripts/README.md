# OCI Full Stack Disaster Recovery: Database Handler Scripts

This repository provides scripts to facilitate the integration of Oracle Cloud Infrastructure (OCI) Full Stack Disaster Recovery (DR) with Oracle Data Guard for database role transitions. The scripts automate operations such as switchover, failover, and snapshot conversions, ensuring seamless disaster recovery processes.

## Prerequisites

Before utilizing these scripts, ensure the following prerequisites are met:

### 1. Administrator Access or Required OCI IAM Policies

You must have administrator privileges or configure the necessary OCI Identity and Access Management (IAM) policies and dynamic groups to use OCI Full Stack DR. The database handler script internally launches an OCI container instance, so appropriate policies are required.

> **Note**: Replace all occurrences of `<compartment_ocid>` and `<compartment_name>` with your actual OCI compartment OCID and name.

#### Create a Dynamic Group

Create a dynamic group named `FullStackDR_Database_DG` with the following matching rules:

```
Any {instance.compartment.id = '<compartment_ocid>'}
Any {resource.type = 'instance', resource.compartment.id = '<compartment_ocid>'}
Any {resource.type = 'computecontainerinstance', resource.compartment.id = '<compartment_ocid>'}
Any {resource.type = 'drprotectiongroup', resource.compartment.id = '<compartment_ocid>'}
```

#### Create an OCI IAM Policy

Create a policy named `FullStackDR_Database_Group_Policies` with the following allow statements:

```
Allow dynamic-group FullStackDR_Database_DG to read secret-family in compartment <compartment_name>
Allow dynamic-group FullStackDR_Database_DG to manage virtual-network-family in compartment <compartment_name>
Allow dynamic-group FullStackDR_Database_DG to manage instance-agent-command-family in compartment <compartment_name>
Allow dynamic-group FullStackDR_Database_DG to manage instance-agent-command-execution-family in compartment <compartment_name>
Allow dynamic-group FullStackDR_Database_DG to manage objects in compartment <compartment_name>
Allow dynamic-group FullStackDR_Database_DG to manage database-family in compartment <compartment_name>
Allow dynamic-group FullStackDR_Database_DG to manage compute-container-family in compartment <compartment_name>
```

For more information, refer to the [OCI Full Stack DR Policies Documentation](https://blogs.oracle.com/maa/iam-policies-fullstackdr).

### 2. Access to Run Commands on OCI Compute Instances

Set up the run command prerequisites, as user-defined plan groups are used for running scripts during DR operations. For more information, see [Running Commands on an Instance](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/runcommands.htm).

A compute instance, referred to as the **Jumphost**, will host the database handler scripts and execute them using the **Run Command** feature.

### 3. Install OCI CLI on the Jumphost in Both Regions

Install the OCI CLI on the jumphosts in both regions based on their operating systems. Ensure that OCI CLI commands can be invoked using instance principals. For installation instructions, see [OCI CLI Installation](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm).

### 4. Set Up VCNs in Both Regions with Remote VCN Peering

Create Virtual Cloud Networks (VCNs) in both the primary and standby regions and set up remote VCN peering. This is required for setting up cross-region Oracle Data Guard. For more information, see [OCI Base DB Networking Configuration](https://docs.oracle.com/en-us/iaas/Content/Database/Tasks/overview.htm).

### 5. Manual Oracle Data Guard Configuration

Manually configure Oracle Data Guard based on your requirements using Oracle Data Guard broker. For more information, see [Oracle Data Guard Broker](https://docs.oracle.com/en/database/oracle/oracle-database/19/dgbkr/index.html) and [Oracle Clusterware](https://docs.oracle.com/en/database/oracle/oracle-database/19/cwadd/index.html).

### 6. Install Git on the Jumphost

Install Git on the jumphosts in both regions to download the database handler scripts from GitHub.

**For Oracle Linux / Red Hat Enterprise Linux / CentOS:**
```bash
sudo yum install git -y
```

**For Ubuntu / Debian:**
```bash
sudo apt-get update
sudo apt-get install git -y
```

Verify the installation:
```bash
git --version
```

### 7. Download the Database Handler Scripts to the Jumphost

- Clone the Oracle Data Guard database handler scripts from the GitHub repository:
  ```bash
  git clone https://github.com/oracle-samples/full-stack-disaster-recovery.git
  cd full-stack-disaster-recovery/fsdr_databases/oracledb_dataguard_scripts
  ```
- Copy the scripts to the `/home/opc/` directory (or any preferred path) on the jumphosts in both regions.
- Ensure the files have executable permissions:
  ```bash
  chmod +x *.sh *.py
  ```
- The `full_stack_dr_non_std_db_handler.py` script handles Oracle Data Guard role transitions. Associated bash scripts are provided as templates and can be modified to suit specific requirements. **Do not modify** the Python role change script itself.

### 8. Create OCI Vault and Secrets

Create an OCI Vault and store database credentials as secrets in both regions.

- Create an OCI Vault in each region using the OCI Console or CLI.
- Create a secret within the vault to store the `SYS` user password for the database.

### 9. Connectivity Checks from the Jumphost

Ensure the OCI Database service, OCI Vault service, and OCI container instance service are accessible from the compute instance. This is required because the OCI Full Stack DR scripts perform introspection to fetch database details from both **Primary** and **Standby** regions.

Run the following commands from the jumphost:

```bash
# Primary Region
curl -v telnet://database.<primary_region>.oraclecloud.com:443
curl -v telnet://secrets.vaults.<primary_region>.oci.oraclecloud.com:443
curl -v telnet://iaas.<primary_region>.oraclecloud.com:443
curl -v telnet://compute-containers.<primary_region>.oci.oraclecloud.com:443

# Standby Region
curl -v telnet://database.<standby_region>.oraclecloud.com:443
curl -v telnet://secrets.vaults.<standby_region>.oci.oraclecloud.com:443
curl -v telnet://iaas.<standby_region>.oci.oraclecloud.com:443
curl -v telnet://compute-containers.<standby_region>.oci.oraclecloud.com:443
```

> **Note**: Replace `<primary_region>` and `<standby_region>` with actual OCI region identifiers. For example:
> - `us-ashburn-1` for Ashburn
> - `us-phoenix-1` for Phoenix
>
> For a complete list, see [OCI Region Identifiers](https://docs.oracle.com/en-us/iaas/Content/General/Concepts/regions.htm).

> **Expected Output**: Each command should return a message similar to `Connected to ...`.
>
> If any connection fails, check the security lists, route tables, and service gateway configuration of the VCN/subnets of the jumphost.

### 10. Create Object Storage Buckets

Create OCI Object Storage buckets in the primary and standby regions to store logs generated by OCI Full Stack DR during recovery operations. For more information, see [Preparing Log Location for Operation Logs](https://docs.oracle.com/en-us/iaas/Content/FullStackDR/Tasks/prepare-log-location.htm).

## Database Handler Script Usage and Customization

The database handler scripts support various `--db_operation` options:

- `SWITCHOVER`
- `SWITCHOVER_PRECHECK`
- `FAILOVER`
- `FAILOVER_PRECHECK`
- `CONVERT_PHYSICAL_TO_SNAPSHOT_STANDBY`
- `CONVERT_PHYSICAL_TO_SNAPSHOT_STANDBY_PRECHECK`
- `REVERT_SNAPSHOT_TO_PHYSICAL_STANDBY_PRECHECK`
- `REVERT_SNAPSHOT_TO_PHYSICAL_STANDBY`

### Script Usage

The Python script `full_stack_dr_non_std_db_handler.py` requires the following parameters:

```bash
usage: full_stack_dr_non_std_db_handler.py [-h] --database_ocid DATABASE_OCID
                                           --vault_ocid VAULT_OCID
                                           --db_operation DB_OPERATION
                                           --region REGION
                                           --primary_db_unique_name PRIMARY_DB_UNIQUE_NAME
                                           --standby_db_unique_name STANDBY_DB_UNIQUE_NAME
                                           --drpg_ocid DRPG_OCID
                                           [--auth_type AUTH_TYPE]
                                           [--delegation_token DELEGATION_TOKEN]
                                           [--log_level LOG_LEVEL]
```

**Required Arguments:**
- `--database_ocid DATABASE_OCID` - Database OCID
- `--vault_ocid VAULT_OCID` - Standby VaultSecret OCID
- `--db_operation DB_OPERATION` - Database Operation (see supported operations above)
- `--region REGION` - Region Name (e.g., `us-phoenix-1`, `us-ashburn-1`)
- `--primary_db_unique_name PRIMARY_DB_UNIQUE_NAME` - Primary Database Unique Name
- `--standby_db_unique_name STANDBY_DB_UNIQUE_NAME` - Standby Database Unique Name
- `--drpg_ocid DRPG_OCID` - DrProtectionGroup OCID

**Optional Arguments:**
- `-h, --help` - Show this help message and exit
- `--auth_type AUTH_TYPE` - Authentication Type (default: `INSTANCE_PRINCIPAL`)
- `--delegation_token DELEGATION_TOKEN` - Token Based Authentication
- `--log_level LOG_LEVEL` - Log Level

### Creating Wrapper Scripts

OCI Full Stack DR expects all required parameters to be passed when running the database handler script. For better usability and repeatability, it is recommended to create a wrapper bash script that:

- Provides the required parameters.
- Enables logging for auditing and troubleshooting.

## Database Switchover Script: `db-switchover-iad-phx.sh`

This script facilitates the switchover of an Oracle Database from the primary region (Ashburn) to the standby region (Phoenix) using Oracle Cloud Infrastructure (OCI) Full Stack Disaster Recovery (DR).

### Script Details

```bash
#!/bin/bash

# Define log file with date and time
LOG_FILE="db-switchover-iad-phx-$(date +%Y%m%d_%H%M%S).log"

# Define Python script and arguments
PYTHON_SCRIPT="full_stack_dr_non_std_db_handler.py"
ARGUMENTS=(
  --database_ocid="ocid1.database.oc1.phx.xxxxxxxx"
  --vault_ocid="ocid1.vaultsecret.oc1.phx.xxxxx"
  --region="us-phoenix-1"
  --primary_db_unique_name="adghol_site0"
  --standby_db_unique_name="adghol_site1"
  --drpg_ocid="ocid1.drprotectiongroup.oc1.phx.axxxxxxax"
  --db_operation="SWITCHOVER"
  --auth_type=INSTANCE_PRINCIPAL
)

# Execute Python script and log output
echo "Executing Python script: $PYTHON_SCRIPT with arguments: ${ARGUMENTS[*]}" | tee -a "$LOG_FILE"
/usr/bin/python3 "$PYTHON_SCRIPT" "${ARGUMENTS[@]}" 2>&1 | tee -a "$LOG_FILE"

echo "Execution completed. Logs saved in $LOG_FILE"
```

### Instructions

1. **Save the Script**:
   - Save the above script as `db-switchover-iad-phx.sh` in the same directory as your database handler scripts.

2. **Make the Script Executable**:
   - Run the following command to grant execute permissions:
     ```bash
     chmod +x db-switchover-iad-phx.sh
     ```

3. **Execute the Script**:
   - To perform the switchover, execute the script:
     ```bash
     ./db-switchover-iad-phx.sh
     ```

### Notes

- **Parameter Values**: Replace the placeholder values (e.g., `ocid1.database.oc1.phx.xxxxxxxx`, `adghol_site0`) with your actual OCI resource identifiers and database unique names.

- **Logging**: The script logs its output to a file named `db-switchover-iad-phx-YYYYMMDD_HHMMSS.log` in the current directory, where `YYYYMMDD_HHMMSS` represents the date and time of execution.

- **Python Script**: Ensure that the `full_stack_dr_non_std_db_handler.py` script is present in the same directory and has the necessary permissions.

- **Instance Principal Authentication**: The script uses `INSTANCE_PRINCIPAL` for authentication. Ensure that the instance has the appropriate IAM policies and dynamic group configurations to perform the required operations.

By using this wrapper script, you can streamline the execution of database role transitions as part of your OCI Full Stack DR plans.

### Creating Scripts for Other Operations

Similar to the switchover script example above, you can create wrapper scripts for other database operations by modifying the `--db_operation` parameter:

- **Switchover Precheck**: Change `--db_operation="SWITCHOVER"` to `--db_operation="SWITCHOVER_PRECHECK"`
- **Failover**: Change `--db_operation="SWITCHOVER"` to `--db_operation="FAILOVER"`
- **Failover Precheck**: Change `--db_operation="SWITCHOVER"` to `--db_operation="FAILOVER_PRECHECK"`
- **Start Drill**: Change `--db_operation="SWITCHOVER"` to `--db_operation="CONVERT_PHYSICAL_TO_SNAPSHOT_STANDBY"`
- **Start Drill Precheck**: Change `--db_operation="SWITCHOVER"` to `--db_operation="CONVERT_PHYSICAL_TO_SNAPSHOT_STANDBY_PRECHECK"`
- **Stop Drill**: Change `--db_operation="SWITCHOVER"` to `--db_operation="REVERT_SNAPSHOT_TO_PHYSICAL_STANDBY"`
- **Stop Drill Precheck**: Change `--db_operation="SWITCHOVER"` to `--db_operation="REVERT_SNAPSHOT_TO_PHYSICAL_STANDBY_PRECHECK"`

Remember to update the script filename and log filename accordingly to reflect the operation being performed.

## DR Plan Script Mapping

### Scenario 1: Database Running in Region 1 (Ashburn) as Primary and Region 2 (Phoenix) as Standby

| DR Plan Type | Target Instance | Script Name | Comment |
|--------------|-----------------|-------------|---------|
| Switchover | script-phx | `db-prechk-switchover-iad-phx.sh` | Prechk DB Switchover from IAD to PHX |
| Switchover | script-phx | `db-switchover-iad-phx.sh` | DB Switchover from IAD to PHX |
| Failover | script-phx | `db-prechk-failover-iad-phx.sh` | Prechk DB Failover from IAD to PHX |
| Failover | script-phx | `db-failover-iad-phx.sh` | DB Failover from IAD to PHX |
| Start drill | script-phx | `db-prechk-startdrill-phx.sh` | Prechk Start DR Drill in PHX |
| Start drill | script-phx | `db-startdrill-phx.sh` | Start DR Drill in PHX |
| Stop drill | script-phx | `db-prechk-stopdrill-phx.sh` | Prechk Stop DR Drill in PHX |
| Stop drill | script-phx | `db-stopdrill-phx.sh` | Stop DR Drill in PHX |

### Scenario 2: Database Running in Region 2 (Phoenix) as Primary and Region 1 (Ashburn) as Standby

| DR Plan Type | Target Instance | Script Name | Comment |
|--------------|-----------------|-------------|---------|
| Switchover | script-iad | `db-prechk-switchover-phx-iad.sh` | Prechk DB Switchover from PHX to IAD |
| Switchover | script-iad | `db-switchover-phx-iad.sh` | DB Switchover from PHX to IAD |
| Failover | script-iad | `db-prechk-failover-phx-iad.sh` | Prechk DB Failover from PHX to IAD |
| Failover | script-iad | `db-failover-phx-iad.sh` | DB Failover from PHX to IAD |
| Start drill | script-iad | `db-prechk-startdrill-iad.sh` | Prechk Start DR Drill in IAD |
| Start drill | script-iad | `db-startdrill-iad.sh` | Start DR Drill in IAD |
| Stop drill | script-iad | `db-prechk-stopdrill-iad.sh` | Prechk Stop DR Drill in IAD |
| Stop drill | script-iad | `db-stopdrill-iad.sh` | Stop DR Drill in IAD |

> **Note**: For better clarity and usability, we have created multiple bash wrapper scripts tailored to specific DR plan types and regions. These scripts use a shared Python script for database role transitions, which you can customize to suit your own requirements and environment.