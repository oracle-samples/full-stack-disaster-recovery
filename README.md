# Full Stack Disaster Recovery Cloud Service Samples

Full Stack Disaster Recovery (FSDR) is an Oracle Cloud Infrastructure (OCI) disaster recovery orchestration and management service that provides comprehensive disaster recovery capabilities for all layers of an application stack, including infrastructure, middleware, database, and application.

This repository contains code samples related to Full Stack Disaster Recovery Cloud Service from Oracle.

## Installation and Usage

Download the scripts and copy them to the OCI Compute instance where you want to execute these scripts.

Run the script using the command syntax: python <script_name> <script_arguments>
  
Here is a sample command:
  
<i> /usr/bin/python3 /home/opc/fsdr/fullstackdr_script_executor.py local --mode execute --script_interpreter '/bin/sh' --script_path '/home/opc/fsdr/my_custom_script.sh' --script_arguments  'FSDR1 FSDR2' </i>

In the above sample command, we are assuming that the scripts are available in the folder named /home/opc/fsdr on the compute instance.  The <i> my_custom_script.sh </i> is the user defined script that the user wants to execute.  

## Documentation

You can find the online documentation for Oracle Full Stack Disaster Recovery Cloud Service at [docs.oracle.com](https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/overview-disaster-recovery.html).

## Need Help?

Create GitHub [Issue](https://github.com/oracle-samples/full-stack-disaster-recovery/issues)

## Security

Please consult the [security guide](./SECURITY.md) for our responsible security vulnerability disclosure process.

## Contributing

This project is not accepting external contributions at this time. For bugs or enhancement requests, please file a GitHub issue unless it’s security related. When filing a bug remember that the better written the bug is, the more likely it is to be fixed. If you think you’ve found a security vulnerability, do not raise a GitHub issue and follow the instructions in our [security policy](./SECURITY.md).

## License

Copyright (c) 2023 Oracle and/or its affiliates.

Released under the Universal Permissive License v1.0 as shown at
<https://oss.oracle.com/licenses/upl/>.
