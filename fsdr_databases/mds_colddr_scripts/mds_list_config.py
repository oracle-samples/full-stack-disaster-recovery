#!/usr/bin/python
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# Example script written by Antoun Moubarak, Cloud Architecture Specialist

import os
import sys
import csv
from tabulate import tabulate

current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Define the file name 
config_file_name = current_directory + "/config.csv"
 
config_file_open = open(config_file_name)
config_file_read = csv.reader(config_file_open)
print(tabulate(config_file_read, headers='firstrow', tablefmt="psql", maxcolwidths=[None,50,50,50,50,50,50,50]))
