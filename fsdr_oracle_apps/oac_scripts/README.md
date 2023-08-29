## Oracle Analytics Cloud scripts for OCI Full Stack Disaster Recovery:

Full Stack Disaster Recovery is an Oracle Cloud Infrastructure (OCI) disaster recovery orchestration and management service that provides comprehensive disaster recovery capabilities for all layers of an application stack, including infrastructure, middleware, database, and application.

Full Stack DR can be used to orchestrate DR operations like Switchover and Failover for both oracle and non-oracle applications.

## Prerequisites

1. Deploy Oracle Anlaytics Cloud in OCI with Production and Disaster Recovery setup:

Refer the Technical papers - Disaster Recovery Configuration for Oracle Analytics Cloud https://docs.oracle.com/en/cloud/paas/analytics-cloud/actch/OAC_Disaster_Recovery.pdf

Disaster Recovery Plan for Oracle Analytics Cloud using Manual Switchover Method
https://blogs.oracle.com/analytics/post/implement-a-disaster-recovery-for-oracle-analytics-cloud-using-manual-switch-over

Watch these videos for more details:
 
Deploy Oracle Analytics Cloud Service for Disaster Recovery (video 1)- https://www.youtube.com/watch?v=HPQFyfS26Yg
 
Automate recovery for Oracle Analytics Cloud Service(video 2)- https://www.youtube.com/watch?v=hY_LoGR5edU

Scripts used to automate recovery for Oracle Analytics Cloud Service (video 3) - https://www.youtube.com/watch?v=r8gQDDMxOvA

2. Prepare Source OCI region and Standby OCI region. Administrator privileges or Configure the required Oracle Identity and Access Management (IAM) policies for Full Stack Disaster Recovery as outlined here: Configuring Identity and Access Management (IAM) policies to use Full Stack DR and Policies for Full Stack Disaster Recovery -https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/disaster-recovery-policies.html and Configuring Identity and Access Management (IAM) policies to use Full Stack DR https://blogs.oracle.com/maa/post/iam-policies-fullstackdr

## Oracle Analytics Cloud Scripts

Oracle Analytics Cloud scripts for Full Stack DR switchover and failover.

1. oac-start-stop.sh - Resume or Pause Oracle Analytics Cloud instances in the selected Region.
2. oac-create-snapshot.sh - Exports Oracle Analytics Cloud snapshot backup in the desired Region.
3. oac-register-snapshot.sh - imports Oracle Analytics Cloud snapshot backup in the desired Region.
4. oac-chg-cronjob.sh - Disables and enables cron jobs for Oracle Analytics Cloud snapshot process after Switchover / Failover
5. getSourceRefreshToken.sh - Refresh token generated for oac-create-snapshot.sh consumption, No need to call explicitly.
6. getTargetRefreshToken.sh- Refresh token generated for oac-register-snapshot.sh consumption, No need to call explicitly.

These scripts are provided for generic guidance. You can either use your own scripts or customize the scripts according to your corporate policy and security requirements.

**Oracle Analytics Cloud Switchover plan**

Let us assume your primary region is Ashburn and DR region is Phoenix.The following user-defined groups will be be created and necessary Oracle Analytics Cloud scripts will be used as part of Oracle Analytics Cloud switchover plan in the specific order.

1. Stop Oracle Analytics Cloud at Ashburn Region
    - oac-start-stop.sh IAD
2. Start Oracle Analytics Cloud at Phoenix Region
    - oac-start-stop.sh PHX
3. Recover the OAC Snapshot at Phoenix Region
    - oac-register-snapshot.sh PHX
4. Change the Cron job from Ashburn to Phoenix Region
    - oac-chg-cronjob.sh IAD to PHX


**Oracle Analytics Cloud Failover plan**

Let us assume your primary region is Ashburn and DR region is Phoenix.The following user-defined groups will be be created and necessary Oracle Analytics Cloud scripts will be used as part of Oracle Analytics Cloud failover plan in the specific order.

1. Start Oracle Analytics Cloud at Phoenix Region
    - oac-start-stop.sh PHX
2. Recover the OAC Snapshot at Phoenix Region
    - oac-register-snapshot.sh PHX
3. Change the Cron job from Ashburn to Phoenix Region
    - oac-chg-cronjob.sh IAD to PHX

## Documentation

You can find the online documentation for Oracle Full Stack Disaster Recovery Cloud Service at [docs.oracle.com](https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/overview-disaster-recovery.html).

## Need Help?

Create GitHub [Issue](https://github.com/oracle-samples/full-stack-disaster-recovery/issues)

## Security

Please consult the [security guide](./SECURITY.md) for our responsible security vulnerability disclosure process.

## Contributions

Community contributions are not currently being accepted.

## License

Copyright (c) 2023 Oracle and/or its affiliates.

Released under the Universal Permissive License v1.0 as shown at
<https://oss.oracle.com/licenses/upl/>.
