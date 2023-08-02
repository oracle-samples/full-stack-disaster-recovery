#!/bin/bash
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
cd /u01/app/psoft/fscm92-dbaas-vinay-prcs/ps_cfg_home/appserv/prcs/PRCSDOM01
rm -rf CACHE
psadmin -p cleanipc -d PRCSDOM01
psadmin -p start -d PRCSDOM01