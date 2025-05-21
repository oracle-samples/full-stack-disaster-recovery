## Oracle E-Business Suite scripts for OCI Full Stack Disaster Recovery:

Full Stack Disaster Recovery is an Oracle Cloud Infrastructure (OCI) disaster recovery orchestration and management service that provides comprehensive disaster recovery capabilities for all layers of an application stack, including infrastructure, middleware, database, and application.

Full Stack DR can be used to orchestrate DR operations like Switchover and Failover for both oracle and non-oracle applications.

## Prerequisites

1. Deploy Oracle E-Business Suite in OCI with Production and Disaster Recovery setup:

Refer My oracle support note Oracle Business Continuity for Oracle E-Business Suite Release 12.2 on Oracle Database 19c Using Logical Host Names (Doc ID 2617788.1)

Watch these videos for more details:

How to Deploy E-Business Suite for DR Before Using Full Stack DR (video 1)- https://www.youtube.com/watch?v=Ipw4w7FwhBw

How to add E-Business Suite to Full Stack DR (video 2)-https://www.youtube.com/watch?v=wUVCIzOAf7Q

2. Prepare Source OCI region and Standby OCI region. Administrator privileges or Configure the required Oracle Identity and Access Management (IAM) policies for Full Stack Disaster Recovery as outlined here: Configuring Identity and Access Management (IAM) policies to use Full Stack DR and Policies for Full Stack Disaster Recovery -https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/disaster-recovery-policies.html and Configuring Identity and Access Management (IAM) policies to use Full Stack DR https://blogs.oracle.com/maa/post/iam-policies-fullstackdr

## EBS Scripts

EBS scripts for Full Stack DR switchover and failover.

1. shutdownapps.sh - Stop EBS services using adstpall.sh
2. fsdr-rsync-ebs.sh - Cron job to disable and enable rsync for the EBS file systems
3. autoconfigapps.sh- Reconfigure application configuration files using adautocfg.sh
4. startapps.sh- Start EBS services using adstrtal.sh
5. dbswitchover.sh - Custom script to perform DB switchover using dgmgrl
6. dbfailover.sh- Custom script to perform DB failover using dgmgrl

These scripts are provided for generic guidance. You can either use your own scripts or customize the scripts according to your requirements.

**EBS Switchover plan**

Let us assume your primary region is Ashburn and DR region is phoenix.The following user-defined groups will be be created and necessary EBS scripts will be used as part of EBS switchover plan in the specific order.

1. Stop EBS at IAD
    - shutdownapps.sh
    - fsdr-rsync-ebs.sh disable
2. Switchover Data Guard to PHX
    - dbswitchover.sh
3. Run autoconfig on app tier at PHX
    - autoconfigapps.sh
4. Start EBS at PHX
    - startapps.sh
    - fsdr-rsync-ebs.sh enable

**EBS Failover plan**

Let us assume your primary region is Ashburn and DR region is phoenix.The following user-defined groups will be be created and necessary EBS scripts will be used as part of EBS failover plan in the specific order.

1. Failover Data Guard to PHX
    - dbfailover.sh
3. Run autoconfig on app tier at PHX
    - autoconfigapps.sh
4. Start EBS at PHX
    - startapps.sh

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
