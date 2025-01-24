"""
Copyright (c) 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
"""
#!/usr/bin/python3.6.8 -Es
# -*- coding: utf-8 -*-

import logging
import json
import argparse
import oci
from argparse import RawDescriptionHelpFormatter

parser = argparse.ArgumentParser(
    prog="bss_update_cmk_multi_key.py",
    formatter_class=RawDescriptionHelpFormatter,    
    description="This script is used to update the encryption key on Volumes from a Volume Group "
    "after Disaster Recovery plan execution\n"
    "This is a multi key version. It uses volume freeform tags to collect the keys OCID\n"
    " [REQUIRED] params:\n"
    "   --drpg_id\n"
    "   --key_tag\n"
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
    "--key_tag",
    required=True,
    type= str,
    help="Freeform tag where kms key OCID is stored"
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
    global core_client
    global block_storage_client
    global FSDRclient    

    #for local or OCI instance execution point your oci config file below
    ociconfig = config_file
    #for cloud shell running profile must be region full name
    block_storage_client = None
    FSDRclient = None

    if profile == None:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        identity_client = oci.identity.IdentityClient(config={}, signer=signer)
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

        core_client = oci.core.ComputeClient(config)

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
                service_endpoint=service_endpoint,
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

def get_cmk_tag(volume_id,key_tag):
    if "boot" in volume_id:
        get_volume_response = block_storage_client.get_boot_volume(boot_volume_id = volume_id)
    else:
        get_volume_response = block_storage_client.get_volume(volume_id = volume_id)

    response_dict = json.loads(str(get_volume_response.data))
    tags_list = response_dict.get("freeform_tags", {})
    return tags_list.get(key_tag)

def update_kms_key(volume_id, kms_key_id):
    if kms_key_id != None:
        try:
            if "boot" in volume_id:
                update_response = block_storage_client.update_boot_volume_kms_key(
                    boot_volume_id = volume_id,
                    update_boot_volume_kms_key_details = oci.core.models.UpdateBootVolumeKmsKeyDetails(
                        kms_key_id = kms_key_id
                    )
                )   
                
            else:
                update_response = block_storage_client.update_volume_kms_key(
                    volume_id = volume_id,
                    update_volume_kms_key_details = oci.core.models.UpdateVolumeKmsKeyDetails(
                        kms_key_id = kms_key_id
                    )
                )  
            log(f"Volume {volume_id} successfully updated")
        except Exception as e:
            log(f"There was an exception updating kms key id on volume {volume_id}: {e}",level = 'ERROR')
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
    key_tag = args.key_tag
    service_endpoint = args.service_endpoint
    config_file = args.config_file

    if config_file==None:
        config_file = "/etc/opc/config"

    if not validate_string_is_an_ocid(drpg_id,"drprotectiongroup"):
        log("Drpg ID OCID " + drpg_id + " is not a properly formatted OCID")
        exit(-1)

    setupenv(profile, service_endpoint, config_file)

    #Get volume group details from drpg
    vgroup_ids = get_vgroup_id(drpg_id)

    for vgroup_id in vgroup_ids:
        #List all the volumes and boot volumes from volume group and their freeform tags
        log("Processing volume group: " + vgroup_id)
        volume_ids = get_volumes(vgroup_id)
        
        #Update kms_key ids from freeform tags to volumes and boot volumes from volume group
        for volume_id in volume_ids:
            kms_key_id = get_cmk_tag(volume_id,key_tag)
            validate_string_is_an_ocid(kms_key_id,"drprotectiongroup")
            if kms_key_id != None:
                log("Updating Volume " + volume_id + " with key " + kms_key_id)
                update_kms_key(volume_id, kms_key_id)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"The script finished on error: {e}",level = 'CRITICAL')
        exit(-1)
    
    