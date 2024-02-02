Oracle Integration Cloud (OIC) scripts for OCI Full Stack Disaster Recovery:

OCI Full Stack Disaster Recovery (Full Stack DR) provides fully automated and comprehensive disaster recovery orchestration solution for all the layers of a full-stack cloud application, including infrastructure, database, and the application middle tier. Using Full Stack DR, you can recover your full stack applications across OCI regions or availability domains within the same region.


Prerequisites:

1. Oracle Integration Cloud (OIC) is a managed OCI Platform as a Service offering (PaaS) which is not something Full Stack DR can manage natively since OIC itself does not expose compute, storage or database to OCI users.But, Full Stack DR can automate recovery for PaaS offerings as long as the engineering team for a given service such as OIC has documented a way to provision, configure and recover their service for disaster recovery between OCI regions. Please follow the OIC documentation[Configuring a Disaster Recovery Solution for Oracle Integration Generation 2](https://docs.oracle.com/en/cloud/paas/integration-cloud/disaster-recovery/disaster-recovery-integrations.html#GUID-A5319115-2B0F-40EC-87C0-30A527B58A09) to manually provision, configure and recover OIC. This is applicable for OIC Gen2.

2. Prepare Source OCI region and Standby OCI region. Administrator privileges or Configure the required Oracle Identity and Access Management (IAM) policies for Full Stack Disaster Recovery as outlined here: Configuring Identity and Access Management (IAM) policies to use Full Stack DR and Policies for Full Stack Disaster Recovery -https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/disaster-recovery-policies.html and Configuring Identity and Access Management (IAM) policies to use Full Stack DR https://blogs.oracle.com/maa/post/iam-policies-fullstackdr

Oracle Integration Cloud Scripts:

Oracle Integration Cloud scripts for Full Stack DR switchover and failover.

    oic-start-stop.sh - Start or stop Oracle Integration Cloud instances in the selected Region.
    dns_record_update.sh - Update the DNS records with the running Oracle Integration Cloud instances in the selected Region.

These scripts are provided for generic guidance. You can either use your own scripts or customize the scripts according to your corporate policy and security requirements. You need to install OCI CLI and configure your credentials to use the scripts.

1. Oracle Integration Cloud Switchover plan

Let us assume your primary region is Ashburn and DR region is Phoenix.The following user-defined groups will be be created and necessary Oracle Integration Cloud scripts will be used as part of Oracle Integration Cloud switchover plan in the specific order.

    Stop Oracle Integration Cloud at Ashburn Region
         oic-start-stop.sh stop IAD
    Start Oracle Integration Cloud at Phoenix Region
         oic-start-stop.sh start PHX
    Update DNS record at Phoenix Region
        dns_record_update.sh PHX

2. Oracle Integration Cloud Failover plan

Let us assume your primary region is Ashburn and DR region is Phoenix.The following user-defined groups will be be created and necessary Oracle Integration Cloud scripts will be used as part of Oracle Oracle Integration Cloud failover plan in the specific order.

    Start Oracle Integration Cloud at Phoenix Region
         oic-start-stop.sh start PHX
    Update DNS record at Phoenix Region
        dns_record_update.sh PHX

Documentation

You can find the online documentation for Oracle Full Stack Disaster Recovery Cloud Service at docs.oracle.com.
