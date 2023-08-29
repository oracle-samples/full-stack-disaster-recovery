## Oracle PeopleSoft (Non-moving) for OCI Full Stack Disaster Recovery:

Full Stack Disaster Recovery is an Oracle Cloud Infrastructure (OCI) disaster recovery orchestration and management service that provides comprehensive disaster recovery capabilities for all layers of an application stack, including infrastructure, middleware, database, and application.

Full Stack DR can be used to orchestrate DR operations like Switchover and Failover for both oracle and non-oracle applications.

## Prerequisites

1. Deploy PeopleSoft application in OCI with Production and Disaster Recovery setup:

Refer My oracle support note PeopleSoft : Implementing Disaster Recovery with Oracle Data Guard (Doc ID 1379808.1)
Refer the Technical paper - Disaster Recovery Configuration for PeopleSoft in Oracle Cloud https://www.oracle.com/technetwork/database/features/availability/maa-peoplesoft-bestpractices-134154.pdf

Watch these videos for more details:
 
Deploy single instance Oracle PeopleSoft Application for DR (video 1) - https://www.youtube.com/watch?v=TCLlRwmGwlw
 
Automate recovery for single instance Oracle PeopleSoft (video 2) - https://www.youtube.com/watch?v=QDFCgYTOC5g

Scripts used to automate recovery for single instance Oracle PeopleSoft (video 3) -  https://www.youtube.com/watch?v=1ASsKYyGQKo

2. Prepare Source OCI region and Standby OCI region. Administrator privileges or Configure the required Oracle Identity and Access Management (IAM) policies for Full Stack Disaster Recovery as outlined here: Configuring Identity and Access Management (IAM) policies to use Full Stack DR and Policies for Full Stack Disaster Recovery -https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/disaster-recovery-policies.html and Configuring Identity and Access Management (IAM) policies to use Full Stack DR https://blogs.oracle.com/maa/post/iam-policies-fullstackdr

## Oracle Peoplesoft Scripts

Oracle Peoplesoft scripts for Full Stack DR switchover and failover.

01. app_shutdown.sh - To shutdown PeopleSoft Application Server domain  
02. app_boot.sh - To startup PeopleSoft Application Server domain  
03. prcs_shutdown.sh - To shutdown PeopleSoft Process Scheduler domain in Linux  
04. prcs_start.sh - To startup PeopleSoft Process Scheduler domain in Linux  
05. psnt_shutdown_domain.bat - To shutdown PeopleSoft Process Scheduler domain in Windows  
06. psnt_start_domain.bat - To startup PeopleSoft Process Scheduler domain in Windows  
07. web_shutdown.sh - To shudtown PeopleSoft Web Server domain  
08. web_boot.sh - To startup PeopleSoft Web Server domain  
09. fsdr-rsync-psft.sh - To disable and enable rsync cronb jobs for PeopleSoft application and customisations files and folders  
10. elk_kill.sh - To stop Elastic Search services  
11. elk_start.sh - To start Elastic Search services  
12. kibana_kill.sh - To stop Kibana services  
13. kibana_start.sh - To start Kibana services  

These scripts are provided for generic guidance. You can either use your own scripts or customize the scripts according to your corporate policy and security requirements.

**Oracle PeopleSoft Switchover plan**

Let us assume your primary region is Ashburn and DR region is Phoenix.The following user-defined plan groups(with steps) will be be created and Oracle PeopleSoft scripts will be used as part of Oracle Peoplesoft switchover plan in the specific order. Built-in plan groups for DB switchover is added here for showing the complete plan.

1. Stop PeopleSoft Application at Ashburn Region
    - app_shutdown.sh
    - prcs_shutdown.sh
    - psnt_shutdown_domain.bat
    - web_shutdown.sh
    - elk_kill.sh
    - kibana_kill.sh
2. Disable Rsync Crobjobs at Ashburn Region
    - fsdr-rsync-psft.sh  disable x.x.x.x  (private ip of IAD app server)
    - fsdr-rsync-psft.sh  disable x.x.x.x  (private ip of IAD process scheduler [linux])
    - fsdr-rsync-psft.sh  disable x.x.x.x  (private ip of IAD webserver)
3. DB Switchover from Ashburn to Phoenix (In-Built Plan)
4. Start PeopleSoft Application at Phoenix Region
    - app_boot.sh
    - prcs_start.sh
    - psnt_start_domain.bat
    - web_boot.sh
5. Start Elastic Search at Pheonix Region
    - elk_start.sh
6. Start Kibana at Phoenix region
    - kibana_start.sh
7. Enable Rsync Crobjobs at Pheonix Region
    - fsdr-rsync-psft.sh  enable x.x.x.x  (private ip of PHX app server)
    - fsdr-rsync-psft.sh  enable x.x.x.x  (private ip of PHX process scheduler [linux])
    - fsdr-rsync-psft.sh  enable x.x.x.x  (private ip of PHX webserver)


**Oracle PeopleSoft Failover plan**

Let us assume your primary region is Ashburn and DR region is Phoenix.The following user-defined plan groups(with steps) will be be created and Oracle PeopleSoft scripts will be used as part of Oracle Peoplesoft failover plan in the specific order. Built-in plan groups for DB failover is added here for showing the complete plan.

1. DB Failover from Ashburn to Phoenix (In-Built Plan)
2. Start PeopleSoft Application at Phoenix Region
    - app_boot.sh
    - prcs_start.sh
    - psnt_start_domain.bat
    - web_boot.sh
3. Start Elastic Search at Pheonix Region
    - elk_start.sh
4. Start Kibana at Phoenix region
    - kibana_start.sh


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
