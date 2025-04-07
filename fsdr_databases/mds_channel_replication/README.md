# README  

## Disclaimer

The scripts provided are intended as general examples and may not be fully suited for your specific use case. They should be thoroughly tested and reviewed before being implemented in a production environment. By using these scripts, you acknowledge that they are provided "as-is," without any warranty or support. You assume full responsibility for any issues that may arise from their use. No support is offered, and the scripts are not guaranteed to work in every situation. Proceed with caution and test thoroughly.

## Overview

This repository contains a collection of scripts designed to facilitate Switchover / Failover tasks for Heatwave MySQL related to Automate Disaster Recovery based on Channel Replication. Below is a detailed description of each script, its purpose, and how it is used.  

---

## Scripts  

### 1. **`mds_switchover.py`**

**Description:**

This script will do a Switchover of a HeatWave MySQL Database System. It performs is a role reversal between the primary database and one of its replicas databases.

**This script should be executed for a planned operation**.

Channel replication should be enable between a primary Heatwave MySQL and a remote replica in another OCI region.

The Replica DB system should be in read-only mode where write operations are not allowed.

The script will do the following steps :

- Connect to primary and replica systems.
- Check replication statuses on primary and replica.
- If the replication is working fine, the script will put the primary in Read Only Mode.
- Fetch for GTID gaps between primary and replica
- Check whether all GTIDs have been successfully applied to the replica.
- If the checks are successful, it will delete the replication channel on replica.
- Create a new replication channel on the new replica (old primary) from the new primary system (old replica).
- Put the new primary in Read Write Mode.
- Update the JSON configuration file to reflect the new setup.

**Usage:**

```bash  
mds_switchover.py -c CONFIG_FILE -to TO_REPLICA

options:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -to TO_REPLICA, --to-replica TO_REPLICA
                        Specify the replica Unique Name (from the JSON configuration file).
```

### 2. **`mds_failover.py`**

**Description:**

This script will do a Failover of a HeatWave MySQL Database System. A failover must be done when the primary database fails or has become unreachable. It will promte the replica to a primary role by putting it in Read Write mode.

**This script should ONLY be executed for unplanned or emergency operations. Failover may or may not result in dataloss.**

Channel replication should be enable between a primary Heatwave MySQL and a remote replica in another OCI region.

The Replica DB system should be in read-only mode where write operations are not allowed.

The script will do the following steps :

- Delete the replication channel on replica.
- Check whether all GTIDs have been successfully applied to the replica.
- Put the new primary in Read Write Mode.
- Update the JSON configuration file to reflect the new setup.

**Usage:**

```bash  
mds_failover.py -c CONFIG_FILE -to TO_REPLICA

options:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -to TO_REPLICA, --to-replica TO_REPLICA
                        Specify the replica Unique Name (from the JSON configuration file).
```

### 3. **`mds_startdrill.py`**

The purpose of this script is to automate the process of restoring a MySQL database backup on the Standby region during a Dry Run (Start Drill plan).

Once the MySQL database System is restored the script will update the `drill_mysql_id` details in the configuration file, to be used by `mds_stopdrill.py` script to terminate the system during the Stop DR Drill plan.

**Usage:**

```bash  
mds_startdrill.py -c CONFIG_FILE -to TO_REPLICA [-b] [-t TIMEOUT] [dest_ad_number]

positional arguments:
  dest_ad_number        Destination Availability Domain Number (Default value is 1 for AD1)

options:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -to TO_REPLICA, --to-replica TO_REPLICA
                        Specify the replica Unique Name.
  -b, --backup          Do a backup of the replica MySQL DB before the restore. (If Automatic Backup not enabled).
  -t TIMEOUT, --timeout TIMEOUT
                        Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.
```

### 4. **`mds_stopdrill.py`**

The purpose of this script is to terminate a MySQL Database System identified in the configuration file with the value of `drill_mysql_id`, during a Dry Run (Stop Drill plan).

Once completed, the script will reset the value of `drill_mysql_id` in the configuration file.

**Usage:**

```bash
mds_stopdrill.py -c CONFIG_FILE -to TO_REPLICA [--force] [--skip] [-t TIMEOUT]

options:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -to TO_REPLICA, --to-replica TO_REPLICA
                        Specify the replica Unique Name.
  --force               Force termination even if delete protection is enabled.
  --skip                Skip final backup before deletion.
  -t TIMEOUT, --timeout TIMEOUT
                        Specify the maximum time to wait, in seconds. Defaults to 1200 seconds.
```

### 5. **`mds_update_dns.py`**

**Description:**

This script updates the DNS record for the MySQL Database System endpoint within the OCI DNS Private Zone in both regions. The DNS zone OCID should be specified in the json config file for seamless execution.

**Usage:**

```bash  
mds_update_dns.py -c CONFIG_FILE -r REGION -d DNS_NAME -g TARGET -t RTYPE [-T TTL]

options:
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify the JSON configuration file.
  -r REGION, --region REGION
                        Specify the Region Identifier from the config file.
  -d DNS_NAME, --dns-name DNS_NAME
                        Specify the DNS Name to update.
  -g TARGET, --target TARGET
                        Specify the DNS Target value.
  -t RTYPE, --rtype RTYPE
                        Specify the DNS Record type. Defaults CNAME.
  -T TTL, --ttl TTL     
                        Specify the TTL in seconds for the DNS record. Defaults to 300 seconds.
```

## Configuration file (xxxx.json)

This JSON file contains details about a MySQL replication setup, including information about the primary database system, its replicas, and DNS configurations for different regions. The structure is divided into two main sections: mysql_db_details and dns_details

**Summary**
The `replication_details` section outlines the MySQL replication configuration, including the primary system and its replica(s) with all required information for connectivity, authentication, and secret management.

The `dns_details` section holds information about the DNS zones in different regions where these systems reside, which is useful for managing DNS records for those systems.

### mysql_db_details

This section holds details about the primary MySQL system and its associated replica(s), including connection details, user credentials, and secrets.

- **`primary`**: This contains details about the primary MySQL database system, which is the main database in the replication setup.
  - `db_unique_name`: A unique identifier for the primary MySQL database system in this configuration file.  
  - `id`: The OCID for the primary MySQL database system, which helps in uniquely identifying the system within Oracle Cloud.
  - `compartment_id`: The OCID for the compartment containing the MySQL database system.
  - `region`: The region where the primary database is hosted.  
  - `endpoint`: The endpoint (DNS record or IP) of the primary database.
  - `port`: The port used to connect to the MySQL server, typically 3306.
  - `admin_user`: The username with administrative privileges.
  - `admin_secrect_id`: The OCID of the secret stored in the Oracle Vault to retrieve the admin password for the primary database.
  - `replication_user`: The username used for MySQL replication.
  - `replication_secrect_id`: The OCID of the secret stored in the Oracle Vault for the replication user’s password.

- **`replicas`**: This section is a list of replica systems, where each replica contains similar details to the primary database. In this case, there is one replica described.
  - `db_unique_name`: A unique identifier for the replica MySQL database system.
  - `id`: The OCID for the replica MySQL database system.
  - `compartment_id`: The OCID for the compartment containing the replica.
  - `region`: The region where the replica is hosted.
  - `endpoint`: The endpoint (DNS record or IP) of the replica database.
  - `port`: The port used to connect to the replica (typically 3306).
  - `admin_user`: The administrative username for the replica.
  - `admin_secrect_id`: The OCID for the admin password secret stored in the Oracle Vault for the replica.
  - `replication_user`: The username used for replication on the replica.
  - `replication_secrect_id`: The OCID for the replication user’s password secret stored in the Oracle Vault for the replica.

### dns_details

This section contains information about DNS settings across different regions, specifically the DNS zone IDs for each region where the database systems are hosted.

- **`regions`**: This is a list containing DNS zone details for multiple regions.
  - `region`: Specifies the region name for which the DNS zone configuration applies.
  - `dns_zone_id`: The unique OCID for the DNS zone in the respective region.
