## Disclaimer

The scripts provided are intended as general examples and may not be fully suited for your specific use case. They should be thoroughly tested and reviewed before being implemented in a production environment. By using these scripts, you acknowledge that they are provided "as-is," without any warranty or support. You assume full responsibility for any issues that may arise from their use. No support is offered, and the scripts are not guaranteed to work in every situation. Proceed with caution and test thoroughly.

## Oracle E-Business Suite scripts for OCI Full Stack Disaster Recovery

Full Stack Disaster Recovery (is an Oracle Cloud Infrastructure (OCI) orchestration and management service for automating disaster recovery across all layers—application, middleware, and database. These scripts assist in automating common E-Business Suite (EBS) DR operations such as application shutdown/startup, configuration updates, and secure file synchronization.


## Prerequisites

1. Deploy Oracle E-Business Suite in OCI with Production and Disaster Recovery setup using one of the following:
   - [Deploy EBS for DR using BaseDB: Doc ID 2875417.1](https://support.oracle.com/epmos/faces/DocumentDisplay?id=2875417.1)
   - [Deploy EBS for DR using ExaCS: Doc ID 2919723.1](https://support.oracle.com/epmos/faces/DocumentDisplay?id=2919723.1)

2. Prepare both Source (Primary) and Standby OCI regions and ensure required IAM policies are configured:
   - [Full Stack DR IAM Policy Documentation](https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/disaster-recovery-policies.html)
   - [IAM Policy Setup Blog](https://blogs.oracle.com/maa/post/iam-policies-fullstackdr)


## EBS Scripts

Automation scripts for key operations in EBS Full Stack DR. All scripts are **compatible with Bash** and can be executed using the **`/bin/sh` shell** on Oracle Linux-based systems where `/bin/sh` is symlinked to Bash.

### Execution Format:

Use the following syntax for all scripts:
```sh
/bin/sh script_name.sh <arguments>
```

### Available Scripts:

1. **shutdownapps.sh** – Securely shuts down EBS application services.  
   - Usage: `/bin/sh shutdownapps.sh <SECRET_APPS_OCID>`

2. **fsdr-rsync-ebs.sh** – Enables/disables rsync-based file sync during DR transitions.  
   - Usage: `/bin/sh fsdr-rsync-ebs.sh enable <EBS_IP>`  
   - Usage: `/bin/sh fsdr-rsync-ebs.sh disable <EBS_IP>`

3. **autoconfigapps.sh** – Executes AutoConfig on the application tier with secret OCID handling.  
   - Usage: `/bin/sh autoconfigapps.sh <SECRET_APPS_OCID>`

4. **startapps.sh** – Securely starts EBS application services.  
   - Usage: `/bin/sh startapps.sh <SECRET_APPS_OCID> <SECRET_WEBLOGIC_OCID>`

5. **dbtxkconfig.sh** – Automates configuration of DB-tier TXK utilities like UTL_FILE_DIR.  
   - Usage: `/bin/sh dbtxkconfig.sh <SECRET_APPS_OCID> <SECRET_SYSTEM_OCID>`

6. **fndnodeclean.sh** – Performs cleanup of FND_NODES in the Applications PDB.  
   - Usage: `/bin/sh fndnodeclean.sh <SECRET_APPS_OCID> <CDB_NAME>`


## EBS Switchover Plan

Assuming Primary region is **Phoenix (PHX)** and DR region is **Ashburn (IAD)**:

1. **Stop EBS at PHX**  
   - `/bin/sh shutdownapps.sh <SECRET_APPS_OCID>`  
   - `/bin/sh fsdr-rsync-ebs.sh disable <EBS_IP>`

2. **Switchover DB to IAD**  
   - *No script is required. This operation is automatically performed as part of the Full Stack DR workflow for Database Cloud Services.*

3. **Perform FND Node Cleanup**  
   - `/bin/sh fndnodeclean.sh <SECRET_APPS_OCID> <CDB_NAME>`

4. **Configure DB Tier Utilities**  
   - `/bin/sh dbtxkconfig.sh <SECRET_APPS_OCID> <SECRET_SYSTEM_OCID>`

5. **Reconfigure App Tier at IAD**  
   - `/bin/sh autoconfigapps.sh <SECRET_APPS_OCID>`

6. **Start EBS at IAD**  
   - `/bin/sh startapps.sh <SECRET_APPS_OCID> <SECRET_WEBLOGIC_OCID>`  
   - `/bin/sh fsdr-rsync-ebs.sh enable <EBS_IP>`


## EBS Failover Plan

Assuming Primary region is **Phoenix (PHX)** and DR region is **Ashburn (IAD)**, follow these steps:

1. **Failover DB to IAD**  
   - *No script is required. This operation is automatically performed as part of the Full Stack DR workflow for Database Cloud Services as it is added part of the plan.*

2. **Perform FND Node Cleanup**  
   - `/bin/sh fndnodeclean.sh <SECRET_APPS_OCID> <CDB_NAME>`

3. **Configure DB Tier Utilities**  
   - `/bin/sh dbtxkconfig.sh <SECRET_APPS_OCID> <SECRET_SYSTEM_OCID>`

4. **Reconfigure App Tier at IAD**  
   - `/bin/sh autoconfigapps.sh <SECRET_APPS_OCID>`

5. **Start EBS at IAD**  
   - `/bin/sh startapps.sh <SECRET_APPS_OCID> <SECRET_WEBLOGIC_OCID>`

## General Notes

- All scripts utilize OCI CLI for secure secret retrieval and decoding.
- Logs are stored in `/home/oracle/fsdr/logs`.
- Ensure environment variables like `EBSapps.env`, `CONTEXT_FILE`, and `ORACLE_HOME` are properly set before execution.
- Scripts enforce strict error handling using `set -euo pipefail` — supported due to `/bin/sh` symlinking to Bash in Oracle Linux.


## Documentation

- [Oracle Full Stack Disaster Recovery Overview](https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/overview-disaster-recovery.html)


## Need Help?

Open a GitHub [Issue](https://github.com/oracle-samples/full-stack-disaster-recovery/issues) or contact your Full Stack DR administrator.

---

## Author

Chandra Dharanikota

---

## License

Released under the [Universal Permissive License v1.0](https://oss.oracle.com/licenses/upl/).
