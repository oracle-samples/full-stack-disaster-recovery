"""
Copyright (c) 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
"""
#!/usr/bin/python3.6.8 -Es
# -*- coding: utf-8 -*-

"""
Script tested in Python 3.6.8
Please follow this instruction to configure OCI CLI https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm
python3 bss_update_backup_policy_vg.py --profile <profile_name> --drpg_id <ocid_drpg> --backup_policy_id <ocid_backup_policy>
"""

import logging
import json
import argparse
import oci
from argparse import RawDescriptionHelpFormatter

parser = argparse.ArgumentParser(
    prog="bss_update_backup_policy_vg.py",
    formatter_class=RawDescriptionHelpFormatter,    
    description="This script is used to update the backup policies on Volume Groups "
    "after Disaster Recovery plan execution\n"
    " [REQUIRED] params:\n"
    "   --drpg_id\n"
    "   --backup_policy_id\n"
    " [OPTIONAL] params:\n"
    "   --profile\n"
    "   --config_file\n"
    "   --service_endpoint\n"
)

parser.add_argument(
    "--drpg_id",
    required=True,
    type= str,
    help="Disaster recovery protection group OCID"
)

parser.add_argument(
    "--backup_policy_id",
    required=True,
    type= str,
    help="Backup policy OCID"
)

parser.add_argument(
    "--profile",
    required=False,
    type=str,
    help="OCI cli profile. In case of Cloud Shell execution this must be the full region name"
)

parser.add_argument(
    "--service_endpoint",
    required=False,
    type=str,
    help="OCI service endpoint for disaster recovery API calls"
)

parser.add_argument(
    "--config_file",
    required=False,
    type= str,
    help="OCI cli config file (default /etc/opc/config)"    
)

def log(message, level = 'INFO'):
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %I:%M:%S %p',
        level=logging.INFO
    )

    logger = logging.getLogger()

    if level.upper() == 'DEBUG':
        logger.debug(message)
    elif level.upper() == 'INFO':
        logger.info(message)
    elif level.upper() == 'WARNING':
        logger.warning(message)
    elif level.upper() == 'ERROR':
        logger.error(message)
    elif level.upper() == 'CRITICAL':
        logger.critical(message)
    else:
        logger.info(message)

def setupenv(profile, service_endpoint, config_file):
    global ociconfig
    global block_storage_client
    global FSDRclient    

    #for local or OCI instance execution point your oci config file below
    ociconfig = config_file
    #for cloud shell running profile must be region full name
    #ociconfig = "/etc/oci/config"
    block_storage_client = None
    FSDRclient = None

    if profile == None:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        block_storage_client = oci.core.BlockstorageClient(config={}, signer=signer)

        if service_endpoint == None:
            #Use this constructor for prod environment
            FSDRclient = oci.disaster_recovery.DisasterRecoveryClient(
                config={}, signer=signer
            )                
        else:
            #Use this constructor for non prod environment
            FSDRclient = oci.disaster_recovery.DisasterRecoveryClient(
                config={},
                service_endpoint=service_endpoint,
                signer=signer
            )

    else:
        config = oci.config.from_file(
            ociconfig, profile_name=profile
        )
        block_storage_client = oci.core.BlockstorageClient(config)

        if service_endpoint == None:
            #Use this constructor for prod environment
            FSDRclient = oci.disaster_recovery.DisasterRecoveryClient(
                config
            )    
        else:
            #Use this constructor for non prod environment
            FSDRclient = oci.disaster_recovery.DisasterRecoveryClient(
                config,
                service_endpoint=service_endpoint
            )

def get_volumes(vgroup_id):
    get_volume_group_response = block_storage_client.get_volume_group(volume_group_id = vgroup_id)

    response_dict = json.loads(str(get_volume_group_response.data))
    volume_ids = response_dict.get("volume_ids", {})   
    return volume_ids

def get_vgroup_id(drpg_id):
    vgroup_ids = []

    get_dr_protection_group_response = FSDRclient.get_dr_protection_group(
        dr_protection_group_id=drpg_id
    )

    response_dict = json.loads(str(get_dr_protection_group_response.data))
    members_list = response_dict.get("members", {})

    for key in members_list:
        if key["member_type"] == "VOLUME_GROUP":
            vgroup_ids.append(key["member_id"])

    return  vgroup_ids
     

def update_backup_policy(vgroup_id, backup_policy_id):
    try:
        update_backup_policy_response = block_storage_client.create_volume_backup_policy_assignment(
            create_volume_backup_policy_assignment_details = oci.core.models.CreateVolumeBackupPolicyAssignmentDetails(
                asset_id = vgroup_id,
                policy_id = backup_policy_id,
                xrc_kms_key_id = None
            )
        )
        log("Volume group "+ vgroup_id + " successfully updated")
    except Exception as e:
        log(f"There was an exception updating backup policy {backup_policy_id} on volume group {vgroup_id}: {e}", level = 'ERROR')
        raise


def validate_string_is_an_ocid(ocid, kind):
    """
    Validate that the input string is an OCID of specified kind
    """
    try:
        ocid_parts = ocid.split(".")
        return ocid_parts[0].startswith("ocid") & (ocid_parts[1] == kind)
    except: 
        return False

def main():
    """
    Initial entry point
    """

    args = parser.parse_args()

    drpg_id = args.drpg_id
    profile = args.profile
    backup_policy_id = args.backup_policy_id
    service_endpoint = args.service_endpoint
    config_file = args.config_file
    if config_file==None:
        config_file = "/etc/opc/config"

    if not validate_string_is_an_ocid(drpg_id,"drprotectiongroup"):
        log("Drpg ID OCID " + drpg_id + " is not a properly formatted OCID")
        exit(-1)

    if not validate_string_is_an_ocid(backup_policy_id,"volumebackuppolicy"):
        log(" Key ID OCID " + backup_policy_id + " is not a properly formatted OCID")
        exit(-1)

    setupenv(profile, service_endpoint, config_file)

    #Get volume group details from drpg
    vgroup_ids = get_vgroup_id(drpg_id)

    for vgroup_id in vgroup_ids:
        #List all the volumes and boot volumes from volume group and their freeform tags
        log("Processing volume group: " + vgroup_id)
        #Update volume group backup policy
        if backup_policy_id != None:
            log("Updating volume group " + vgroup_id + " with backup policy " + backup_policy_id)
            update_backup_policy(vgroup_id, backup_policy_id)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"The script finished on error: {e}",level = 'CRITICAL')
        exit(-1)
    
    