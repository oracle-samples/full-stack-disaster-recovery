#!/usr/bin/python -x
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.
#
# Example script written by Antoun Moubarak, Cloud Architecture Specialist

import oci
import argparse
import json
import os
import sys
import time
import logging
import base64
import mysql.connector
import re

# Argument Parsing
# This section parses the command-line arguments for the script.
parser = argparse.ArgumentParser(description='Switchover a HeatWave MySQL Database System. It performs is a role reversal between the primary database and one of its replicas databases.')
parser.add_argument("-c", "--config-file", required=True, help="Specify the JSON configuration file.")
parser.add_argument("-to", "--to-replica", required=True, help="Specify the replica Unique Name.")
args = parser.parse_args()

# Extract parsed arguments
config_file_name = args.config_file
replica_db_name = args.to_replica

# Get the current directory of the script
current_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Configure logging
logfilename = current_directory + "/logs/disaster_recovery.log"
logging.basicConfig(
    handlers=[
        logging.FileHandler(logfilename,'a'),
        logging.StreamHandler()
    ],
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logging.info(args)

def print_cmd():
    command = sys.argv[0]
    arguments = sys.argv[1:]
    logging.info(f"Executing the following command {command} with arguments {arguments}")

def prepare_regions_file(primary_region,replica_region):
    regions_file = current_directory + "/" + os.path.basename(config_file_name).split('.')[0] + "_regions_switchover." + time.strftime("%Y%m%d%H%M%S")
    with open(regions_file, "w") as regions:
        regions.write("[PRIMARY]\n")
        regions.write("region = " + primary_region + "\n")
        regions.write("[REPLICA]\n")
        regions.write("region = " + replica_region + "\n")
    return regions_file

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

def find_replica_in_config(data, replica_db_name):
    # Iterating through the replicas list
    for index, item in enumerate(data["replication_details"]["replicas"]):
        if item["db_unique_name"] == replica_db_name:
            return index
    return -1

def get_db_system_details(db_system_id,oci_region_config,oci_signer):
    try:
        # Initialize the DB System client and fetch DB system details
        oci_db_system_client = oci.mysql.DbSystemClient(config=oci_region_config, signer=oci_signer)
        oci_db_system_details = oci_db_system_client.get_db_system(db_system_id)
        return oci_db_system_details
    except Exception as err:
        logging.error(f"{err}")
        return None

def get_secret_password(secret_id,oci_region_config,oci_signer):
    try:
        oci_secrets_client = oci.secrets.SecretsClient(config=oci_region_config, signer=oci_signer)
        oci_secret_bundle = oci_secrets_client.get_secret_bundle(secret_id)
        oci_secret_content = oci_secret_bundle.data.secret_bundle_content.content
        decoded_secret_content = base64.b64decode(oci_secret_content)
        return decoded_secret_content.decode('utf-8')
    except Exception as err:
        logging.error(f"{err}")
        return None

def set_db_system_database_mode(db_system_id,oci_region_config,oci_signer,database_mode):
    try:
        # Initialize the DB System client and set database_mode
        oci_db_system_client = oci.mysql.DbSystemClient(config=oci_region_config, signer=oci_signer)
        oci_db_system_update_details = oci.mysql.models.UpdateDbSystemDetails(database_mode=database_mode)
        oci_db_system_client.update_db_system(db_system_id=db_system_id,update_db_system_details=oci_db_system_update_details)
        
        # Wait for the DB system to reach the state
        oci_db_system_get_rsp = oci_db_system_client.get_db_system(db_system_id)
        oci.wait_until(oci_db_system_client, oci_db_system_get_rsp, 'database_mode', database_mode)
        return oci_db_system_get_rsp
    except Exception as err:
        logging.error(f"{err}")
        return None

def get_repilca_channel_id(oci_replica_channels_details,primary_db_endpoint):
    for item in oci_replica_channels_details:
        if item.source.hostname == primary_db_endpoint and item.lifecycle_state == "ACTIVE":
            return item.id
    return None

def delete_replica_channel(channel_id,oci_region_config,oci_signer):
    try:
        oci_db_system_channel_client = oci.mysql.ChannelsClient(config=oci_region_config, signer=oci_signer)
        oci_db_system_channel_client.delete_channel(channel_id)

        oci_db_system_channel_get_rsp = oci_db_system_channel_client.get_channel(channel_id)
        oci.wait_until(oci_db_system_channel_client, oci_db_system_channel_get_rsp, 'lifecycle_state', 'DELETED')
        return 1
    except Exception as err:
        logging.error(f"{err}")
        return None
    
def create_replica_channel(channel_source_config,channel_target_config,compartment_id,display_name,oci_region_config,oci_signer):
    try:
        oci_db_system_channel_client = oci.mysql.ChannelsClient(config=oci_region_config, signer=oci_signer)
        oci_source = oci.mysql.models.CreateChannelSourceFromMysqlDetails(**channel_source_config)
        oci_target = oci.mysql.models.CreateChannelTargetFromDbSystemDetails(**channel_target_config)
        oci_create_channel_details = oci.mysql.models.CreateChannelDetails(source=oci_source,target=oci_target,compartment_id=compartment_id,display_name=display_name)
        oci_db_system_channel_create = oci_db_system_channel_client.create_channel(oci_create_channel_details)
        oci_channel_id = oci_db_system_channel_create.data.id
        oci_db_system_channel_get_rsp = oci_db_system_channel_client.get_channel(oci_channel_id)
        oci.wait_until(oci_db_system_channel_client, oci_db_system_channel_get_rsp, 'lifecycle_state', 'ACTIVE')
        return oci_channel_id
    except Exception as err:
        logging.error(f"{err}")
        return None

def connect_mysql(config):
    """Connect to MySQL Server."""
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Error connecting to MySQL {config['host']}: {err}")
        return None

def connect_mysql(config):
    """Connect to MySQL Server."""
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Error connecting to MySQL {config['host']}: {err}")
        return None

def get_replication_status(conn, is_primary=True):
    """Retrieve replication status from MySQL server."""
    cursor = conn.cursor(dictionary=True)

    if is_primary:
        cursor.execute("SHOW BINARY LOG STATUS;")
        status = cursor.fetchone()
    else:
        #cursor.execute(f"SHOW REPLICA STATUS FOR CHANNEL '{REPLICATION_CHANNEL}';")
        cursor.execute(f"SHOW REPLICA STATUS;")
        status = cursor.fetchone()

    cursor.close()
    return status

def wait_for_executed_gtid(conn, gtid_executed):
    cursor = conn.cursor(dictionary=True)
    # Split the GTID set into individual sets
    gtid_sets = gtid_executed.split(',')

    for gtid_set in gtid_sets:
        gtid_set = gtid_set.strip()
        query = f"SELECT WAIT_FOR_EXECUTED_GTID_SET('{gtid_set}') AS WAIT_FOR_EXECUTED_GTID_SET"
        cursor.execute(query)
        row = cursor.fetchone()
        result = row['WAIT_FOR_EXECUTED_GTID_SET']
        if result != 0:
            return -1
    cursor.close()
    return None

def parse_gtid_set(gtid_set):
    """
    Parses a GTID set string into a dictionary mapping server UUIDs to sets of transaction IDs.
    """
    gtid_dict = {}
    if not gtid_set:
        return gtid_dict

    for uuid_set in gtid_set.split(","):
        match = re.match(r"([\w-]+):([\d-]+)", uuid_set)
        if match:
            server_uuid, txn_range = match.groups()
            transactions = set()
            for part in txn_range.split(","):
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    transactions.update(range(start, end + 1))
                else:
                    transactions.add(int(part))
            gtid_dict[server_uuid] = transactions
    return gtid_dict

def find_gtid_gaps(primary_gtid, replica_gtid):
    """
    Compare GTID sets and detect missing transactions.
    """
    primary_gtid_dict = parse_gtid_set(primary_gtid)
    replica_gtid_dict = parse_gtid_set(replica_gtid)

    missing_gtids = {}

    for uuid, source_transactions in primary_gtid_dict.items():
        replica_transactions = replica_gtid_dict.get(uuid, set())
        missing_transactions = source_transactions - replica_transactions

        if missing_transactions:
            missing_gtids[uuid] = sorted(missing_transactions)

    return missing_gtids

def get_gtid_executed(conn):
    """Fetch GTID_EXECUTED from a MySQL server."""
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW GLOBAL VARIABLES LIKE 'gtid_executed';")
        result = cursor.fetchone()
        cursor.close()

        if result:
            # Remove newlines and extra spaces
            return result[1].replace("\n", "").replace(" ", "")
        return None
    except mysql.connector.Error as err:
        logging.error(f"Error connecting to {conn['host']}: {err}")
        return None

def switchover_roles():
    # Read the configuration file
    data = read_config_file(config_file_name)

    # Find Replica details from the config file
    index = find_replica_in_config(data, replica_db_name)
    if index == -1:
        logging.error(f"Replica {replica_db_name} not found in {config_file_name} file.")
        sys.exit(1)

    # Init variables
    primary_region = data["replication_details"]["primary"]["region"]
    primary_db_name = data["replication_details"]["primary"]["db_unique_name"]
    primary_db_id = data["replication_details"]["primary"]["id"]
    primary_db_compartment_id = data["replication_details"]["primary"]["compartment_id"]
    primary_db_endpoint = data["replication_details"]["primary"]["endpoint"]
    primary_db_port = data["replication_details"]["primary"]["port"]
    primary_db_admin_user = data["replication_details"]["primary"]["admin_user"]
    primary_db_admin_secret_id = data["replication_details"]["primary"]["admin_secrect_id"]
    primary_db_replication_user = data["replication_details"]["primary"]["replication_user"]
    primary_db_replication_secret_id = data["replication_details"]["primary"]["replication_secrect_id"]
    replica_region = data["replication_details"]["replicas"][index]["region"]
    replica_db_id = data["replication_details"]["replicas"][index]["id"]
    replica_db_compartment_id = data["replication_details"]["replicas"][index]["compartment_id"]
    replica_db_endpoint = data["replication_details"]["replicas"][index]["endpoint"]
    replica_db_port = data["replication_details"]["replicas"][index]["port"]
    replica_db_admin_user = data["replication_details"]["replicas"][index]["admin_user"]
    replica_db_admin_secret_id = data["replication_details"]["replicas"][index]["admin_secrect_id"]
    replica_db_replication_user = data["replication_details"]["replicas"][index]["replication_user"]
    replica_db_replication_secret_id = data["replication_details"]["replicas"][index]["replication_secrect_id"]

    # Prepare a temporary regions file for OCI SDK configuration
    regions_file = prepare_regions_file(primary_region,replica_region)

    # Set up OCI signer and configuration
    oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    oci_primary_config = oci.config.from_file(file_location=regions_file, profile_name="PRIMARY")
    oci_replica_config = oci.config.from_file(file_location=regions_file, profile_name="REPLICA")

    # OCI get MySQL DB Systems details
    oci_primary_db_system_details = get_db_system_details(primary_db_id,oci_primary_config,oci_signer)
    if not oci_primary_db_system_details:
        os.remove(regions_file)
        logging.error(f"Failed to retrieve HeatWave MySQL Database System details: {primary_db_id}")
        sys.exit(1)

    oci_replica_db_system_details = get_db_system_details(replica_db_id,oci_replica_config,oci_signer)
    if not oci_replica_db_system_details:
        os.remove(regions_file)
        logging.error(f"Failed to retrieve HeatWave MySQL Database System details: {replica_db_id}")
        sys.exit(1)

    # OCI get Channel replication status
    oci_replica_channels_details = oci_replica_db_system_details.data.channels
    oci_replica_channel_id = get_repilca_channel_id(oci_replica_channels_details,primary_db_endpoint)
    if not oci_replica_channel_id:
        logging.error(f"No ACTIVE replica channel found for {replica_db_name} from {primary_db_endpoint}")
        os.remove(regions_file)
        sys.exit(1)
    # Check if Replicas is in Read / Only Mode
    elif oci_replica_db_system_details.data.database_mode != "READ_ONLY":
        #logging.warning(f"Replica {replica_db_name} is not in READ_ONLY mode.")
        logging.error(f"Replica {replica_db_name} is not in READ_ONLY mode.")
        os.remove(regions_file)
        sys.exit(1)

    oci_primary_db_admin_pass = get_secret_password(primary_db_admin_secret_id,oci_primary_config,oci_signer)
    if not oci_primary_db_admin_pass:
        os.remove(regions_file)
        logging.error(f"Failed to get Admin password of primary MySQL Database System in secret: {primary_db_admin_secret_id}")
        sys.exit(1)

    oci_replica_db_admin_pass = get_secret_password(replica_db_admin_secret_id,oci_replica_config,oci_signer)
    if not oci_replica_db_admin_pass:
        os.remove(regions_file)
        logging.error(f"Failed to get Admin password of replica MySQL Database System in secret: {replica_db_admin_secret_id}")
        sys.exit(1)

    oci_primary_db_replication_pass = get_secret_password(primary_db_replication_secret_id,oci_primary_config,oci_signer)
    if not oci_primary_db_replication_pass:
        os.remove(regions_file)
        logging.error(f"Failed to get Replication password of primary MySQL Database System in secret: {primary_db_replication_secret_id}")
        sys.exit(1)

    oci_replica_db_replication_pass = get_secret_password(replica_db_replication_secret_id,oci_replica_config,oci_signer)
    if not oci_replica_db_replication_pass:
        os.remove(regions_file)
        logging.error(f"Failed to get Replication password of replica MySQL Database System in secret: {replica_db_replication_secret_id}")
        sys.exit(1)
    
    PRIMARY_CONFIG = {
        "host": primary_db_endpoint,
        "user": primary_db_admin_user,
        "password": oci_primary_db_admin_pass
    }

    REPLICA_CONFIG = {
        "host": replica_db_endpoint,
        "user": replica_db_admin_user,
        "password": oci_replica_db_admin_pass
    }

    logging.info(f"Connecting to {primary_db_name} and {replica_db_name} systems...")

    primary_conn = connect_mysql(PRIMARY_CONFIG)
    replica_conn = connect_mysql(REPLICA_CONFIG)

    if not primary_conn or not replica_conn:
        logging.error(f"Failed to connect to one or both MySQL servers.")
        os.remove(regions_file)
        exit(1)

    logging.info(f"Fetching {primary_db_name} and {replica_db_name} replication statuses...")

    # Get the primary binlog status
    primary_status = get_replication_status(primary_conn, is_primary=True)
    if not primary_status:
        logging.error(f"Failed to retrieve {primary_db_name} status.")
        os.remove(regions_file)
        exit(1)

    # Get the replica status
    replica_status = get_replication_status(replica_conn, is_primary=False)
    if not replica_status:
        logging.error(f"Failed to retrieve {replica_db_name} status.")
        os.remove(regions_file)
        exit(1)
    else:
        replica_last_error = replica_status['Last_Errno']
        replica_io_running = replica_status['Replica_IO_Running']
        replica_sql_running = replica_status['Replica_SQL_Running']

        if replica_last_error != 0:
            logging.error(f"Error when processing relay log")
            os.remove(regions_file)
            exit(1)
        elif replica_io_running != "Yes":
            logging.error(f"I/O thread for reading the primary binary log is not running")
            os.remove(regions_file)
            exit(1)
        elif replica_sql_running != "Yes":
            logging.error(f"SQL thread for executing events in the relay log is not running")
            os.remove(regions_file)
            exit(1)
    
    # Set the primary DB in Read Only Mode
    logging.info(f"Putting {primary_db_name} in Read Only Mode...")
    oci_set_db_system_database_mode = set_db_system_database_mode(primary_db_id,oci_primary_config,oci_signer,"READ_ONLY")
    if not oci_set_db_system_database_mode:
        os.remove(regions_file)
        logging.error(f"Failed to put HeatWave MySQL Database System in READ_ONLY: {primary_db_id}")
        sys.exit(1)
    
    # Get the excuted GTID for Comapraison
    primary_gtid = get_gtid_executed(primary_conn)
    replica_gtid = get_gtid_executed(replica_conn)

    if not primary_gtid or not replica_gtid:
        # Put Primary in R/W again
        logging.error(f"Failed to retrieve GTID sets. Check MySQL connection.")
        logging.info(f"Putting back {primary_db_name} in Read Write Mode...")
        oci_set_db_system_database_mode = set_db_system_database_mode(primary_db_id,oci_primary_config,oci_signer,"READ_WRITE")
        os.remove(regions_file)
        exit(1)
    
    logging.info(f"Fetching for GTID gaps between {primary_db_name} and {replica_db_name}...")
    # Fing Gaps between primary and replica
    gaps = find_gtid_gaps(primary_gtid, replica_gtid)
    
    # if Gaps Loop for sometime and comapare GTID again
    if gaps:
        logging.warning(f"GTID Gap Detected! Missing transactions:")
        iterate = 1
        timeout = 240
        while (iterate != timeout) and gaps:
            for uuid, missing in gaps.items():
                logging.warning(f"Server UUID: {uuid}, Missing Transactions: {missing}")
                iterate += 1
                print(f"{iterate} {timeout}")
                if iterate == timeout:
                    logging.error(f"Replica {replica_db_name} is not synched with primary!")
                    logging.info(f"Putting back {primary_db_name} in Read Write Mode...")
                    oci_set_db_system_database_mode = set_db_system_database_mode(primary_db_id,oci_primary_config,oci_signer,"READ_WRITE")
                    os.remove(regions_file)
                    exit(1)
                else:
                    primary_gtid = get_gtid_executed(primary_conn)
                    replica_gtid = get_gtid_executed(replica_conn)
                    gaps = find_gtid_gaps(primary_gtid, replica_gtid)
                time.sleep(5);
    else:
        logging.info(f"No GTID gaps detected. {replica_db_name} is in sync with {primary_db_name}...")

    logging.info(f"Checking whether all GTIDs have been successfully applied to {replica_db_name}...")
    wait_gtid = wait_for_executed_gtid(replica_conn,replica_gtid)
    if wait_gtid == -1:
        logging.error(f"Timeout waiting for executed GTID in {replica_db_name}.")
        logging.info(f"Putting back {primary_db_name} in Read Write Mode...")
        set_db_system_database_mode(primary_db_id,oci_primary_config,oci_signer,"READ_WRITE")
        os.remove(regions_file)
        exit(1)
    else:
        logging.info(f"All GTIDs have been successfully applied to {replica_db_name}.")
        
    logging.info(f"Deleting replication channel on {replica_db_name} from {primary_db_endpoint}...")
    oci_delete_replication_channel = delete_replica_channel(oci_replica_channel_id,oci_replica_config,oci_signer)
    if not oci_delete_replication_channel:
        logging.error(f"Failed to delete replication channel: {oci_replica_channel_id}")
        logging.info(f"Putting back {primary_db_name} in Read Write Mode...")
        set_db_system_database_mode(primary_db_id,oci_primary_config,oci_signer,"READ_WRITE")
        os.remove(regions_file)
        exit(1)
    
    CHANNEL_SOURCE_CONFIG = {
        "source_type": "MYSQL",
        "hostname": replica_db_endpoint,
        "username": replica_db_replication_user,
        "password": oci_replica_db_replication_pass,
        "ssl_mode": "REQUIRED",
        "port": int(replica_db_port)
    }

    CHANNEL_TARGET_CONFIG = {
        "target_type": "DBSYSTEM",
        "db_system_id": primary_db_id
    }
    channel_display_name = "Replication from " + replica_db_endpoint
    logging.info(f"Creating replication channel on {primary_db_name} from {replica_db_endpoint}...")
    oci_create_replication_channel_id = create_replica_channel(CHANNEL_SOURCE_CONFIG,CHANNEL_TARGET_CONFIG,primary_db_compartment_id,channel_display_name,oci_primary_config,oci_signer)
    if not oci_create_replication_channel_id:
        logging.error(f"Failed to create replication channel: {oci_create_replication_channel_id}")
        logging.info(f"Putting back {primary_db_name} in Read Write Mode...")
        set_db_system_database_mode(primary_db_id,oci_primary_config,oci_signer,"READ_WRITE")
        os.remove(regions_file)
        exit(1)        

    # Set the Replica DB in Read Write Mode
    if oci_replica_db_system_details.data.database_mode != "READ_WRITE":
        logging.info(f"Putting {replica_db_name} in Read Write Mode...")
        oci_set_db_system_database_mode = set_db_system_database_mode(replica_db_id,oci_replica_config,oci_signer,"READ_WRITE")
        if not oci_set_db_system_database_mode:
            os.remove(regions_file)
            logging.error(f"Failed to put HeatWave MySQL Database System in READ_WRITE: {replica_db_id}")
            sys.exit(1)

    # Update Configuration JSON file
    logging.info(f"Updating {config_file_name} file...")
    data["replication_details"]["primary"]["region"] = replica_region
    data["replication_details"]["primary"]["db_unique_name"] = replica_db_name
    data["replication_details"]["primary"]["id"] = replica_db_id
    data["replication_details"]["primary"]["compartment_id"] = replica_db_compartment_id
    data["replication_details"]["primary"]["endpoint"] = replica_db_endpoint
    data["replication_details"]["primary"]["port"] = replica_db_port
    data["replication_details"]["primary"]["admin_user"] = replica_db_admin_user
    data["replication_details"]["primary"]["admin_secrect_id"] = replica_db_admin_secret_id
    data["replication_details"]["primary"]["replication_user"] = replica_db_replication_user
    data["replication_details"]["primary"]["replication_secrect_id"] = replica_db_replication_secret_id
    data["replication_details"]["replicas"][index]["region"] = primary_region
    data["replication_details"]["replicas"][index]["db_unique_name"] = primary_db_name
    data["replication_details"]["replicas"][index]["id"] = primary_db_id
    data["replication_details"]["replicas"][index]["compartment_id"] = primary_db_compartment_id
    data["replication_details"]["replicas"][index]["endpoint"] = primary_db_endpoint
    data["replication_details"]["replicas"][index]["port"] = primary_db_port
    data["replication_details"]["replicas"][index]["admin_user"] = primary_db_admin_user
    data["replication_details"]["replicas"][index]["admin_secrect_id"] = primary_db_admin_secret_id
    data["replication_details"]["replicas"][index]["replication_user"] = primary_db_replication_user
    data["replication_details"]["replicas"][index]["replication_secrect_id"] = primary_db_replication_secret_id
    upddate_config_file = update_config_file(config_file_name,data)
    if not upddate_config_file:
        os.remove(regions_file)
        logging.error(f"Failed to update {config_file_name}...")
        sys.exit(1)

    # Clean up temporary regions file
    os.remove(regions_file)
    logging.info(f"Switchover to {replica_db_name} process completed successfully.")

if __name__ == "__main__":
    print_cmd()
    switchover_roles()