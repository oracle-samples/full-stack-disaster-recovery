## Oracle Hyperion EPM System scripts for OCI Full Stack Disaster Recovery:

OCI Full Stack Disaster Recovery (Full Stack DR) provides fully automated and comprehensive disaster recovery orchestration solution for all the layers of a full-stack cloud application, including infrastructure, database, and the application middle tier. Using Full Stack DR, you can recover your full stack applications across OCI regions or availability domains within the same region.

## Prerequisites:

1. The disaster recovery (DR) strategy employs a comprehensive replication of both boot and block volumes from the production environment to the standby site, greatly simplifying the configuration of the standby location. This method aligns with the DR guidelines outlined in the EPM System Deployment Options Guide available at https://docs.oracle.com/en/applications/enterprise-performance-management/11.2/hitdo/general_information_about_disaster_recovery.html, which adheres to the recommendations for disaster recovery provided for Fusion Middleware. You must install the EPM system with all the required components.

2. Prepare Source OCI region and Standby OCI region. Administrator privileges or Configure the required Oracle Identity and Access Management (IAM) policies for Full Stack Disaster Recovery as outlined here: Configuring Identity and Access Management (IAM) policies to use Full Stack DR and Policies for Full Stack Disaster Recovery -https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/disaster-recovery-policies.html and Configuring Identity and Access Management (IAM) policies to use Full Stack DR https://blogs.oracle.com/maa/post/iam-policies-fullstackdr

## Oracle Hyperion EPM System Full Stack Disaster Recovery scripts:

Scripts used for Full Stack DR switchover and failover.

1.start_services.ps1/sh - script to start all EPM System services, including WLS and OHS, on Windows (PowerShell) or Linux (Bash) compute  
2.stop_services.ps1/sh - script to start all EPM System services, including WLS and OHS, on Windows (PowerShell) or Linux (Bash) compute  
3.host_switch_failover.ps1/sh - script to update host file after switch to the standby region. Windows (PowerShell) or Linux (Bash)  
4.host_switch_failback.ps1/sh - script to update host file after switch from standby region back to the primary region. Windows (PowerShell) or Linux (Bash)  

These scripts are provided for generic guidance. You can either use your own scripts or customize the scripts according to your corporate policy and security requirements.

**1. Switchover plan**

Let us assume your primary region is London and DR region is Newport.The following user-defined groups will be be created and necessary Oracle Hyperion EPM System will be used as part of Oracle Hyperion EPM System switchover plan in the specific order.

Custom scripts before shutdown  
  - Script to Stop EPM Services  
      stop_services.ps1/sh  

Custom scripts after Startup  
  - Script to Update Host File  
      host_switch_failover.ps1/sh  
  - Script to Start EPM Services  
      start_services.ps1/sh  

Note: Plan groups related to moving compute, volume groups and load balancer will be generated as built-in plan groups.

**2. Failover plan**

Let us assume your primary region is Newport and DR region is London.The following user-defined groups will be be created and necessary Oracle Hyperion EPM System will be used as part of Oracle Hyperion EPM System failover plan in the specific order.

Custom scripts after Startup  
  - Script to Update Host File  
      host_switch_failback.ps1/sh  
  - Script to Start EPM Services  
      start_services.ps1/sh  

Note: Plan groups related to moving compute, volume groups and load balancer will be generated as built-in plan groups.

## Documentation:

You can find the online documentation for Oracle Full Stack Disaster Recovery Cloud Service at docs.oracle.com.

## License

Copyright (c) 2024 Oracle and/or its affiliates.

Released under the Universal Permissive License v1.0 as shown at
<https://oss.oracle.com/licenses/upl/>.

