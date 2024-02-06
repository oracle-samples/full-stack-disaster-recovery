# Full Stack Disaster Recovery Bash Examples

Full Stack Disaster Recovery is an Oracle Cloud Infrastructure (OCI) disaster recovery orchestration and management service that provides comprehensive disaster recovery capabilities for all layers of an application stack, including infrastructure, middleware, database, and application.

This repository contains bash code examples related to Full Stack DR from Oracle.  The examples are production ready but can be modified to fit unique requirements of individual deployments of Full Stack DR in your own tenancy.

## Installation

Download the scripts and copy them to the OCI Compute instance where you want to execute these scripts.  There are two differt file types with different extensions: the scripts all have *.sh extensions and function modules that the scripts rely on have *.func extensions.

The scripts are not standalone, monolithic code and rely on two files that act as function libraries/modules. The two function modules both have a "func" extension in the filenames. These two files are critical and must reside in the same directory as the scripts.

The scripts can be owned root:root or any other user:group, but ensure all files have permissions of 755.  The scripts should be executable by any user that has OCI CLI configured and valid API keys installed in their home directory. Please ensure the user account that will be executing these scripts has everything set up as explained in [the CLI Quickstart guide](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm).

Also, ensure you have the latest version of OCI CLI installed. The CLI and SDKs change every time a new API for any OCI service is added, removed or updated.  That means the python modules for OCI CLI are always changing.  Using a version of CLI from six months ago will likely make any CLI script written for popular OCI services fail, so make sure you take the time to upgrade the CLI before running these scripts.

## Usage
The scripts will display a usage/help message if they are executed with no arguments.

**fsdr-bkup-plans.sh**: 
* This can be added to crontab to periodically create backups of a specific DRPG and all DR plans associated with the DRPG. It can also be executed on the command line any time changes are made to DR plans or BEFORE a member resource is added to a DRPG since adding members deletes all DR plans in both regions.
* This script is designed to be executed on the command line, not as a user-defined step in a DR plan.
* The script only requires a single argument. The single argument is the OCID of the DR protection group (DRPG) that you want to back up.
* This script must be executed separately for the DRPG in each region. For example, if the DRPG peers are in Amsterdam and Frankfurt, the script needs executed with the DRPG OCID for Amsterdam and then executed with the DRPG OCID for Frankfurt.
* This will create an individual file containing the object data record in JSON format for the DRPG and each DR plan.
* The backups are stored in a date/time stamped directory in /tmp on the local host where the script is being executed.  The script creates a log file and directory with a similar name like this:
  * /tmp/fsdr-bkup-plans.sh_29012024-100507.log
  * /tmp/fsdr-bkup-plans.sh_29012024-100507-my-drpg-name.bkup

**fsdr-upd-dns.sh**: 
* This will automatically update IP addresses for compute and load balancers in OCI DNS as part of a DR switchover or failover.  It updates the IPs for any compute and load balancers that it finds in a specified DR protection group.
* This script can be added to a user-defined plan step in a DR plan and executed as any user that is able to execute OCI CLI on the local host where the script is installed and being called.
* This script can also be executed from the command line on any host by any user that is able to execute OCI CLI on the local host where the script is installed.
* When executed as a plan step, all output is logged to the DRPG object storage bucket and in /tmp on the local host where the script is installed. When executed on the command line outside of Full Stack DR all output is just logged to /tmp on the local host where the script is installed. The log file on local host will look something like this in either case:
  * /tmp/fsdr-upd-dns.sh_20240129-195750.log


## Documentation

You can find the online documentation for Oracle Full Stack Disaster Recovery at [docs.oracle.com](https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/overview-disaster-recovery.html).

## Need Help?

Create GitHub [Issue](https://github.com/oracle-samples/full-stack-disaster-recovery/issues)

## Security

Please consult the [security guide](./SECURITY.md) for our responsible security vulnerability disclosure process.

## Contributions

Community contributions are not currently being accepted.

## License

Copyright (c) 2024 Oracle and/or its affiliates.

Released under the Universal Permissive License v1.0 as shown at
<https://oss.oracle.com/licenses/upl/>.
