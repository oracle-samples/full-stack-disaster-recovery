#!/bin/bash
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
psadmin -w shutdown! -d WEBSERVER01
cd /u01/app/psoft/fscm92-dbaas-vinay-web/ps_cfg_home/webserv/WEBSERVER01/applications/peoplesoft/PORTAL.war/
rm -rf cache
