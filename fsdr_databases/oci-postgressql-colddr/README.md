# README  

## Disclaimer

The scripts provided are intended as general examples and may not be fully suited for your specific use case. They should be thoroughly tested and reviewed before being implemented in a production environment. By using these scripts, you acknowledge that they are provided "as-is," without any warranty or support. You assume full responsibility for any issues that may arise from their use. No support is offered, and the scripts are not guaranteed to work in every situation. Proceed with caution and test thoroughly.

## Overview

This repository contains a collection of scripts designed to facilitate Create / Copy / Restore Backup tasks for OCI Database with PostgreSQL related to Automate Cold Disaster Recovery. Below is a detailed description of each script, its purpose, and how it is used.

---

## Pre-requisities

### Postgres Policies Required

- Allow dynamic-group <dynamic-group> to manage postgres-db-systems in compartment id <compartment_ocid>
- Allow dynamic-group <dynamic-group> to manage postgres-backups in compartment id <compartment_ocid>
- Allow dynamic-group <dynamic-group> to use virtual-network-family in compartment id <compartment_ocid>
- Allow dynamic-group <dynamic-group> to read secret-family in compartment id <compartment_ocid>
- Allow dynamic-group <dynamic-group> to read vaults in compartment id <compartment_ocid>

### FSDR Policies Required

- Allow group <group> to manage buckets in compartment <compartment name>
- Allow group <group> to manage objects in compartment <compartment name>
- Allow group <group> to manage instance-family in compartment <compartment name>
- Allow group <group> to manage instance-agent-command-family in compartment <compartment name>
- Allow group <group> to manage volume-family in compartment <compartment name>

## Scripts  

### 1. Wrapper script - **`psql_exec_cold_dr.py`**

**Description:**

This script serves as a control wrapper for running specific OCI Disaster Recovery operations, including switchover, failover, and drills.
Use it alongside psql_update_dns to execute a comprehensive disaster recovery plan for OCI Database with PostgreSQL.

**Usage:**

```bash  
psql_exec_cold_dr.py -c CONFIG_FILE [-o {drill,switchover,failover,terminate}] [-t TIMEOUT] [dest_ad_number]

positional arguments:
  dest_ad_number        Destination Availability Domain Number (Default value is 1 for AD1)

arguments:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -o {drill,switchover,failover,terminate}, --operation {drill,switchover,failover,terminate}
                        Specify the operation type to execute. Default operation is drill (Dry Run).
  -t TIMEOUT, --timeout TIMEOUT
                        Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.
```

### 2. Create Backup (Primary Region) - **`psql_create_bkp.py`**

**Description:**

This script creates a manual backup of an OCI Database with PostgreSQL, ensuring data is securely stored for recovery purposes.

**Usage:**

```bash  
psql_create_bkp.py -c CONFIG_FILE [-t TIMEOUT]

arguments:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -t TIMEOUT, --timeout TIMEOUT
                        Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.
```

### 3. Copy Configuration (To DR Region) - **`psql_copy_config.py`**

**Description:**

This script copies the current OCI Database with PostgreSQL Configuration and re-creates it in the target region. 
A backup file is created with the parameters overriden by the administrator.

**Usage:**

```bash  
psql_copy_config.py -c CONFIG_FILE [-t TIMEOUT]

arguments:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -t TIMEOUT, --timeout TIMEOUT
                        Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.
```

### 4. Copy Backup (To DR Region) - **`psql_copy_bkp.py`**

**Description:**

This script copies the last Backup of an OCI Database with PostgreSQL to a remote OCI region, facilitating cross-region data redundancy and disaster recovery readiness.

**Usage:**

```bash  
psql_copy_bkp.py -c CONFIG_FILE [-t TIMEOUT]

arguments:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -t TIMEOUT, --timeout TIMEOUT
                        Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.
```

### 5. Restore Backup (In DR Region) - **`psql_restore_bkp.py`**

**Description:**

This script restores the last Backup of an OCI Database with PostgreSQL to a different OCI region, enabling cross-region recovery and redundancy.

**Usage:**

```bash  
psql_restore_bkp.py -c CONFIG_FILE [-o {drill,switchover,failover}] [-t TIMEOUT] [dest_ad_number]

positional arguments:
  dest_ad_number        Destination Availability Domain Number (Default value is 1 for AD1)

arguments:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -o {drill,switchover,failover}, --operation {drill,switchover,failover}
                        Specify the operation type to execute. Default operation is drill (Dry Run).
  -t TIMEOUT, --timeout TIMEOUT
                        Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.
```

### 6. Terminate DB - **`psql_terminate_db.py`**

**Description:**

This script Terminate an OCI Database with PostgreSQL in the context of a Disater Recovery (Switchover or a Dry Run).

The OCI Database with PostgreSQL to be terminated is identified in the json config file through the "psql_db_to_terminate_id" key, which is populated during the restore phase.

If the drill (Default) option is specified during the restore phase, the OCI Database with PostgreSQL to be terminated (in the dry run) will be the same database that was just restored.

If the switchover option is specified during the restore phase, the OCI Database with PostgreSQL to be terminated (during the switchover) will be the Source OCI Database with PostgreSQL.

**Usage:**

```bash  
psql_terminate_db.py -c CONFIG_FILE [-t TIMEOUT]

arguments:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -t TIMEOUT, --timeout TIMEOUT
                        Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.
```

### 7. **`psql_update_dns.py`**

**Description:**

This script updates the DNS record for the OCI Database with PostgreSQL endpoint within the OCI DNS Private Zone in both regions. The DNS zone OCID should be specified in the json config file for seamless execution.

>**Note:** This assumes that an A record is configured in OCI DNS Private Zone in each region, pointing to the current primary PostgreSQL endpoint.

**Usage:**

```bash  
psql_update_dns.py -c CONFIG_FILE -d DOMAIN_NAME [-o {startdrill,stopdrill,switchover,failover}] [-t TTL]

arguments:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -d DOMAIN_NAME, --domain_name DOMAIN_NAME 
                        The DNS record to be updated
  -o {startdrill,stopdrill,switchover,failover}, --operation {startdrill,stopdrill,switchover,failover}
                        Specify the operation type to execute. Default operation is startdrill (Dry Run).
  -t TTL, --ttl TTL     Specify the TTL in seconds for the DNS record. Default to 300 seconds.
```

The `startdrill` (Dry Run) operation will update the DNS record in the DR region with the IP address of the PostgreSQL endpoint restored during the `drill` operation, initiated with the `psql_restore_bkp.py` script.

The `stopdrill` operation will revert the DNS record in the DR region with the IP address of the primary PostgreSQL endpoint in the current primary region.

The `switchover` operation will update the DNS record in **Both** OCI regions with the IP address of the new primary PostgreSQL endpoint restored during the `switchover` operation, initiated with the `psql_restore_bkp.py` script.

The `failover` operation will update the DNS record in DR region with the IP address of the new primary PostgreSQL endpoint restored during the `failover` operation, initiated with the `psql_restore_bkp.py` script.

## Configuration file (config/xxxx.json)

This JSON file contains information related to the setup and configuration of the OCI Database with PostgreSQL and the DNS zones across multiple regions. The structure is divided into two main sections: psql_db_details and dns_details

### psql_db_details

This section contains details about the OCI Database with PostgreSQL, including information on its identity, location, and subnet configuration across two regions.

- `id`: This represents the OCID of the OCI Database with PostgreSQL.
- `compartment_id`: The OCID of the compartment that the OCI Database with PostgreSQL belongs to.
- `primary_region`: Indicates the primary region where the OCI Database with PostgreSQL is deployed.
- `standby_region`: Indicates the standby region for disaster recovery or failover.
- `primary_subnet_id`: The OCID of the subnet in the primary region where the OCI Database with PostgreSQL is located.
- `standby_subnet_id`: The OCID of the subnet in the standby region.
- `admin_user`: The Administartor user of the  OCI Database with PostgreSQL.
- `primary_admin_secrect_id`: The OCID of the secret in the primary region containing the admin password of the OCI Database with PostgreSQL.
- `standby_admin_secrect_id`: The OCID of the secret in the standby region containing the admin password of the OCI Database with PostgreSQL.
- `psql_db_to_terminate_id`: This field is intended to store the OCID of the OCI Database with PostgreSQL that may need to be terminated. **it is populated by the `psql_restore_bkp.py` script.**
- `psql_config_to_terminate_id`: This field is intended to store the OCID of the OCI Database with PostgreSQL Configuration that may need to be terminated. **it is populated by the `psql_restore_bkp.py` script.**

The following keys are refreshed by the **`psql_create_bkp.py script`.** You can keep them empty for the first execution.

- `display_name`: ""
- `primary_config_id`: ""
- `db_version`: ""
- `instance_count`:
- `instance_memory_size_in_gbs`:
- `instance_ocpu_count`:
- `shape`: ""
- `storage_details`:
  - `iops`:
  - `is_regionally_durable`:
  - `system_type`: ""
- `management_policy`:
  - `backup_policy`:
    - `backup_start`:
    - `copy_policy`:
      - `compartment_id`: ""
    - `kind`: ""
    - `retention_days`:
  - `maintenance_window_start`: ""

### dns_details

This section contains information about DNS (Domain Name System) configurations for two regions.

- **`regions`**: This is a list containing DNS zone details for multiple regions.
  - `region`: Specifies the region name for which the DNS zone configuration applies.
  - `dns_zone_id`: The unique OCID for the DNS zone in the respective region.
