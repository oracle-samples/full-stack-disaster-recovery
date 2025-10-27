#!/usr/bin/env python3
#
# full_stack_dr_non_std_db_handler.py
#
# Copyright (c) 2025, Oracle and/or its affiliates. All rights reserved.
#
#    NAME
#      full_stack_dr_non_std_db_handler.py - <one-line expansion of the name>
#
#    DESCRIPTION
#      <short description of component this file declares/defines>
#
#    NOTES
#      <other useful comments, qualifications, etc.>
#
#    MODIFIED   (MM/DD/YY)
#
#    santhosh     03/11/24 - Creation
#
import argparse
import datetime
import logging
import time

import oci
from oci._vendor.urllib3.exceptions import ConnectTimeoutError, MaxRetryError


# Parses Input to Boolean Flags
def parse_boolean(value):
    value = value.lower()

    if value in ["true", "yes", "y", "1", "t"]:
        return True
    elif value in ["false", "no", "n", "0", "f"]:
        return False

    return False


# Retrieve Subnet Details
def get_subnet_details(virtual_network_client, subnet_id):
    subnet_details = {}
    public_subnet_flag = False
    try:
        response = virtual_network_client.get_subnet(subnet_id)
        subnet_response = response.data
        logger.debug("Fetch Subnet details response - [{0}]".format(subnet_response))
        if "_prohibit_public_ip_on_vnic" in subnet_response.__dict__.keys():
            if subnet_response.prohibit_public_ip_on_vnic:
                public_subnet_flag = False
            else:
                public_subnet_flag = True

        subnet_details["public_subnet_flag"] = public_subnet_flag
    except (MaxRetryError, ConnectTimeoutError) as e:
        logger.info("Error in fetching DRPG Details: {0}".format(e.reason))
    return subnet_details


# Retrieve Database Details
def get_database_details(database_client, virtual_network_client, database_id):
    db_details = {}

    response = database_client.get_database(database_id=database_id)
    database_response = response.data
    logger.debug("Fetch database details response - [{0}]".format(database_response))

    db_details["dbName"] = database_response.db_name
    db_details["dbUniqueName"] = database_response.db_unique_name
    db_details["dblifecycleState"] = database_response.lifecycle_state
    db_details["db_home_id"] = database_response.db_home_id
    dbhome_response = database_client.get_db_home(db_home_id=db_details["db_home_id"])
    db_details["dbHomeLocation"] = dbhome_response.data.db_home_location
    db_details["dbVersion"] = dbhome_response.data.db_version

    db_details["compartmentId"] = database_response.compartment_id

    print(database_response.db_system_id)
    print(database_response.vm_cluster_id)
    db_details["dbSystemId"] = database_response.db_system_id
    db_details["vmClusterId"] = database_response.vm_cluster_id

    if database_response.db_system_id is None:
        dbnode_response = database_client.list_db_nodes(
            compartment_id=db_details["compartmentId"],
            vm_cluster_id=db_details["vmClusterId"],
        )
    else:
        dbnode_response = database_client.list_db_nodes(
            compartment_id=db_details["compartmentId"],
            db_system_id=db_details["dbSystemId"],
        )
    dbnode1_hostname = dbnode_response.data[0].hostname

    logger.debug("Fetch db node details response - [{0}]".format(dbnode_response.data))
    host_ip_id = dbnode_response.data[0].host_ip_id
    vnic_id = dbnode_response.data[0].vnic_id

    if host_ip_id is not None:
        response = virtual_network_client.get_private_ip(private_ip_id=host_ip_id)
        logger.debug(
            "Fetch DB Private IP details response - [{0}]".format(response.data)
        )
        db_details["dbNode1"] = response.data.ip_address
    else:
        response = virtual_network_client.get_vnic(vnic_id=vnic_id)
        logger.debug("Fetch DB Vnic details response - [{0}]".format(response.data))
        db_details["dbNode1"] = response.data.private_ip

    db_details["dbNode1_hostname"] = dbnode1_hostname
    return db_details


# Retrieve DB System Details
def get_db_system_details(database_client, db_system_id):
    db_system_details = {}

    response = database_client.get_db_system(db_system_id=db_system_id)
    database_response = response.data
    logger.debug("Fetch db system details response - [{0}]".format(database_response))
    db_system_details["id"] = database_response.id
    db_system_details["availabilityDomain"] = database_response.availability_domain
    db_system_details["subnetId"] = database_response.subnet_id
    db_system_details["sshPublicKeys"] = database_response.ssh_public_keys
    db_system_details["nodeCount"] = database_response.node_count
    db_system_details["dbSystemHostName"] = database_response.hostname
    db_system_details["dbSystemLifecycleState"] = database_response.lifecycle_state

    return db_system_details


# Retrieve DB VM Cluster Details
def get_db_vm_cluster_details(database_client, cloud_vm_cluster_id):
    db_vm_cluster_details = {}

    response = database_client.get_cloud_vm_cluster(
        cloud_vm_cluster_id=cloud_vm_cluster_id
    )
    database_response = response.data
    logger.debug(
        "Fetch db vm cluster details response - [{0}]".format(database_response)
    )
    db_vm_cluster_details["id"] = database_response.id
    db_vm_cluster_details["availabilityDomain"] = database_response.availability_domain
    db_vm_cluster_details["subnetId"] = database_response.subnet_id
    db_vm_cluster_details["sshPublicKeys"] = database_response.ssh_public_keys
    db_vm_cluster_details["nodeCount"] = database_response.node_count
    db_vm_cluster_details["dbSystemLifecycleState"] = database_response.lifecycle_state
    db_vm_cluster_details["hostname"] = database_response.hostname

    return db_vm_cluster_details


def poll_container_instance(container_instance_client, container_instance_id):
    total_polls = 10
    curr_poll = 1

    while True:
        response = container_instance_client.get_container_instance(
            container_instance_id=container_instance_id
        )

        container_instance_lifecycle_state = response.data.lifecycle_state
        lifecycle_states = ["ACTIVE", "FAILED", "DELETED"]
        if any(
            [
                lifecycle_state in container_instance_lifecycle_state
                for lifecycle_state in lifecycle_states
            ]
        ):
            logger.info(
                "Container Instance reached the terminal LifeCycleState [{0}]. Stopping the Poll.".format(
                    container_instance_lifecycle_state
                )
            )
            break
        if curr_poll > total_polls:
            logger.info("Reached the Maximum Poll Count. Stopping the Execution.")
            break
        else:
            curr_poll += 1
            logger.info(
                "Current LifeCycleState for Container Instance [{0}] is : [{1}]".format(
                    container_instance_id, container_instance_lifecycle_state
                )
            )
            logger.info(
                "Sleeping for 30 seconds before polling for container instance status again."
            )
            time.sleep(30)
    return container_instance_lifecycle_state


def poll_container_instance_logs(
    container_instance_client, container_instance_id, container_id
):
    if "PRECHECK" in args.db_operation:
        total_iterations = 120
    else:
        total_iterations = 360

    container_exit_status = -1
    curr_itr = 1

    while True:
        response = container_instance_client.retrieve_logs(container_id=container_id)
        container_logs = response.data.text
        sucess_log_strings = [
            "has been removed successfully",
            "DB Operation is completed successfully",
        ]
        error_log_strings = [
            "Operation has been failed",
        ]
        if any([log_str in container_logs for log_str in sucess_log_strings]):
            logger.info(
                "Found the Log string in Container Logs. Stopping the Execution."
            )
            container_exit_status = 0
            break
        if any([log_str in container_logs for log_str in error_log_strings]):
            logger.info(
                "Found the Log string in Container Logs. Stopping the Execution."
            )
            container_exit_status = 1
            break
        if curr_itr > total_iterations:
            logger.info(
                "Reached the Maximum Poll Count on Container Execution Logs. Stopping the Execution."
            )
            break
        else:
            curr_itr += 1
            logger.info("Sleeping for 5 seconds before polling for logs again.")
            response = container_instance_client.get_container_instance(
                container_instance_id=container_instance_id
            )

            container_instance_lifecycle_state = response.data.lifecycle_state
            logger.info(
                "LifeCycleState of Container Instance [{0}]: [{1}]".format(
                    container_instance_id, container_instance_lifecycle_state
                )
            )

            if container_instance_lifecycle_state != "ACTIVE":
                logger.info(
                    "Container LifeCycle State changed from Active to {0}. Stopping the Execution.",
                    container_instance_lifecycle_state,
                )
                break
            time.sleep(5)

    logger.info("==========================Container Logs=====================")
    logger.info("[{0}]".format(container_logs))
    return container_exit_status

def get_region_code(identity_client, region):
    list_regions_response = identity_client.list_regions()
    regions_list = list_regions_response.data
    print(regions_list)
    region_code = None
    for region_data in regions_list:
        if "name" in region_data and region_data["name"]:
            if "key" in region_data:
                region_code = region_data["key"].lower()
                break
    return region_code

##########################################################################
# Main
##########################################################################

# Get Command Line Parser
parser = argparse.ArgumentParser()
parser.add_argument("--database_ocid", help="Database OCID", required=True)
parser.add_argument("--vault_ocid", help="Standby VaultSecret OCID", required=True)
parser.add_argument("--db_operation", help="Database Operation", required=True)
parser.add_argument("--region", help="Region Name", required=True)
parser.add_argument(
    "--primary_db_unique_name", help="Primary Database Unique Name", required=True
)
parser.add_argument(
    "--standby_db_unique_name", help="Standby Database Unique Name", required=True
)
parser.add_argument("--drpg_ocid", help="DrProtectionGroup OCID", required=True)

parser.add_argument("--auth_type", help="Authentication Type", required=False)
parser.add_argument(
    "--delegation_token", help="Token Based Authentication", required=False
)
parser.add_argument("--log_level", help="Log Level", required=False)
args = parser.parse_args()

# Logging basic config
logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p"
)
logger = logging.getLogger(__name__)

if args.log_level is not None:
    if args.log_level == "WARNING":
        logger.setLevel("WARNING")
    elif args.log_level == "DEBUG":
        logger.setLevel("DEBUG")
    elif args.log_level == "ERROR":
        logger.setLevel("ERROR")
    elif args.log_level == "CRITICAL":
        logger.setLevel("CRITICAL")
else:
    logger.setLevel("INFO")

db_handler_version = "202510280000"

start_dt = datetime.datetime.now()
logger.info("Execution Start Date - [{0}]".format(start_dt))
dt_string = start_dt.strftime("%d%m%Y%H%M%S")

delegation_token = args.delegation_token
auth_type = args.auth_type

if delegation_token is not None:
    signer = oci.auth.signers.InstancePrincipalsDelegationTokenSigner(
        delegation_token=delegation_token
    )
if auth_type is not None and auth_type == "RESOURCE_PRINCIPAL":
    signer = oci.auth.signers.get_resource_principals_signer()
else:
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()

signer.region = args.region

container_instance_client = oci.container_instances.ContainerInstanceClient(
    config={}, signer=signer
)

container_instance_composite_client = (
    oci.container_instances.ContainerInstanceClientCompositeOperations(
        client=container_instance_client
    )
)

identity_client = oci.identity.IdentityClient(config={}, signer=signer)

db_client = oci.database.DatabaseClient(config={}, signer=signer)
network_client = oci.core.VirtualNetworkClient(config={}, signer=signer)

logger.debug("DB Handler - DB Introspection Start")

db_details = get_database_details(
    database_client=db_client,
    database_id=args.database_ocid,
    virtual_network_client=network_client,
)

logger.debug("DB System details response - [{0}]".format(db_details))


if db_details["dbSystemId"] is None:
    db_vm_cluster_details = get_db_vm_cluster_details(
        database_client=db_client, cloud_vm_cluster_id=db_details["vmClusterId"]
    )
    availability_domain = db_vm_cluster_details["availabilityDomain"]
    subnet_id = db_vm_cluster_details["subnetId"]
else:
    db_system_details = get_db_system_details(
        database_client=db_client, db_system_id=db_details["dbSystemId"]
    )
    logger.debug("DB System details - [{0}]".format(db_system_details))
    availability_domain = db_system_details["availabilityDomain"]
    subnet_id = db_system_details["subnetId"]

logger.debug("DB Handler - DB Introspection End")

valid_operations = [
    "SWITCHOVER",
    "SWITCHOVER_PRECHECK" "FAILOVER",
    "FAILOVER_PRECHECK",
    "CONVERT_PHYSICAL_TO_SNAPSHOT_STANDBY_PRECHECK",
    "REVERT_SNAPSHOT_TO_PHYSICAL_STANDBY_PRECHECK",
    "REVERT_SNAPSHOT_TO_PHYSICAL_STANDBY",
    "CONVERT_PHYSICAL_TO_SNAPSHOT_STANDBY",
]

if args.db_operation.upper() not in valid_operations:
    logger.info(
        "Invalid Database Operation passed - [{0}]".format(args.db_operation.upper())
    )

db_system_compartment_id = db_details["compartmentId"]

subnet_details = get_subnet_details(
    virtual_network_client=network_client, subnet_id=subnet_id
)

public_subnet = None
if "public_subnet_flag" in subnet_details.keys():
    public_subnet = subnet_details["public_subnet_flag"]

if public_subnet:
    assign_public_ip = True
else:
    assign_public_ip = False

ocir_registry = None

region_code = get_region_code(identity_client=identity_client, region=args.region)

if region_code is not None:
    ocir_registry = region_code + ".ocir.io"
    logger.info("OCIR Image Path to be used: [{0}]".format(ocir_registry))

if ocir_registry is None:
    logger.info(
        "ERROR: Could not fetch Container Image Endpoint - [{0}]".format(ocir_registry)
    )
    exit(1)

image_path = ocir_registry + "/siteguardprod/fsdr-oracledb-handler:latest"
ci_display_name = "FSDR-CI-Non-Std-DG-Operation-" + dt_string
container_display_name = "FSDR-Container-Non-Std-DG-Operation"
vnic_display_name = "FSDR-Container-VNIC-" + dt_string

arg1 = "--db_handler_version=" + db_handler_version
arg2 = "--database_ocid=" + args.database_ocid
arg3 = "--vault_ocid=" + args.vault_ocid
arg4 = "--region=" + args.region
arg5 = "--db_operation=" + args.db_operation
arg6 = "--primary_db_unique_name=" + args.primary_db_unique_name
arg7 = "--standby_db_unique_name=" + args.standby_db_unique_name
arg8 = "--drpg_ocid=" + args.drpg_ocid
arg9 = "--auth_type=RESOURCE_PRINCIPAL"

container_arguments = [
    arg1,
    arg2,
    arg3,
    arg4,
    arg5,
    arg6,
    arg7,
    arg8,
    arg9,
]

logger.debug("Container arguments - [{0}]".format(container_arguments))

# exit(1)
logger.debug("DB Handler - Create Container Instance Start")

create_container_instance_details = oci.container_instances.models.CreateContainerInstanceDetails(
    containers=[
        oci.container_instances.models.CreateContainerDetails(
            image_url=image_path,
            display_name=container_display_name,
            arguments=container_arguments,
        )
    ],
    compartment_id=db_system_compartment_id,
    availability_domain=availability_domain,
    shape="CI.Standard.E4.Flex",
    shape_config=oci.container_instances.models.CreateContainerInstanceShapeConfigDetails(
        ocpus=1, memory_in_gbs=1
    ),
    vnics=[
        oci.container_instances.models.CreateContainerVnicDetails(
            subnet_id=subnet_id,
            display_name=vnic_display_name,
            is_public_ip_assigned=assign_public_ip,
            skip_source_dest_check=True,
        )
    ],
    display_name=ci_display_name,
    graceful_shutdown_timeout_in_seconds=300,
    container_restart_policy="ON_FAILURE",
)

"""
primary_container_instance_composite_client.create_container_instance_and_wait_for_state(
    create_container_instance_details, wait_for_states=["ACTIVE", "FAILED", "DELETED"]
)

primary_container_instance_composite_client.delete_container_instance_and_wait_for_state(
    container_instance_id=container_instance_id,
    wait_for_states=["DELETED"],
)
"""

create_container_instance_response = (
    container_instance_client.create_container_instance(
        create_container_instance_details=create_container_instance_details
    )
)

logger.debug(
    "create_container_instance_response - [{0}]".format(
        create_container_instance_response.data
    )
)

work_request_id = create_container_instance_response.headers.get("opc-work-request-id")
container_instance_id = create_container_instance_response.data.id
container_id = create_container_instance_response.data.containers[0].container_id

logger.info("Work Request OCID - [{0}]".format(work_request_id))
logger.info("Container Instance OCID - [{0}]".format(container_instance_id))
logger.info("Container OCID - [{0}]".format(container_id))

container_instance_lifecycle_state = poll_container_instance(
    container_instance_client, container_instance_id
)

logger.debug("DB Handler - Create Container Instance End")

container_exit_status = -1

if container_instance_lifecycle_state == "ACTIVE":
    logger.info(
        "Container Instance is in Active State. Retrieving the Execution Logs from Container now."
    )
    logger.debug("DB Handler - Poll Container Logs Start")
    container_exit_status = poll_container_instance_logs(
        container_instance_client, container_instance_id, container_id
    )
    logger.debug("DB Handler - Poll Container Logs End")
else:
    if work_request_id is not None and work_request_id != "":
        response = container_instance_client.list_work_request_errors(
            work_request_id=work_request_id
        )
        logger.info("Retrieving the Container Instance WorkRequest ERRORS!!!")
        logger.info(
            "Current LifeCycleState for Container Instance [{0}] is :  [{1}]".format(
                container_instance_id, response.data
            )
        )

logger.debug("DB Handler - Delete Container Instance Start")

if (
    container_instance_lifecycle_state == "ACTIVE"
    or container_instance_lifecycle_state == "FAILED"
    or container_instance_lifecycle_state == "INACTIVE"
):
    logger.info("Deleting the Container Instance {0}!!!".format(container_instance_id))
    container_instance_composite_client.delete_container_instance_and_wait_for_state(
        container_instance_id=container_instance_id,
        wait_for_states=["FAILED", "SUCCEEDED", "CANCELED"],
    )
    response = container_instance_client.get_container_instance(
        container_instance_id=container_instance_id
    )

    container_instance_lifecycle_state = response.data.lifecycle_state
    logger.info(
        "LifeCycleState of Container Instance [{0}] after Delete Request: [{1}]".format(
            container_instance_id, container_instance_lifecycle_state
        )
    )

logger.debug("DB Handler - Delete Container Instance End")

end_dt = datetime.datetime.now()
time_taken = round((end_dt - start_dt).total_seconds(), 2)
logger.info("Execution End Date - [{0}]".format(end_dt))
logger.info("Total Execution Time - [{0}] seconds".format(time_taken))
exit(container_exit_status)
