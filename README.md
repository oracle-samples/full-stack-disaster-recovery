# Full Stack Disaster Recovery Cloud Service Samples

Full Stack Disaster Recovery (FSDR) is an Oracle Cloud Infrastructure (OCI) disaster recovery orchestration and management service that provides comprehensive disaster recovery capabilities for all layers of an application stack, including infrastructure, middleware, database, and application.

This repository contains code samples related to Full Stack Disaster Recovery Cloud Service from Oracle.

## Installation

Download the scripts and copy them to the OCI Compute instance where you want to execute these scripts.

Run the script using the command syntax: python <script_name> <arguments>
  
Here is a sample command:
  
/usr/bin/python3 /tmp/fsdr/fullstackdr_script_executor.py local --mode precheck --script_interpreter ‘/bin/sh’ --script_path ‘/tmp/fsdr/scriptexecutortest.sh’ --script_arguments ‘FSDR1 FSDR2’

## Documentation

You can find the online documentation for Oracle Full Stack Disaster Recovery Cloud Service at [docs.oracle.com](https://docs.oracle.com/en-us/iaas/disaster-recovery/doc/overview-disaster-recovery.html)

## Need Help?

Create GitHub [Issue](https://github.com/oracle-samples/full-stack-disaster-recovery/issues)

## Security

Please consult the [security guide](./SECURITY.md) for our responsible security vulnerability disclosure process

## License

Copyright (c) 2023 Oracle and/or its affiliates.

Released under the Universal Permissive License v1.0 as shown at
<https://oss.oracle.com/licenses/upl/>.
