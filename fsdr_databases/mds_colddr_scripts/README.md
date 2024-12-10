# README  

## Overview

This repository contains a collection of scripts designed to facilitate Copy / Create / Restore Backup tasks for MySQL Database System related to Automate Cold Disaster Recovery. Below is a detailed description of each script, its purpose, and how it is used.  

---

## Scripts  

### 1. **`mds_copy_bkp.py`**

**Description:**

This script copies a MySQL Database backup to a remote OCI region, facilitating cross-region data redundancy and disaster recovery readiness.

**Usage:**

```bash  
mds_copy_bkp.py db_source_label 

positional arguments:
  db_source_label  System Label of the Source MySQL system to be copied. System Label from the config file (config.csv).
```

**Dependencies:**

This script requires the pandas module

```bash
pip install pandas
```

### 2. **`mds_create_bkp.py`**

**Description:**

This script creates a manual backup of the MySQL database, ensuring data is securely stored for recovery purposes.

**Usage:**

```bash  
mds_create_bkp.py db_source_label 

positional arguments:
  db_source_label  System Label of the Source MySQL system. System Label from the config file (config.csv).

optional arguments:
  --stop           Stop the Source MySQL DB before the Backup (Switchover scenario ONLY)
```

**Dependencies:**

This script requires the pandas module

```bash
pip install pandas
```

### 3. **`mds_list_config.py`**

**Description:**

This script lists the MySQL DB Systems specified in the configuration file (config.csv) for streamlined access and ease of management.

**Usage:**

```bash  
mds_list_config.py
```

**Dependencies:**

This script requires pandas and tabulate module

```bash
pip install tabulate
pip install pandas
```

### 4. **`mds_restore_bkp.py`**

**Description:**

This script restores a MySQL database backup to a different OCI region, enabling cross-region recovery and redundancy.

**Usage:**

```bash  
mds_restore_bkp.py db_source_label [dest_ad_number] [--config] [--switch | --drill]

positional arguments:
  db_source_label  System Label of the Source MySQL system to be restored. System Label from the config file. (config.csv)
  dest_ad_number   Destination Availability Domain Number (Default value 1 for AD1)

optional arguments:
  --config         Update config file with the new OCID of the restored MDS
  --switch         TAG the Source MySQL DB to be terminated after a Restore (Switchover scenario)
  --drill          TAG the Target MySQL DB to be terminated after a Restore (Dry Run scenario)
```

**Dependencies:**

This script requires the pandas module

```bash
pip install pandas
```

### 5. **`mds_terminate_db.py`**

**Description:**

This script Terminate a MySQL Database System in the context of a Disater Recovery (Switchover or a Dry Run).

The MySQL database to be terminated is identified in the config.csv file through the "TO TERMINATE" column, which is populated during the restore phase.

If the --drill option is specified during the restore phase, the MySQL database to be terminated (in the dry run) will be the same database that was just restored.

If the --switch option is specified during the restore phase, the MySQL database to be terminated (during the switchover) will be the Source DB.

**Usage:**

```bash  
mds_terminate_db.py db_source_label

positional arguments:
  db_source_label  System Label of the MySQL DB system. System Label from the config file
```

**Dependencies:**

This script requires the pandas module

```bash
pip install pandas
```

### 6. **`mds_update_dns.py`**

**Description:**

This script updates the DNS record for the MySQL Database System endpoint within the OCI DNS Private Zone in both regions. The DNS view OCID should be specified in the config.csv file for seamless execution.

**Usage:**

```bash  
mds_update_dns.py mds_label zone_name domain_name [--remote]

positional arguments:
  mds_label      System Label of the MySQL to get the Endpoint IP
  zone_name      The DNS Zone Name
  domain_name    The DNS record to be updated

optional arguments:
  --remote       Update DNS in the Remote Region as well (Only for Switchover Scenario)
```

**Dependencies:**

This script requires the pandas module

```bash
pip install pandas
```

## Configuration file (config.csv)

This file contains the OCIDs for the MySQL Database System, the Subnet OCIDs in both regions and the compartment where the MySQL System resides. Each entry is referenced with a descriptive label, which is consistently used across all the previous scripts for simplicity and clarity.

It also includes the Private DNS View OCIDs for both OCI regions, which are utilized by the mds_update_dns.py script to update DNS records seamlessly.

## License

Copyright (c) 2024 Oracle and/or its affiliates.

Released under the Universal Permissive License v1.0 as shown at <https://oss.oracle.com/licenses/upl/>.
