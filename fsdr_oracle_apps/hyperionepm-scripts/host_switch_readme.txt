During a failover to a standby region, applications might rely on hostnames to access critical resources. These hostnames often resolve to IP addresses within the primary region.  By switching the hosts file to a version containing the corresponding IP addresses for the standby region, applications can continue to function seamlessly without needing code modifications. This ensures minimal disruption and a smoother transition during a failover event. The host_switch scripts allow you to automate this process and can be used in Full Stack Disaster Recovery plans.

Instructions

Prerequisites

PowerShell execution policy must allow script execution (set to at least RemoteSigned or similar if the script is not signed).
The script needs to be run with sufficient privileges to modify the hosts files.

Files:

host_switch_failover.ps1: The PowerShell script that performs the host file switching after failover to standby region.
host_switch_failback.ps1: The PowerShell script that restores the original host file after failback from the standby region to the primary region.
primary_hosts.txt: Contains the correct host mappings for the primary region.
standby_hosts.txt: Contains the correct host mappings for the standby region.

Overall Process

Preparation:

Create the primary_hosts.txt and standby_hosts.txt files with the appropriate IP address and hostname mappings for their corresponding regions.
Place all files (host_switch.ps1, primary_hosts.txt, standby_hosts.txt) in an accessible location on both the primary and standby systems.

Failover to Standby:

On the standby system, execute the script host_switch_failover.ps1/host_switch_failover.sh:

powershell.exe -File C:\scripts\host_switch_failover.ps1
or
/path/to/host_switch_failover.sh

This will replace the hosts file with the standby mappings.

Failback to Primary:

On the original primary system, execute the host_switch_failback.ps1/host_switch_failback.sh:

powershell.exe -File C:\scripts\host_switch_failback.ps1
or
/path/to/host_switch_failback.sh

This will restore the hosts file to the original primary mappings.

Important Notes

File Paths: Adjust file paths in the instructions and the script if your files are located in a different directory.

Backup: The script creates an archive backup of the hosts file with a date and time appended to the filename (e.g., hosts.bak_20240308_163012) before any modifications are made.

Permissions: Ensure the user or process executing the script has permissions to modify the hosts file in "C:\Windows\System32\drivers\etc". You may need to run the script with administrative privileges.

Automation: Consider integrating this script into your broader disaster recovery orchestration processes for automated execution, if applicable.

Additional Tips

Test Thoroughly: Test the script in a non-production environment to ensure it works as expected before using it in your production switchover process.

Script Protection: Store the script and host files in a secure location with appropriate access controls to prevent unauthorized modifications.
