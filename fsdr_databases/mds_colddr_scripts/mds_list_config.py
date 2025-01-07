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
import pandas

# Get the current script directory
current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Define the file name for the configuration file
config_file_name = current_directory + "/config.csv"

# Open the configuration file
with open(config_file_name, mode='r') as config_file_open:
    config_file_read = csv.reader(config_file_open)

    # Read the file into a pandas DataFrame for easy manipulation
    df = pandas.read_csv(config_file_name)

    # Check for duplicate MySQL DB Labels
    unique_label = not df["MYSQL_DB_LABEL"].is_unique
    # Check for duplicate MySQL DB OCIDs
    unique_ocid = not df["MYSQL_DB_OCID"].is_unique

    # Handle duplicates if found
    if unique_label:
        print("/!\\/!\\ Caution: Duplicate MySQL DB Label values found in the config.csv file /!\\/!\\")
    elif unique_ocid:
        print("/!\\/!\\ Caution: Duplicate MySQL DB OCID values found in the config.csv file /!\\/!\\")
    else:
        # If no duplicates, print the configuration file content in a tabular format
        print(tabulate(config_file_read, headers='firstrow', tablefmt="grid"))
