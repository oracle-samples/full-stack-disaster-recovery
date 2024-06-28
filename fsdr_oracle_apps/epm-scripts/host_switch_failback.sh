#!/bin/bash
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
hosts_file="/etc/hosts"
primary_hosts_file="/path/to/primary_hosts.txt"

# Overwrite hosts file with primary version
sudo cp $primary_hosts_file $hosts_file

echo "Failback to primary complete."
