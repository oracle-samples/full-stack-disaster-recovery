#!/usr/bin/env -S python3 -x
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# This module contains reusable Python functions that are shared across multiple scripts in the project.
# It serves as a centralized utility library to promote code reuse, reduce duplication, and maintain consistency.

# By isolating common logic here, we aim to improve maintainability and make the codebase easier to understand
# and extend—both for internal development and external contributors.
#
# Module written by Antoun Moubarak, Cloud Architecture Specialist

import oci
import sys
import logging
import time
import json

def prepare_regions_file(source_region,destination_region,current_directory,base_config_file_name,script_name):
    regions_file = current_directory + "/" + base_config_file_name + "_" + script_name + "." + time.strftime("%Y%m%d%H%M%S")
    with open(regions_file, "w") as regions:
        regions.write("[SOURCE]\n")
        regions.write("region = " + source_region + "\n")
        regions.write("[DESTINATION]\n")
        regions.write("region = " + destination_region + "\n")
    return regions_file

def print_cmd():
    command = sys.argv[0]
    arguments = sys.argv[1:]
    logging.info(f"Executing the following command {command} with arguments {arguments}")

def config_logging(current_directory,base_config_file_name):
    logfilename = current_directory + "/logs/cold_disaster_recovery_" + base_config_file_name + ".log"
    logging.basicConfig(
        handlers=[
            logging.FileHandler(logfilename,'a'),
            logging.StreamHandler()
        ],
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    return logfilename

def read_config_file(config_file_name):
    # Opening JSON file
    config_file = open(config_file_name)

    # returns JSON object as a dictionary
    data = json.load(config_file)

    # Closing file
    config_file.close()
    return data

def update_config_file(config_file_name,data):
    # Opening JSON file
    with open(config_file_name, 'w') as file:
        json.dump(data, file, indent=4)

    # Closing file
    file.close()
    return 1

def get_db_system_details(db_system_id,oci_db_system_client):
    try:
        # Initialize the DB System client and fetch DB system details
        oci_db_system_details = oci_db_system_client.get_db_system(db_system_id)
        return oci_db_system_details
    except Exception as err:
        logging.error(f"{err}")
        return None