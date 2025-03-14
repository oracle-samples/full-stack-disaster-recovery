# README
## Volume group cmk key and policy update scripts for OCI Full Stack Disaster Recovery

## Introduction
These scripts provide essential tools for managing and updating encryption keys and backup policies for Oracle Cloud Infrastructure (OCI) Volume Group members during Disaster Recovery (DR) scenarios. By automating these tasks, you can ensure your recovery processes are efficient, consisten, and compliant with your organizational policies.

## Overview
The scripts are designed toL
- Update encryption keys (Customer-Managed Keys) for volumes within a Volume Group.
- Apply user-defined backup policies to Volume Groups after executing a DR plan.

These tools simplify administrative efforts, minimize human errors, and enhance operational reliability.

## Prerrequisites

### General Requirements
- **Execution Environment**: Supported environments include local systems, OCI instances (direct or via user-defined DR steps), and Cloud Shell.
- **Python Version**: Tested with Python 3.6.8 and higher.
- **OCI CLI Setup**:
  - For local or OCI instance executions, configure OCI CLI with a profile (`--profile`) and configuration file (`--config_file`).
  - For Cloud Shell, the `--profile` parameter must specify the full region name (e.g., `--profile us-ashburn-1`).
  - For OCI instance executions, Instance Principal authentication can be used instead of `--profile` and `--config_file` parameters, provided the instance has the necessary permissions
- **Volume Group Membership**: Ensure all target volues are part of a Volume Group and associated with the primary DR Protection Group. Volumes may include both block and boot volumes.

Refer to the [OCI CLI Installation Guide](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm) for setup instructions.

### Environment Setup

#### On OCI Instances or User-Defined Steps

Use the following commands to set up the environment:

```bash
sudo dnf install python3.12
sudo alternatives --set python3 /usr/bin/python3.12
sudo dnf install python3-pip python3-setuptools python3-wheel
python3 -m ensurepip --default-pip
python3 -m pip install --user oci
```

For user defined step, create a bash script as follows:
```
#!/bin/bash
python3 bss_update_cmk_multi_key.py "$@"
```

Ensure the OCI instance has `ocarun` permissions enabled.

### User-Defined Steps Execution Considerations
It is recommended to execute the scripts at the very end of the DR plan to ensure all the other recovery steps are completed. However, the scripts can also be executed after `Compute Instances - Launch` / `Compute Instances - Start` steps if required.

#### For Local Execution

It is recommended to use a virtual environment:

```bash
python3 -m venv venv 
source venv/bin/activate    
pip install oci --force
pip install oci-cli --force
```

### Scripts and Usage

## bss_update_cmk_single_key.py
This script updates the enryption key for all volumes in a Volume Group after a DR plan execution. It applies the same key to every volume in the volume group.

**Usage:**
```bash
bss_update_cmk_single_key.py --dr_protection_group_id <drpg_ocid> --kms_key_id <key_ocid> [--profile PROFILE] [--config_file config_file] [--service_endpoint service_endpoint]
```
**Parameters:**
- **Required:**
  - `--dr_protection_group_id`: Disaster recovery protection group OCID
  - `--kms_key_id`: Encryption key OCID

- **Optional:**
  - `--profile`: OCI cli profile. In case of Cloud Shell execution this must be the full region name
  - `--config_file`: OCI cli config file (default /etc/opc/config)
  - `--service_endpoint`: OCI service endpoint for disaster recovery API calls

## bss_update_cmk_multi_key.py
This script uses freeform tags to determine and update encryption keys for individual volumes within a Volume Group. Each volume must have appropriate freeform tags for the primary and standby keys.

**Usage:**
```bash
bss_update_cmk_multi_key.py --dr_protection_group_id <drpg_ocid> --freeform_tag_key FREEFORM_TAG [--profile PROFILE] [--config_file config_file] [--service_endpoint service_endpoint]
```
**Parameters:**
- **Required:**
  - `--dr_protection_group_id`: Disaster recovery protection group OCID
  - `--freeform_tag_key`: Freeform tag where kms key OCID is stored

- **Optional:**
  - `--profile`: OCI cli profile. In case of Cloud Shell execution this must be the full region name
  - `--config_file`: OCI cli config file (default /etc/opc/config)
  - `--service_endpoint`: OCI service endpoint for disaster recovery API calls

## bss_update_backup_policy_vg.py
This script assigns a user-defined backup policy to Volume Groups after a DR plan execution. Note that it does not support Oracle-defined policies.

**Usage:**
```bash
bss_update_backup_policy_vg.py --dr_protection_group_id <drpg_ocid> --backup_policy_id <backup_policy_ocid> [--profile PROFILE] [--config_file config_file] [--service_endpoint service_endpoint]
```

**Parameters:**
- **Required:**
  - `--dr_protection_group_id`: Disaster recovery protection group OCID
  - `--backup_policy_id`: Backup policy OCID

- **Optional:**
  - `--profile`: OCI cli profile. In case of Cloud Shell execution this must be the full region name
  - `--config_file`: OCI cli config file (default /etc/opc/config)
  - `--service_endpoint`: OCI service endpoint for disaster recovery API calls

### Common Errors and Troubleshooting
#### Invalid OCID Format
Ensure that OCIDs provided for `--dr_protection_group_id`, `--kms_key_id` and `--backup_policy_id` follow the correct format. <br>

#### Incorrect OCI CLI Configuration
Verify the following:
- OCI CLI is correcly installed and configured.
- The correct profile and config file are specified.

#### Logging and Debugging

To enable detailed logs, adjust the logging level in the scripts:

```python
logging.basicConfig(level=logging.DEBUG)
```

## License

Copyright (c) 2025 Oracle and/or its affiliates.

Released under the Universal Permissive License v1.0 as shown at
<https://oss.oracle.com/licenses/upl/>.