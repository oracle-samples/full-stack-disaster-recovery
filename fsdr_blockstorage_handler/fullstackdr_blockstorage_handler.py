#!/usr/bin/python3.6.8 -Es
# -*- coding: utf-8 -*-
"""
Copyright (c) 2016, 2023, Oracle and/or its affiliates.  
Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/

OCI Full Stack Disaster Recovery Service (Full Stack DR) Blockstorage Handler.

This script is used to manage blockstorage volume attachment and detachment
when performing active/passive DR workflows in OCI Full Stack DR service.

The script has been tested on Python 3.6.8
"""
import sys
import json

# import datetime
# print("Starting OCI imports at {}".format(datetime.datetime.now()))
import oci.core.models
from oci import core as oci_core
from oci import regions as oci_regions
from oci import config as oci_config
from oci import disaster_recovery as oci_fsdr

# print("Finished OCI imports at {}".format(datetime.datetime.now()))

__author__ = "Oracle Corp."
__version__ = "1.0"
__copyright__ = (
    """ Copyright (c) 2022, Oracle and/or its affiliates. All rights reserved. """
)

# Windows is not supported
if sys.platform == "win32":
    print("ERROR: Full Stack DR Blockstorage Handler is not supported on Windows")
    sys.exit(1)

if sys.version_info < (3,):
    print("ERROR: Full Stack DR Blockstorage Handler is supported on Python 3.x")
    sys.exit(1)

import argparse
from argparse import RawDescriptionHelpFormatter
import datetime
import logging
import os

retry_strategy = oci.retry.RetryStrategyBuilder(  # Make up to 10 service calls
    max_attempts_check=True,
    max_attempts=10,
    # Don't exceed a total of 600 seconds for all service calls
    total_elapsed_time_check=True,
    total_elapsed_time_seconds=600,
    # Wait 45 seconds between attempts
    retry_max_wait_between_calls_seconds=45,
    # Use 2 seconds as the base number for doing sleep time calculations
    retry_base_sleep_time_seconds=2,
    # Retry on certain service errors:
    #
    #   - 5xx code received for the request
    #   - Any 429 (this is signified by the empty array in the retry config)
    #   - 400s where the code is QuotaExceeded or LimitExceeded
    service_error_check=True,
    service_error_retry_on_any_5xx=True,
    service_error_retry_config={400: ["QuotaExceeded", "LimitExceeded"], 429: []},
    # Use exponential backoff and retry with full jitter, but on throttles use
    # exponential backoff and retry with equal jitter
    backoff_type=oci.retry.BACKOFF_FULL_JITTER_EQUAL_ON_THROTTLE_VALUE,
).get_retry_strategy()

# BEGIN -- parser definition
parser = argparse.ArgumentParser(
    prog="fullstackdr_blockstorage_handler.py",
    formatter_class=RawDescriptionHelpFormatter,
    description="This script is used to manage blockstorage volume attachment and "
    "detachment when performing active/passive DR workflows in Oracle "
    "Full Stack  Disaster Recovery Service. "
    " When using this script for 'switchover' workflows, configure two "
    "separate scripts, first a script of type (mode) "
    "'switchover_precheck' which will execute first, and a second script "
    "of type (mode) 'switchover' which will execute after the precheck. "
    "When using for 'failover' workflows, configure two separate "
    "scripts, a script of type (mode) "
    "'failover_precheck' which will execute first, and a second script "
    "of type 'failover' which will execute after the precheck. "
    ".\n\n"
    "Pass parameters to this script using either a single JSON object "
    "preceded by the --json switch, or pass them as a series as individual"
    "parameters preceded by the individual switches documented below\n"
    "These two methods of invocation are shown in the examples below:\n"
    "Using a single object as a JSON argument:\n"
    "python3 fullstackdr_blockstorage_handler.py "
    "\n\t--json {"
    '\n\t\t"mode": "switchover_precheck",'
    '\n\t\t"auth": "instance",'
    '\n\t\t"primary_instance_id": "ocid1.instance.oc1.iad.hmvwntfwa",'
    '\n\t\t"primary_dr_device_list": '
    '"ocid1.volume.oc1.iad.pncudb2dwq:/dev/oracleoci/oraclevde:iscsi,'
    'ocid1.volume.oc1.iad.uyoaajpxxna:/dev/oracleoci/oraclevdf:paravirtualized",'
    '\n\t\t"primary_drpg_id": '
    '"ocid1.drprotectiongroup.oc1.iad.t6wqjeqjzpnq",'
    '\n\t\t"standby_drpg_id": '
    '"ocid1.drprotectiongroup.oc1.phx.zolqwamacc5q",'
    '\n\t\t"standby_instance_id": "ocid1.instance.oc1.phx.4dyccvpja"'
    "\n\t}"
    "\nOr, using separate arguments:"
    "\npython3 fullstackdr_blockstorage_handler.py "
    '\n\t\t--mode="switchover_precheck"'
    '\n\t\t--auth="instance"'
    '\n\t\t--primary_instance_id="ocid1.instance.oc1.iad.hmvwntfwa",'
    '\n\t\t--primary_dr_device_list="ocid1.volume.oc1.iad.pncudb2dwq:/dev'
    "/oracleoci/oraclevde:iscsi,"
    'ocid1.volume.oc1.iad.uyoaajpxxna:/dev/oracleoci/oraclevdf:paravirtualized",'
    '\n\t\t--primary_drpg_id="ocid1.drprotectiongroup.oc1.iad.t6wqjeqjzpnq",'
    '\n\t\t--standby_drpg_id="ocid1.drprotectiongroup.oc1.phx.zolqwamacc5q",'
    '\n\t\t--standby_instance_id="ocid1.instance.oc1.phx.4dyccvpja"'
    "\n\nThis script works with Python 3.x\n\n",
)

parser.add_argument(
    "--json",
    required=False,
    type=str,
    help="Use this switch when passing all arguments "
    "combined into a single JSON object",
)
parser.add_argument(
    "--mode",
    required=False,
    type=str,
    help="The execution mode.  Must be one of: \n"
    "\tswitchover_precheck,\n\tfailover_precheck,\n"
    "\tswitchover,\n\t or failover",
)
parser.add_argument(
    "--auth",
    required=False,
    type=str,
    help="The authentication mode.  Must be one of: \n"
    '\tfile,\n\t or instance.  Use "file" '
    "when using ~/.oci/config for authenticaiton.  Use "
    '"instance" when using instance principal for '
    "authentication.",
)
parser.add_argument(
    "--primary_instance_id",
    required=False,
    type=str,
    help="The OCID of the primary instance.\n"
    "For example: "
    "ocid1.instance.oc1.iad.sky7zxjkqpl",
)
parser.add_argument(
    "--primary_dr_device_list",
    required=False,
    type=str,
    help="The list of blockstorage devices to detach from the primary instance.\n"
    "Provide this list using the sample format shown below. You must list all the "
    "volumes that are to be detached/attached.  This list of volumes must be comma "
    "separated.  Each member in this volume list must contain three parts separated by "
    "colons. Namely: the OCID of the volume, the path where the volume will attach, "
    "and the type of attachment.  All this information can be obtained from the block "
    "volume's page in the OCI console. \n"
    "Example showing a device list of two (2) volumes:\n"
    "ocid1.volume.oc1.iad.jpncudb2dwq:/dev/oracleoci/oraclevde:iscsi,"
    "\nocid1.volume.oc1.iad.yoaajpxxna:/dev/oracleoci/oraclevdf:paravirtualized",
)
parser.add_argument(
    "--primary_drpg_id",
    required=False,
    type=str,
    help="The OCID of the primary DR Protection Group.\n"
    "For example: "
    "ocid1.drprotectiongroup.oc1.iad.t6wqjeqjzpnq",
)
parser.add_argument(
    "--standby_drpg_id",
    required=False,
    type=str,
    help="The OCID of the standby DR Protection Group.\n"
    "For example: "
    "ocid1.drprotectiongroup.oc1.phx.zolqwamacc5q",
)
parser.add_argument(
    "--standby_instance_id",
    required=False,
    type=str,
    help="The OCID of the standby instance.\n"
    "For example: "
    "ocid1.instance.oc1.phx.hkxl3api9zx",
)
# END -- parser definition


def main():
    """
    Initial entry point
    """
    now = datetime.datetime.now()
    loggerObject = _Logger(now)
    log = loggerObject.get_logger()

    log.info("Starting Full Stack DR Blockstorage Handler...")

    args = argument_parser(log)
    print("Args mode = {}".format(args.mode))
    validate_args(args, log)

    if args.mode == "switchover_precheck":
        switchover_precheck(args, log)
    elif args.mode == "failover_precheck":
        failover_precheck(args, log)
    elif args.mode == "switchover":
        switchover(args, log)
    elif args.mode == "failover":
        failover(args, log)
    else:
        log.fatal(
            "FATAL ERROR: Encountered an unknown mode [{}]. Terminating script.".format(
                args.mode
            )
        )
        exit(-1)


def argument_parser(log):
    """
    Argument Parser
    """

    # Parse input arguments
    parser_args, unknown = parser.parse_known_args()

    if unknown:
        parser.print_help()
        log.error("Unknown option specified: {}".format(unknown))
        exit(-1)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        exit(-1)

    if parser_args.json:
        try:
            json_data = json.loads(parser_args.json)
            parser_args.mode = json_data["mode"]
            parser_args.auth = json_data["auth"]
            parser_args.primary_instance_id = json_data["primary_instance_id"]
            parser_args.primary_dr_device_list = json_data["primary_dr_device_list"]
            parser_args.primary_drpg_id = json_data["primary_drpg_id"]
            parser_args.standby_drpg_id = json_data["standby_drpg_id"]
            parser_args.standby_instance_id = json_data["standby_instance_id"]
            parser_args.json = None

        except ValueError as e:
            print("Exception parsing JSON args: {}".format(e))

    return parser_args


def validate_args(args, log):
    """
    Validate scripts arguments
    """
    log.info("Argument list for validation: [{}]".format(args))

    mode_list = ["switchover_precheck", "failover_precheck", "switchover", "failover"]
    auth_list = ["file", "instance"]

    # Validate mode
    if args.mode is None:
        parser.print_help()
        log.error("ERROR: --mode argument cannot be empty or missing".format(args.mode))
        log.error("--mode argument must be one of {}".format(mode_list))
        exit(-1)
    elif args.mode.strip() not in mode_list:
        parser.print_help()
        log.error("ERROR: Unknown mode [{}]".format(args.mode))
        log.error("--mode argument must be one of {}".format(mode_list))
        exit(-1)
    else:
        args.mode = "".join(args.mode.split())
        log.info("\tmode = {}".format(args.mode))

    # Validate auth type
    if args.auth is None:
        parser.print_help()
        log.error("ERROR: --auth argument cannot be empty or missing")
        log.error("--auth argument must be one of {}".format(auth_list))
        exit(-1)
    if args.auth.strip() not in auth_list:
        parser.print_help()
        log.error("ERROR: Unknown auth [{}]".format(args.auth))
        log.error("--auth argument must be one of {}".format(auth_list))
        exit(-1)
    else:
        args.auth = "".join(args.auth.split())
        log.info("\tauth = {}".format(args.auth))

    # Validate primary instance OCID
    if args.primary_instance_id is None:
        parser.print_help()
        log.error("ERROR: --primary_instance_id argument cannot be empty or missing")
        exit(-1)
    elif not validate_string_is_an_ocid(args.primary_instance_id.strip(), "instance"):
        parser.print_help()
        log.error(
            "ERROR: Primary instance OCID [{}] is not a properly formatted OCID".format(
                args.primary_instance_id
            )
        )
        exit(-1)
    else:
        args.primary_instance_id = "".join(args.primary_instance_id.split())
        log.info("\tprimary_instance_id = {}".format(args.primary_instance_id))

    # Validate standby instance OCID
    if args.standby_instance_id is None:
        parser.print_help()
        log.error("ERROR: --standby_instance_id argument cannot be empty or missing")
        exit(-1)
    if not validate_string_is_an_ocid(args.standby_instance_id.strip(), "instance"):
        parser.print_help()
        log.error(
            "ERROR: Standby instance OCID [{}] is not a properly formatted OCID".format(
                args.standby_instance_id
            )
        )
        exit(-1)
    else:
        args.standby_instance_id = "".join(args.standby_instance_id.split())
        log.info("\tstandby_instance_id = {}".format(args.standby_instance_id))

    # Validate primary DRPG OCID
    if args.primary_drpg_id is None:
        parser.print_help()
        log.error("ERROR: --primary_drpg_id argument cannot be empty or missing")
        exit(-1)
    if not validate_string_is_an_ocid(
        args.primary_drpg_id.strip(), "drprotectiongroup"
    ):
        parser.print_help()
        log.error(
            "ERROR: Primary DR Protection Group OCID [{}] is not a properly formatted OCID".format(
                args.primary_drpg_id
            )
        )
        exit(-1)
    else:
        args.primary_drpg_id = "".join(args.primary_drpg_id.split())
        log.info("\tprimary_drpg_id = {}".format(args.primary_drpg_id))

    # Validate standby DRPG OCID
    if args.standby_drpg_id is None:
        parser.print_help()
        log.error("ERROR: --standby_drpg_id argument cannot be empty or missing")
        exit(-1)
    if not validate_string_is_an_ocid(
        args.standby_drpg_id.strip(), "drprotectiongroup"
    ):
        parser.print_help()
        log.error(
            "ERROR: Standby DR Protection Group OCID [{}] is not a properly formatted OCID".format(
                args.standby_drpg_id
            )
        )
        exit(-1)
    else:
        args.standby_drpg_id = "".join(args.standby_drpg_id.split())
        log.info("\tstandby_drpg_id = {}".format(args.standby_drpg_id))

    # Validate device list
    if args.primary_dr_device_list is None:
        parser.print_help()
        log.error("ERROR: --standby_drpg_id argument cannot be empty or missing")
        exit(-1)
    args.primary_dr_device_list = "".join(args.primary_dr_device_list.split())
    validate_device_list(args.primary_dr_device_list, log)
    log.info("\tprimary_dr_device_list = {}".format(args.primary_dr_device_list))


def validate_string_is_an_ocid(ocid, kind):
    """
    Validate that the input string is an OCID of specified kind
    """
    ocid_parts = ocid.split(".")
    return ocid_parts[0].startswith("ocid") & (ocid_parts[1] == kind)


def validate_device_list(device_string, log):
    """
    Validate that the device string from user is properly formatted using the format:
    ocid:device_path:attchment_type
    e.g. ocid1.volume.oc1.iad.gdheruiakl:/dev/oracleoci/oraclevdf:iscsi
         ocid1.volume.oc1.iad.zmncqrtyui:/dev/oracleoci/oraclevde:paravirtualized
    """
    volumes_list = list()
    device_paths_list = list()
    if not device_string:
        log.error(
            "Cannot have an empty string/list as argument for --primary_dr_device_list"
        )
        exit(-1)
    device_list = device_string.split(",")
    for device in device_list:
        device_parts = device.split(":")
        if len(device_parts) < 3:
            log.error(
                "ERROR: Device [{}] in device list [{}] is not a properly formatted or valid device "
                "specification".format(device, device_string)
            )
            exit(-1)
        elif (
            device_parts[0].startswith("ocid1.volume")
            and device_parts[1].startswith("/dev/oracleoci/oracle")
            and ("iscsi" in device_parts[2] or "paravirtualized" in device_parts[2])
        ):
            pass
        else:
            log.error(
                "ERROR: Device [{}] in device list [{}] is not a properly formatted or valid device "
                "specification".format(device, device_string)
            )
            exit(-1)

        # Now add the device parts to separate lists for further checking
        volumes_list.append(device.split(":")[0])
        device_paths_list.append(device.split(":")[1])

    # Check if user input has any duplicates
    if (len(volumes_list) != len(set(volumes_list))) or (
        len(device_paths_list) != len(set(device_paths_list))
    ):
        log.error(
            "ERROR: Device list [{}] contains duplicate volumes or devices".format(
                device_string
            )
        )
        exit(-1)


def create_primary_region_oci_clients(args, log):
    """
    Create the various primary region OCI clients we need and return them in a hash
        - Compute - PRIMARY region
        - Blockstorage - PRIMARY region
        - FSDR - PRIMARY region
    """
    compute_client = None
    blockstorage_client = None
    fsdr_client = None
    primary_clients_dict = {}

    if args.auth == "file":
        region = get_region_from_ocid(args.primary_instance_id, log)
        config = oci_config.from_file()
        config["region"] = region
        log.info(
            "Creating primary region OCI clients for region [{}] using file-based authentication".format(
                region
            )
        )

        # Initialize Clients
        # compute_client = oci_core.ComputeClient(config, retry_strategy=retry_strategy)
        # blockstorage_client = oci_core.BlockstorageClient(config, retry_strategy=retry_strategy)
        # fsdr_client = oci_fsdr.DisasterRecoveryClient(config, retry_strategy=retry_strategy)
        compute_client = oci_core.ComputeClient(config)
        blockstorage_client = oci_core.BlockstorageClient(config)
        fsdr_client = oci_fsdr.DisasterRecoveryClient(config)
    elif args.auth == "instance":
        region = get_region_from_ocid(args.primary_instance_id, log)
        config = {"region": region}
        log.info(
            "Creating primary region OCI clients for region [{}] using instance principal authentication".format(
                region
            )
        )
        # By default this will hit the auth service in the region returned by
        # http://169.254.169.254/opc/v1/instance/region on the instance.
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        compute_client = oci_core.ComputeClient(config=config, signer=signer)
        blockstorage_client = oci_core.BlockstorageClient(config=config, signer=signer)
        fsdr_client = oci_fsdr.DisasterRecoveryClient(config=config, signer=signer)
    else:
        log.fatal(
            "FATAL ERROR: Encountered an unknown auth type [{}]. Terminating script.".format(
                args.auth
            )
        )
        exit(-1)

    # Add clients to dict
    primary_clients_dict["primary_compute_client"] = compute_client
    primary_clients_dict["primary_blockstorage_client"] = blockstorage_client
    primary_clients_dict["primary_fsdr_client"] = fsdr_client

    log.info("Finished creating primary region OCI clients")

    return primary_clients_dict


def create_standby_region_oci_clients(args, log):
    """
    Create the various primary region OCI clients we need and return them in a hash
        - Compute - STANDBY region
        - Blockstorage - STANDBY region
        - FSDR - STANDBY region
    """
    compute_client = None
    blockstorage_client = None
    fsdr_client = None
    standby_clients_dict = {}

    if args.auth == "file":
        region = get_region_from_ocid(args.standby_instance_id, log)
        config = oci_config.from_file()
        config["region"] = region

        log.info(
            "Creating standby region OCI clients for region [{}] using file-based authentication".format(
                region
            )
        )

        # Initialize Clients
        # compute_client = oci_core.ComputeClient(config, retry_strategy=retry_strategy)
        # blockstorage_client = oci_core.BlockstorageClient(config, retry_strategy=retry_strategy)
        # fsdr_client = oci_fsdr.DisasterRecoveryClient(config, retry_strategy=retry_strategy)
        compute_client = oci_core.ComputeClient(config)
        blockstorage_client = oci_core.BlockstorageClient(config)
        fsdr_client = oci_fsdr.DisasterRecoveryClient(config)
    elif args.auth == "instance":
        # By default this will hit the auth service in the region returned by
        # http://169.254.169.254/opc/v1/instance/region on the instance.
        region = get_region_from_ocid(args.standby_instance_id, log)
        # config = {'region': region}
        config = {}
        log.info(
            "Creating standby region OCI clients for region [{}] using instance principal "
            "authentication".format(region)
        )

        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        compute_client = oci_core.ComputeClient(config=config, signer=signer)
        blockstorage_client = oci_core.BlockstorageClient(config=config, signer=signer)
        fsdr_client = oci_fsdr.DisasterRecoveryClient(config=config, signer=signer)
    else:
        log.fatal(
            "FATAL ERROR: Encountered an unknown auth type [{}]. Terminating script.".format(
                args.auth
            )
        )
        exit(-1)

    # Add clients to dict
    standby_clients_dict["standby_compute_client"] = compute_client
    standby_clients_dict["standby_blockstorage_client"] = blockstorage_client
    standby_clients_dict["standby_fsdr_client"] = fsdr_client

    log.info("Finished creating standby region OCI clients")

    return standby_clients_dict


def switchover_precheck(args, log):
    """
    Run a switchover precheck
    """
    log.info(
        "==================  B E G I N   S W I T C H O V E R   P R E C H E C K  =================="
    )

    log.info("-----------------  Create OCI Clients  ----------------------")
    # Create primary and standby region OCI clients
    log.info("Creating OCI clients for primary and standby regions")
    primary_clients_dict = create_primary_region_oci_clients(args, log)
    standby_clients_dict = create_standby_region_oci_clients(args, log)

    primary_compute_client = primary_clients_dict["primary_compute_client"]
    primary_blockstorage_client = primary_clients_dict["primary_blockstorage_client"]
    primary_fsdr_client = primary_clients_dict["primary_fsdr_client"]

    standby_compute_client = standby_clients_dict["standby_compute_client"]
    standby_blockstorage_client = standby_clients_dict["standby_blockstorage_client"]
    standby_fsdr_client = standby_clients_dict["standby_fsdr_client"]

    log.info(
        "--------------  Get primary & standby instance metadata  ----------------"
    )
    # Get metadata for primary and standby instances
    log.info(
        "Getting metadata for primary instance [{}]".format(args.primary_instance_id)
    )
    primary_instance_metadata = primary_compute_client.get_instance(
        args.primary_instance_id
    )

    log.info(
        "Getting metadata for standby instance [{}]".format(args.standby_instance_id)
    )
    standby_instance_metadata = standby_compute_client.get_instance(
        args.standby_instance_id
    )

    log.info("---------------  Validate instance lifecycle states  ----------------")
    # Validate lifecycle state off primary and standby instances
    log.info(
        "Validating lifecycle state for primary instance [{}]".format(
            args.primary_instance_id
        )
    )
    validate_instance_lifecycle_state(primary_instance_metadata.data, log)

    log.info(
        "Validating lifecycle state for standby instance [{}]".format(
            args.primary_instance_id
        )
    )
    validate_instance_lifecycle_state(standby_instance_metadata.data, log)

    log.info("----------  Get primary and standby DRPG member lists  ------------")
    # Get list of members from primary and standby DRPGs
    log.info("Getting member list from primary DRPG [{}]".format(args.primary_drpg_id))
    primary_drpg_member_list = get_member_list_from_drpg(
        primary_fsdr_client, args.primary_drpg_id, log
    )

    log.info("Getting member list from standby DRPG [{}]".format(args.standby_drpg_id))
    standby_drpg_member_list = get_member_list_from_drpg(
        standby_fsdr_client, args.standby_drpg_id, log
    )

    log.info(
        "----------  Validate primary and standby instance DRPG membership  ------------"
    )
    # Check if primary instance belongs to primary DRPG
    log.info("Checking if primary instance belongs to primary DRPG")
    if not check_membership_in_drpg(
        args.primary_instance_id, args.primary_drpg_id, primary_drpg_member_list, log
    ):
        log.error(
            "ERROR: Invalid DR configuration. Primary instance [{}] does not belong to primary DRPG [{}] ".format(
                args.primary_instance_id, args.primary_drpg_id
            )
        )
        exit(-1)

    # Check if standby instance belongs to standby DRPG
    log.info("Checking if standby instance belongs to standby DRPG")
    if not check_membership_in_drpg(
        args.standby_instance_id, args.standby_drpg_id, standby_drpg_member_list, log
    ):
        log.error(
            "ERROR: Invalid DR configuration. Standby instance [{}] does not belong to standby DRPG [{}] ".format(
                args.standby_instance_id, args.standby_drpg_id
            )
        )
        exit(-1)

    log.info("----------  Validate standby instance device paths  ------------")
    # Check if standby instance device attachment paths are available
    log.info("Checking if standby instance device attachment paths are available")
    check_instance_device_attachment_paths_are_free(
        standby_compute_client,
        standby_instance_metadata.data,
        args.primary_dr_device_list,
        log,
    )

    log.info("----------  Validate primary instance volume attachments  ------------")
    # Get all volumes attached to primary instance
    log.info(
        "Getting volume attachments for primary instance [{}]".format(
            args.primary_instance_id
        )
    )
    primary_instance_all_volume_attachments_list = get_volume_attachments_for_instance(
        primary_compute_client, primary_instance_metadata.data, log
    )

    # Validate that device list provided by user (in args) matches attached volumes
    # NOTE: this method checks the device list against attachments and also returns the found attachments
    log.info(
        "Validating that all devices specified in device list [{}] are attached to primary instance [{}]".format(
            args.primary_dr_device_list, args.primary_instance_id
        )
    )

    list_dr_attachments = validate_and_get_attachments_from_device_list(
        primary_instance_metadata.data,
        primary_instance_all_volume_attachments_list,
        args.primary_dr_device_list,
        log,
    )

    log.info("----------  Validate standby volumes and volume groups  ------------")
    # Get list of DR volumes corresponding to our DR device attachments
    list_dr_volumes = get_dr_volumes_list(
        list_dr_attachments, primary_blockstorage_client, log
    )

    # Ensure that all volumes in DR volume list belong to a volume group in DRPG
    check_dr_volume_member_of_drpg_volume_groups(
        list_dr_volumes,
        args.primary_drpg_id,
        primary_drpg_member_list,
        primary_blockstorage_client,
        log,
    )

    log.info("----------  Validate primary volume groups replication  ------------")
    # Ensure that all volume groups in primary DRPG have replication configured
    check_replication_enabled_drpg_volume_groups(
        primary_drpg_member_list, args.standby_drpg_id, primary_blockstorage_client, log
    )
    log.info(
        "==================  E N D   S W I T C H O V E R   P R E C H E C K  =================="
    )


def failover_precheck(args, log):
    """
    Run a failover precheck
    """
    log.info(
        "==================  B E G I N   F A I L O V E R   P R E C H E C K  =================="
    )

    log.info("-----------------  Create OCI Clients  ----------------------")
    # Create primary and standby region OCI clients
    log.info("Creating OCI clients on standby region only")
    standby_clients_dict = create_standby_region_oci_clients(args, log)

    standby_compute_client = standby_clients_dict["standby_compute_client"]
    standby_blockstorage_client = standby_clients_dict["standby_blockstorage_client"]
    standby_fsdr_client = standby_clients_dict["standby_fsdr_client"]

    log.info("--------------  Get standby instance metadata  ----------------")
    # Get metadata for standby instance
    log.info(
        "Getting metadata for standby instance [{}]".format(args.standby_instance_id)
    )
    standby_instance_metadata = standby_compute_client.get_instance(
        args.standby_instance_id
    )

    log.info("--------------  Validate standby instance state  ----------------")
    # Validate lifecycle state off standby instance
    log.info(
        "Validating lifecycle state for standby instance [{}]".format(
            args.primary_instance_id
        )
    )
    validate_instance_lifecycle_state(standby_instance_metadata.data, log)

    log.info(
        "--------------  Validate standby instance membership in standby DRPG  ----------------"
    )
    # Get list of members from standby DRPG
    log.info("Getting member list from standby DRPG [{}]".format(args.standby_drpg_id))
    standby_drpg_member_list = get_member_list_from_drpg(
        standby_fsdr_client, args.standby_drpg_id, log
    )

    # Check if standby instance belongs to standby DRPG
    log.info("Checking if standby instance belongs to standby DRPG")
    if not check_membership_in_drpg(
        args.standby_instance_id, args.standby_drpg_id, standby_drpg_member_list, log
    ):
        log.error(
            "ERROR: Invalid DR configuration. Standby instance [{}] does not belong to standby DRPG [{}] ".format(
                args.standby_instance_id, args.standby_drpg_id
            )
        )
        exit(-1)

    log.info("--------------  Validate standby instance device paths  ----------------")
    # Check if standby instance device attachment paths are available
    log.info("Checking if standby instance device attachment paths are available")
    check_instance_device_attachment_paths_are_free(
        standby_compute_client,
        standby_instance_metadata.data,
        args.primary_dr_device_list,
        log,
    )

    log.info(
        "==================  E N D   F A I L O V E R   P R E C H E C K  =================="
    )


def switchover(args, log):
    """
    Run a switchover
    """
    log.info(
        "===========================  B E G I N   S W I T C H O V E R  ==========================="
    )

    log.info("-----------------  Create OCI Clients  ----------------------")

    # Create primary and standby region OCI clients
    log.info("Creating OCI clients for primary and standby regions")
    primary_clients_dict = create_primary_region_oci_clients(args, log)
    standby_clients_dict = create_standby_region_oci_clients(args, log)

    primary_compute_client = primary_clients_dict["primary_compute_client"]
    primary_blockstorage_client = primary_clients_dict["primary_blockstorage_client"]
    primary_fsdr_client = primary_clients_dict["primary_fsdr_client"]

    standby_compute_client = standby_clients_dict["standby_compute_client"]
    standby_blockstorage_client = standby_clients_dict["standby_blockstorage_client"]
    standby_fsdr_client = standby_clients_dict["standby_fsdr_client"]

    log.info(
        "--------------  Identify restored volumes in standby region ----------------"
    )
    # Get list of standby DRPG members
    log.info("Get list of standby DRPG members")
    standby_drpg_member_list = get_member_list_from_drpg(
        standby_fsdr_client, args.standby_drpg_id, log
    )

    # Find matching restored volumes in standby region that correspond to the primary (source) volumes
    log.info("Find matching volumes in restored standby volume groups")
    matching_restored_volumes_dict = (
        find_matching_volumes_in_restored_standby_volume_groups(
            args, standby_drpg_member_list, standby_blockstorage_client, log
        )
    )

    log.info(
        "--------------  Get primary & standby instance metadata  ----------------"
    )
    # Get metadata for primary and standby instances
    log.info(
        "Getting metadata for primary instance [{}]".format(args.primary_instance_id)
    )
    primary_instance_metadata = primary_compute_client.get_instance(
        args.primary_instance_id
    )

    standby_compute_client = standby_clients_dict["standby_compute_client"]
    log.info(
        "Getting metadata for standby instance [{}]".format(args.standby_instance_id)
    )
    standby_instance_metadata = standby_compute_client.get_instance(
        args.standby_instance_id
    )

    log.info("--------------  Stop primary instance  ----------------")
    # Stop the primary instance if it is running
    log.info(
        "Checking to see if primary instance [{}] needs to to STOPPED".format(
            args.primary_instance_id
        )
    )
    if primary_instance_metadata.data.lifecycle_state == "RUNNING":
        log.info(
            "Primary instance [{}] is RUNNING.  Attempting to stop instance...".format(
                args.primary_instance_id
            )
        )
        perform_instance_action(
            args.primary_instance_id, "STOP", "STOPPED", primary_compute_client, log
        )
    else:
        log.info(
            "Primary instance [{}] is already STOPPED.".format(args.primary_instance_id)
        )

    log.info("--------------  Detach volumes from primary instance  ----------------")
    # Detach volumes from the primary instance
    detach_volumes_from_instance(
        matching_restored_volumes_dict,
        primary_instance_metadata.data,
        primary_compute_client,
        log,
    )

    log.info("--------------  Attach volumes to standby instance  ----------------")
    # Attach restored volumes to the standby instance
    attach_restored_volumes_to_instance(
        matching_restored_volumes_dict,
        standby_instance_metadata.data,
        standby_compute_client,
        log,
    )

    log.info(
        "===========================  E N D   S W I T C H O V E R  ==========================="
    )


def failover(args, log):
    """
    Run a failover
    """
    log.info(
        "===========================  B E G I N   F A I L O V E R  ==========================="
    )

    log.info("-----------------  Create OCI Clients  ----------------------")
    # Create standby region OCI clients
    log.info("Creating OCI clients for standby region only")
    standby_clients_dict = create_standby_region_oci_clients(args, log)

    standby_compute_client = standby_clients_dict["standby_compute_client"]
    standby_blockstorage_client = standby_clients_dict["standby_blockstorage_client"]
    standby_fsdr_client = standby_clients_dict["standby_fsdr_client"]

    log.info(
        "--------------  Identify restored volumes in standby region ----------------"
    )
    # Get list of standby DRPG members
    standby_drpg_member_list = get_member_list_from_drpg(
        standby_fsdr_client, args.standby_drpg_id, log
    )

    # Find matching restored volumes in standby region that correspond to the primary (source) volumes
    matching_restored_volumes_dict = (
        find_matching_volumes_in_restored_standby_volume_groups(
            args, standby_drpg_member_list, standby_blockstorage_client, log
        )
    )
    log.info("--------------  Get standby instance metadata  ----------------")
    # Get metadata for standby instance
    standby_compute_client = standby_clients_dict["standby_compute_client"]
    log.info(
        "Getting metadata for standby instance [{}]".format(args.standby_instance_id)
    )
    standby_instance_metadata = standby_compute_client.get_instance(
        args.standby_instance_id
    )

    log.info("--------------  Attach volumes to standby instance  ----------------")
    # Attach restored volumes to the standby instance
    attach_restored_volumes_to_instance(
        matching_restored_volumes_dict,
        standby_instance_metadata.data,
        standby_compute_client,
        log,
    )

    log.info(
        "===========================  E N D   F A I L O V E R  ==========================="
    )


def get_region_from_ocid(ocid, log):
    """
    Return region from the ID
    """
    region_tla = ocid.split(".")[3]
    return oci_regions.get_region_from_short_name(region_tla)


def get_volume_attachments_for_instance(compute_client, instance, log):
    """
    Get all "attached" volume attachments for instance.
    """
    ret_list = list()
    volume_attachment_list = compute_client.list_volume_attachments(
        instance.compartment_id, instance_id=instance.id
    ).data

    log.info(
        "Found [{}] volumes in attachment list for instance [{}]".format(
            len(volume_attachment_list), instance.id
        )
    )
    for attachment in volume_attachment_list:
        if attachment.lifecycle_state == "ATTACHED":
            log.info(
                "Attachment [{}] for instance [{}] is in [{}] state".format(
                    attachment.id, instance.id, attachment.lifecycle_state
                )
            )
            ret_list.append(attachment)
        else:
            log.info(
                "WARNING: Skipping attachment [{}] for instance [{}] in [{}] state".format(
                    attachment.id, instance.id, attachment.lifecycle_state
                )
            )

    log.info(
        "Returning [{}] volume attachments for instance [{}]".format(
            len(ret_list), instance.id
        )
    )

    return ret_list


def validate_instance_lifecycle_state(primary_instance_metadata, log):
    """
    Validate an instance's lifecycle state
    """
    instance_valid_lifecycle_states = ["RUNNING", "STARTING", "STOPPING", "STOPPED"]
    if primary_instance_metadata.lifecycle_state not in instance_valid_lifecycle_states:
        log.error(
            "ERROR: Instance [{}] is not in an acceptable lifecycle state".format(
                primary_instance_metadata.id
            )
        )
        log.error(
            "Instance lifecycle must be one of {}".format(
                instance_valid_lifecycle_states
            )
        )
        exit(-1)

    log.info(
        "Lifecycle state [{}] is an acceptable state for instance [{}]".format(
            primary_instance_metadata.lifecycle_state, primary_instance_metadata.id
        )
    )


def validate_and_get_attachments_from_device_list(
    primary_instance_metadata,
    primary_instance_volume_attachments_list,
    arg_primary_dr_device_list,
    log,
):
    """
    Validate that each device in device list has a matching attachment and return all matching attachments
    """
    list_attachments_to_return = list()

    primary_dr_device_list = arg_primary_dr_device_list.split(",")
    for device in primary_dr_device_list:
        device = device.strip()
        log.info(
            "Checking if user-specified volume [{}] is attached to instance at [{}]".format(
                device.split(":")[0], device.split(":")[1]
            )
        )
        device_found = False
        for attachment in primary_instance_volume_attachments_list:
            if device.split(":")[0] == attachment.volume_id:
                log.info(
                    "SUCCESS: User-specified volume [{}] is attached using attachment [{}]".format(
                        device.split(":")[0], attachment.id
                    )
                )
                list_attachments_to_return.append(attachment)

                if device.split(":")[1] == attachment.device:
                    log.info(
                        "SUCCESS: User-specified volume [{}] is attached at path [{}] attachment [{}]".format(
                            device.split(":")[0], attachment.device, attachment.id
                        )
                    )
                    list_attachments_to_return.append(attachment)
                    device_found = True
                    break
                else:
                    log.error(
                        "ERROR: Instance [{}] does not have any volume [{}] attached at [{}] specified in "
                        "[--primary_dr_device_list] argument".format(
                            primary_instance_metadata.id,
                            device.split(":")[0],
                            device.split(":")[1],
                        )
                    )
                    exit(-1)

        if device_found is False:
            log.error(
                "ERROR: Instance [{}] does not have any volume [{}] attached at [{}] specified in "
                "[--primary_dr_device_list] argument".format(
                    primary_instance_metadata.id,
                    device.split(":")[0],
                    device.split(":")[1],
                )
            )
            exit(-1)

    return list_attachments_to_return


def get_member_list_from_drpg(fsdr_client, drpg_id, log):
    """
    Get list of members from DRPG
    """
    get_drpg_response = fsdr_client.get_dr_protection_group(drpg_id)
    return get_drpg_response.data.members


def check_membership_in_drpg(member_id, drpg_id, drpg_member_list, log):
    """
    Returns true if member_id found in DRPG, else false
    """
    drpg_member_id_list = list()
    if drpg_member_list:  # check to make sure list is not empty
        for drpg_member in drpg_member_list:
            drpg_member_id_list.append(drpg_member.member_id)

    if member_id in drpg_member_id_list:
        log.info(
            "SUCCESS: Member [{}] was found in DRPG [{}]".format(member_id, drpg_id)
        )
        return True
    else:
        log.info(
            "FAILED: Member [{}] was NOT found in DRPG [{}]".format(member_id, drpg_id)
        )
        return False


def check_instance_device_attachment_paths_are_free(
    compute_client, instance, device_list, log
):
    """
    Check and verify that the device paths for this instance are free for attaching devices
    """
    device_paths_list = list()
    volume_attachments_list = get_volume_attachments_for_instance(
        compute_client, instance, log
    )
    for device in device_list.split(","):
        device_paths_list.append(device.split(":")[1])

    for volume_attachment in volume_attachments_list:
        if volume_attachment.device in device_paths_list:
            log.error(
                "ERROR: Instance [{}] already has a device attached at path [{}]".format(
                    instance.id, volume_attachment.device
                )
            )
            exit(-1)

    log.info(
        "For instance [{}], all required attachment device paths are free: [{}]".format(
            instance.id, device_paths_list
        )
    )


def get_dr_volumes_list(list_dr_attachments, blockstorage_client, log):
    """
    Get a list of DR volumes corresponding to the list of attachments
    """
    dr_volumes_list = list()
    for attachment in list_dr_attachments:
        log.info(
            "Getting volume [{}] for attachment [{}]".format(
                attachment.volume_id, attachment.id
            )
        )
        volume_response = blockstorage_client.get_volume(attachment.volume_id)
        dr_volumes_list.append(volume_response.data)

    return dr_volumes_list


def check_dr_volume_member_of_drpg_volume_groups(
    list_dr_volume_ids, drpg_id, drpg_member_list, blockstorage_client, log
):
    """
    Verify that each volume in list_dr_volume belongs to a volume group in drpg_member_list
    """
    all_block_volumes_in_drpg_volume_groups = list()

    # First build a list of all block volumes in all volume groups
    for member in drpg_member_list:
        if isinstance(
            member, oci.disaster_recovery.models.DrProtectionGroupMemberVolumeGroup
        ):
            log.info(
                "Processing volume group [{}] found in DRPG".format(member.member_id)
            )
            volume_group_response = blockstorage_client.get_volume_group(
                member.member_id
            )
            for volume_id in volume_group_response.data.volume_ids:
                if ("bootvolume" not in volume_id) & ("volume" in volume_id):
                    all_block_volumes_in_drpg_volume_groups.append(volume_id)

    # Next, make sure that each of our DR volumes belongs to that meta list of all block volumes
    if all_block_volumes_in_drpg_volume_groups:
        for volume in list_dr_volume_ids:
            log.info(
                "Checking if DR volume [{}] belongs to a volume group in DRPG [{}]".format(
                    volume.id, drpg_id
                )
            )
            if volume.id not in all_block_volumes_in_drpg_volume_groups:
                log.error(
                    "ERROR: Invalid configuration. Volume [{}] does not belong to any volume group "
                    "in DRPG [{}]".format(volume.id, drpg_id)
                )
                exit(-1)
            else:
                log.info(
                    "SUCCESS: Volume [{}] belongs to volume group in DRPG [{}]".format(
                        volume.id, drpg_id
                    )
                )
    else:
        log.error(
            "ERROR: Invalid configuration. Could not find any volume groups in DRPG [{}]".format(
                drpg_id
            )
        )
        exit(-1)


def check_replication_enabled_drpg_volume_groups(
    drpg_member_list, standby_drpg_id, blockstorage_client, log
):
    """
    Verify that each volume group in drpg_member_list has replication enabled
    """
    standby_region = standby_drpg_id.split(".")[3]
    for member in drpg_member_list:
        if isinstance(
            member, oci.disaster_recovery.models.DrProtectionGroupMemberVolumeGroup
        ):
            log.info(
                "Checking volume group [{}] found in DRPG".format(member.member_id)
            )
            volume_group_response = blockstorage_client.get_volume_group(
                member.member_id
            )
            if not volume_group_response.data.volume_group_replicas:
                log.error(
                    "ERROR: Invalid configuration. Volume group [{}] does not have replication configured ".format(
                        volume_group_response.data.id
                    )
                )
                exit(-1)
            else:
                log.info(
                    "SUCCESS: Volume group [{}] has replication configured".format(
                        volume_group_response.data.id
                    )
                )

            # Make sure the replica is in the same region as our standby DRPG
            replica_region = volume_group_response.data.volume_group_replicas[
                0
            ].volume_group_replica_id.split(".")[3]
            if replica_region != standby_region:
                log.error(
                    "ERROR: Invalid configuration. Volume group [{}] target replica is in region [{}] which is "
                    "different from the standby region [{}] ".format(
                        volume_group_response.data.id, replica_region, standby_region
                    )
                )
                exit(-1)
            else:
                log.info(
                    "SUCCESS: Volume group [{}] replica is in the standby region [{}]".format(
                        volume_group_response.data.id, standby_region
                    )
                )


def find_matching_volumes_in_restored_standby_volume_groups(
    args, drpg_member_list, blockstorage_client, log
):
    """
    Find restored volumes in standby DRPG that match the source volumes

    Returns a dict which stores each primary volume OCID as the key along with the tuple
    (restored volume OCID, device_patH) as the value.  For example:
    { ocid1.volume.oc1.iad.asljfhghsk : (ocid1.volume.oc1.phx.quyertopw, /dev/oracleoci/oraclevdf)}
    """
    all_restored_volume_ids_list = list()
    primary_device_dict = dict()
    matching_volumes_dict = dict()

    device_string = args.primary_dr_device_list
    for device in device_string.split(","):
        primary_device_dict[device.split(":")[0]] = [
            device.split(":")[1],
            device.split(":")[2],
        ]

    for member in drpg_member_list:
        if isinstance(
            member, oci.disaster_recovery.models.DrProtectionGroupMemberVolumeGroup
        ):
            volume_group_response = blockstorage_client.get_volume_group(
                member.member_id
            )
            all_restored_volume_ids_list.extend(volume_group_response.data.volume_ids)

    # Remove boot volumes from our combined list and keep just volumes
    all_restored_volume_ids_list = list(
        filter(lambda x: ".bootvolume." not in x, all_restored_volume_ids_list)
    )

    for restored_volume_id in all_restored_volume_ids_list:
        volume_response = blockstorage_client.get_volume(restored_volume_id)
        volume = volume_response.data
        if isinstance(
            volume.source_details,
            oci.core.models.VolumeSourceFromBlockVolumeReplicaDetails,
        ):
            volume_replica_response = blockstorage_client.get_block_volume_replica(
                volume.source_details.id
            )
            volume_replica = volume_replica_response.data
            if volume_replica.block_volume_id in primary_device_dict:
                log.info(
                    "SUCCESS: Found a matching restored volume [{}] for "
                    "source volume [{}]".format(
                        restored_volume_id, volume_replica.block_volume_id
                    )
                )

                # NOTE: Use a dict to store the primary volume OCID as the key along with the list
                # [restored volume OCID, device_path, attachment_type) as the value.  For example:
                # { ocid1.volume.oc1.iad.asljfhghsk : [ocid1.volume.oc1.phx.quyertopw, /dev/oracleoci/oraclevdf, iscsi)}
                matching_volumes_dict[volume_replica.block_volume_id] = [
                    restored_volume_id,
                    primary_device_dict[volume_replica.block_volume_id][0],
                    primary_device_dict[volume_replica.block_volume_id][1],
                ]

    if len(matching_volumes_dict) != len(primary_device_dict):
        log.error(
            "ERROR: Could not find a restored volume matching each source volumes"
        )
        log.error(
            "Source volume list length = {}.  Matching volumes list length = {}".format(
                len(primary_device_dict), len(matching_volumes_dict)
            )
        )
        log.error("Source volumes list: {}".format(primary_device_dict))
        log.error("Matching volumes found list: {}".format(matching_volumes_dict))
        exit(-1)

    return matching_volumes_dict


def perform_instance_action(instance_id, action, final_state, compute_client, log):
    """
    Perform the specified action on the instance
    """
    action_response = compute_client.instance_action(instance_id, action)

    get_instance_response = oci.wait_until(
        compute_client,
        compute_client.get_instance(action_response.data.id),
        "lifecycle_state",
        final_state,
        max_interval_seconds=10,  # poll interval
        max_wait_seconds=600,  # maximum timeout
    )

    log.info(
        "Finished performing action [{}] on instance [{}].  "
        "Instance state is now [{}]".format(
            action, instance_id, get_instance_response.data.lifecycle_state
        )
    )


def detach_volumes_from_instance(
    matching_restored_volumes_dict, instance, compute_client, log
):
    """
    Detach volumes from instance
    matching_restored_volumes_dict is a dict where key = source_volume_id, and value = a list consisting of
    [restored_volume_id, device_path, attachment_type]
    e.g. {source_volume_id : [restored_volume_id, device_path, attachment_type]}
    """
    volume_attachments_list = get_volume_attachments_for_instance(
        compute_client, instance, log
    )
    log.info("Detaching volumes from instance [{}]".format(instance.id))
    for volume_attachment in volume_attachments_list:
        if volume_attachment.volume_id in matching_restored_volumes_dict:
            log.info(
                "Attempting to detach volume [{}] connected via device path [{}] and attachment [{}]...".format(
                    volume_attachment.volume_id,
                    matching_restored_volumes_dict[volume_attachment.volume_id][1],
                    volume_attachment.id,
                )
            )
            compute_client.detach_volume(volume_attachment.id)
            oci.wait_until(
                compute_client,
                compute_client.get_volume_attachment(volume_attachment.id),
                "lifecycle_state",
                "DETACHED",
                max_interval_seconds=10,
                max_wait_seconds=600,
            )
            log.info(
                "Finished detaching volume [{}] from instance [{}]".format(
                    volume_attachment.volume_id, instance.id
                )
            )


def attach_restored_volumes_to_instance(
    matching_restored_volumes_dict, instance, compute_client, log
):
    """
    Attach volumes to instance
    matching_restored_volumes_dict is a dict where key = source_volume_id, and value = a list consisting of
    [restored_volume_id, device_path, attachment_type]
    e.g. {source_volume_id : [restored_volume_id, device_path, attachment_type]}
    """
    log.info("Attaching volumes to instance [{}]".format(instance.id))
    for restored_volume_list in matching_restored_volumes_dict.values():
        log.info(
            "Attempting to attach volume [{}] to instance [{}] using device path [{}] and type [{}]".format(
                restored_volume_list[0],
                instance.id,
                restored_volume_list[1],
                restored_volume_list[2],
            )
        )

        display_name = "FSDR_attached__" + datetime.datetime.now().strftime(
            "_%Y%m%d.%H%M%S.%f"
        )
        if restored_volume_list[2] == "iscsi":
            iscsi_volume_attachment_response = compute_client.attach_volume(
                oci.core.models.AttachIScsiVolumeDetails(
                    display_name=display_name,
                    instance_id=instance.id,
                    device=restored_volume_list[1],
                    volume_id=restored_volume_list[0],
                )
            )
            oci.wait_until(
                compute_client,
                compute_client.get_volume_attachment(
                    iscsi_volume_attachment_response.data.id
                ),
                "lifecycle_state",
                "ATTACHED",
            )
            log.info(
                "Finished attaching ISCSI volume [{}] to instance [{}]".format(
                    restored_volume_list[0], instance.id
                )
            )
        elif restored_volume_list[2] == "paravirtualized":
            paravirtualized_volume_attachment_response = compute_client.attach_volume(
                oci.core.models.AttachParavirtualizedVolumeDetails(
                    display_name=display_name,
                    instance_id=instance.id,
                    device=restored_volume_list[1],
                    volume_id=restored_volume_list[0],
                )
            )
            oci.wait_until(
                compute_client,
                compute_client.get_volume_attachment(
                    paravirtualized_volume_attachment_response.data.id
                ),
                "lifecycle_state",
                "ATTACHED",
            )
        else:
            log.fatal(
                "ERROR: Unknown volume attachment type [{}] found for restored volume [{}]".format(
                    restored_volume_list[2], restored_volume_list[0]
                )
            )


class _Logger(object):
    """
    Loggers have the following attributes and methods. Note that Loggers should NEVER be instantiated directly,
    but always through the module-level function logging.get_logger(name). Multiple calls to get_logger()
    with the same name will always return a reference to the same Logger object.

    The logger provides API:

    info()
    debug()
    warning()
    error()
    """

    _logger = None
    _dirname = None
    _log_file = None

    def __init__(self, now):
        self.now = now
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.DEBUG)
        self._add_handlers()

    def _add_handlers(self):
        formatter = logging.Formatter("%(asctime)s:[%(levelname)s]: %(message)s")
        self._dirname = _FsdrConstants.FSDR_LOG_DIRECTORY
        if not os.path.isdir(self._dirname):
            os.mkdir(self._dirname)

        self._log_file = self._dirname + _FsdrConstants.FSDR_LOG_FILE_NAME
        fileHandler = logging.FileHandler(self._log_file)

        streamHandler = logging.StreamHandler()
        fileHandler.setFormatter(formatter)
        streamHandler.setFormatter(formatter)

        self._logger.addHandler(fileHandler)
        self._logger.addHandler(streamHandler)

        print(
            "{0}:[INFO]: Created logfile - [{1}]".format(
                self.now.strftime("%Y-%m-%d %H:%M:%S,%j"), self._log_file
            ),
            flush=True,
        )

    def get_logger(self):
        return self._logger

    def get_logfile(self):
        return self._log_file


class _FsdrConstants:
    """
    Full Stack DR Constants
    """

    def __init__(self):
        pass

    FSDR_DATE_TIME_FORMAT = "_%Y%m%d.%H%M%S.%f"

    FSDR_LOG_DIRECTORY = "/tmp/fsdr_logs"
    FSDR_LOG_FILE_NAME = (
        "/fsdr_blockstorage_handler_"
        + datetime.datetime.now().strftime(FSDR_DATE_TIME_FORMAT)
        + ".log"
    )


if __name__ == "__main__":
    main()
