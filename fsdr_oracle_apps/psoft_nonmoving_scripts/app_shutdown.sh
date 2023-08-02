#!/bin/bash
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
psadmin -c shutdown! -d APPDOM01
cd /u01/app/psoft/fscm92-dbaas-vinay-app/ps_cfg_home/appserv/APPDOM01/
rm -rf CACHE
psadmin -c cleanipc -d APPDOM01