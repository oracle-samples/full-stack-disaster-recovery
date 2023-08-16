#!/bin/bash
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
export JAVA_HOME=/u01/app/es_home/es/pt/es_jdk11.0.17
# This is a wrapper script -- wrapper.sh
echo "Invoking command in nohup.."
nohup /u01/app/es_home/es/pt/Kibana7.10.0/bin/kibana > /tmp/kibana.out 2>&1 &
echo `sleep 30`
exit 0
