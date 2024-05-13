# Oracle Integration scripts for OCI Full Stack Disaster Recovery:

OCI Full Stack Disaster Recovery (Full Stack DR) provides fully automated and comprehensive disaster recovery orchestration solution for all the layers of a full-stack cloud application, including infrastructure, database, and the application middle tier. Using Full Stack DR, you can recover your full stack applications across OCI regions or availability domains within the same region.

## Prerequisites:

1. Oracle Integration is a managed OCI Platform as a Service offering (PaaS) which is not something Full Stack DR can manage natively since Oracle Integration itself does not expose compute, storage or database to OCI users.But, Full Stack DR can automate recovery for PaaS offerings as long as the engineering team for a given service such as Oracle Integration has documented a way to provision, configure and recover their service for disaster recovery between OCI regions. Please follow the Oracle Integration documentation[Configuring a Disaster Recovery Solution for Oracle Integration Generation 2](https://docs.oracle.com/en/cloud/paas/integration-cloud/disaster-recovery/disaster-recovery-integrations.html#GUID-A5319115-2B0F-40EC-87C0-30A527B58A09) to manually provision, configure and recover Oracle Integration. This is applicable for Oracle Integration Gen2.

2. Prepare Source OCI region and Standby OCI region. Administrator privileges or Configure the required Oracle Identity and Access Management (IAM) policies for Full Stack Disaster Recovery as outlined here: Configuring Identity and Access Management (IAM) policies to use Full Stack DR and Policies for Full Stack Disaster Recovery -https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/disaster-recovery-policies.html and Configuring Identity and Access Management (IAM) policies to use Full Stack DR https://blogs.oracle.com/maa/post/iam-policies-fullstackdr

## Oracle Integration Scripts:

Oracle Integration scripts for Full Stack DR switchover and failover.

oic-integration-switch.sh - To activate or deactivate integrations in Oracle Integration instances in both Regions  
oic-update-parameters.sh - To update the scheduled parameters of Oracle Integration integrations for Oracle Integration instances.  
oic-integration-schedule.sh - To start or stop OIC scheduled integrations of Oracle Integration integrations for Oracle Integration instances.  
oic-sync-schedule-parameters.sh - To sync scheduled parameters for scheduled integrations, from one Oracle Integration instance to another.  
dns_record_update.sh - Update the DNS records with the running Oracle Integration instances in the selected Region.  

These scripts are provided for generic guidance. You can either use your own scripts or customize the scripts according to your corporate policy and security requirements. You need to install OCI CLI and configure your credentials to use the scripts.

Also, to make sure that your primary instance is updated with latest scheduled parameters, ensure that the json files integrations.json is updated with the all the integration names along with the version details, along with the integration_parameters.json file, which needs to be kept updated with the latest sceduled parameter values for all the scheduled integrations. You can employ CICD to achieve this.

1. Oracle Integration Switchover plan

Let us assume your primary region is Ashburn and DR region is Phoenix.The following user-defined groups will be be created and necessary Oracle Integration scripts will be used as part of Oracle Integration switchover plan in the specific order.

    Sync scheduled parameters from IAD to PHX
         oic-sync-schedule-parameters.sh PHX
    Activate relevant integrations at PHX
         oic-integration-switch.sh activate PHX
    Start scheduled integrations at PHX
         oic-integration-schedule.sh start PHX
    Update DNS record at PHX
        dns_record_update.sh PHX
    Deactivate scheduled integrations at IAD
        oic-integration-switch.sh deactivate IAD

Note: If you have a moving instance added part of DR protection group, then plan groups related to compute and volume groups will be generated as built-in plan groups.

2. Oracle Integration Failover plan

Let us assume your primary region is Ashburn and DR region is Phoenix.The following user-defined groups will be be created and necessary Oracle Integration scripts will be used as part of Oracle Oracle Integration failover plan in the specific order.

    Activate relevant integrations at PHX  
        oic-integration-switch.sh activate PHX  
    Update Schedule Parameters at PHX  
        oic-update-parameters.sh PHX  
    Start scheduled integrations at PHX  
        oic-integration-schedule.sh start PHX  
    Update DNS record at PHX  
        dns_record_update.sh PHX  

Note: If you have a moving instance added part of DR protection group, then plan groups related to compute and volume groups will be generated as built-in plan groups.

## Documentation

You can find the online documentation for Oracle Full Stack Disaster Recovery at [docs.oracle.com](https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/overview-disaster-recovery.html).
