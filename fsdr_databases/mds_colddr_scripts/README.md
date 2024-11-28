# README  

## Overview

This repository contains a collection of scripts designed to facilitate Copy / Create / Restore Backup tasks for OCI MySQL Database System related to Automate Cold Disaster Recovery. Below is a detailed description of each script, its purpose, and how it is used.  

---

## Scripts  

### 1. **`mds_copy_bkp.py`**

**Description:**

This script copies a MySQL Database backup to a remote OCI region, facilitating cross-region data redundancy and disaster recovery readiness.

**Usage:**

```bash  
mds_copy_bkp.py db_source_label dest_region 

Positional arguments:
  db_source_label The system label of the source MySQL system is to be copied. System Label from the config file (config.py).
  dest_region      Destination OCI Region
```

### 2. **`mds_create_bkp.py`**

**Description:**

This script creates a manual MySQL database backup, ensuring data is securely stored for recovery purposes.

**Usage:**

```bash  
mds_create_bkp.py db_source_label 

Positional arguments:
  db_source_label  System Label of the Source MySQL system. System Label from the config file (config.py).
```

### 3. **`mds_list_config.py`**

**Description:**

This script lists the MySQL DB Systems specified in the configuration file (config.py) for streamlined access and ease of management.

**Usage:**

```bash  
mds_list_config.py
```

**Dependencies:**

This script requires the tabulate module.

```bash
pip install tabulate
```

### 4. **`mds_restore_bkp.py`**

**Description:**

This script restores a MySQL database backup to a different OCI region, enabling cross-region recovery and redundancy.

**Usage:**

```bash  
mds_restore_bkp.py db_source_label dest_subnet_id [dest_ad_number] [--config] [--terminate] 

Positional arguments:
  db_source_label The system label of the source MySQL system is to be restored. System Label from the config file. (config.py)
  dest_subnet_id   Destination Subnet OCID
  dest_ad_number   Destination Availability Domain Number (Default value 1 for AD1)

Optional arguments:
  --config         Update config file with the new OCID of the restored MDS
  --terminate      Terminate the Source MDS after a Restore (Switchover scenario)
```

### 5. **`mds_update_dns.py`**

**Description:**

This script updates the DNS record for the MySQL Database System endpoint within the OCI DNS Private Zone in both regions. For seamless execution, the DNS view OCID should be specified in the config.py file.

**Usage:**

```bash  
mds_update_dns.py mds_label zone_name domain_name remote_region [--remote]

Positional arguments:
  mds_label      System Label of MySQL to get the Endpoint IP
  zone_name      The DNS Zone Name
  domain_name    The DNS record to be updated
  remote_region  Remote OCI Region (Old Primary)

Optional arguments:
  --remote       Update DNS in the Remote Region as well (Only for Switchover Scenario)
```

## Configuration file (config.py)

This file contains the OCIDs for the MySQL Database System and the compartment where the MySQL System resides. Each entry is referenced with a descriptive label, consistently used across all the previous scripts for simplicity and clarity.

It also includes the Private DNS View OCIDs for both OCI regions, which the mds_update_dns.py script utilizes to update DNS records seamlessly.

## License

Copyright (c) 2024 Oracle and its affiliates.

Released under the Universal Permissive License v1.0 as shown at <https://oss.oracle.com/licenses/upl/>.
