#!/usr/bin/python -x
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# Example script written by Antoun Moubarak, Cloud Architecture Specialist

from tabulate import tabulate
import config

# Finding system details from the config file
mds_data = config.mdsdata
mds_head = config.mdshead

# display table
print(tabulate(mds_data, headers=mds_head, tablefmt="grid"))


