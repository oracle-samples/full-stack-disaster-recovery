#!/usr/bin/python3
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
    prog="bss_update_cmk_single_key.py",
    formatter_class=RawDescriptionHelpFormatter,    
    description="This script is used to update the encryption key on Volumes from a Volume Group "
    "after Disaster Recovery plan execution\n"
    "This is a single key version. It applies the same key to all volumes from Volume groups\n"
    " [REQUIRED] params:\n"
    "   --dr_protection_group_id\n"
    "   --kms_key_id\n"
    " [OPTIONAL] params:\n"
    "   --profile\n"
    "   --config-file\n"
    "   --service-endpoint\n"
)

parser.add_argument(
    "--dr_protection_group_id",
    required=True,
    type= str,
    help="Disaster recovery protection group OCID"
)

parser.add_argument(
    "--kms_key_id",
    required=True,
    type= str,
    help="encryption key OCID"
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
                service_endpoint=service_endpoint,
            )

def get_volumes(vgroup_id):
    get_volume_group_response = block_storage_client.get_volume_group(volume_group_id = vgroup_id)

    response_dict = json.loads(str(get_volume_group_response.data))
    volume_ids = response_dict.get("volume_ids", {})    
    return volume_ids

def get_vgroup_id(dr_protection_group_id):
    vgroup_ids = []

    get_dr_protection_group_response = FSDRclient.get_dr_protection_group(
        dr_protection_group_id=dr_protection_group_id
    )
    response_dict = json.loads(str(get_dr_protection_group_response.data))
    members_list = response_dict.get("members", {})
    for key in members_list:
        if key["member_type"] == "VOLUME_GROUP":
            vgroup_ids.append(key["member_id"])

    return  vgroup_ids

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

    dr_protection_group_id = args.dr_protection_group_id
    profile = args.profile
    kms_key_id = args.kms_key_id
    service_endpoint = args.service_endpoint
    config_file = args.config_file

    if config_file==None:
        config_file = "/etc/opc/config"

    if not validate_string_is_an_ocid(dr_protection_group_id,"drprotectiongroup"):
        log("Drpg ID OCID " + dr_protection_group_id + " is not a properly formatted OCID",level = 'ERROR')
        exit(-1)

    if not validate_string_is_an_ocid(kms_key_id,"key"):
        log("Key ID OCID " + kms_key_id + " is not a properly formatted OCID",level = 'ERROR')
        exit(-1)

    setupenv(profile, service_endpoint, config_file)

    #Get volume group details from drpg
    vgroup_ids = get_vgroup_id(dr_protection_group_id)

    for vgroup_id in vgroup_ids:
        #List all the volumes and boot volumes from volume group and their freeform tags
        log("Processing volume group: " + vgroup_id)
        volume_ids = get_volumes(vgroup_id)
        
        #Update kms_key ids from freeform tags to volumes and boot volumes from volume group
        for volume_id in volume_ids:            
            if kms_key_id != None:
                log("Updating Volume " + volume_id + " with key " + kms_key_id)
                update_kms_key(volume_id, kms_key_id)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"The script finished on error: {e}",level = 'CRITICAL')
        exit(-1)
    
