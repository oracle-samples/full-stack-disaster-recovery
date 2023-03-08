#
# oci-objectstorage-fullstackdr-python version 1.0.
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#

import io
import os
import json
import sys
from fdk import response

import oci.object_storage

def handler(ctx, data: io.BytesIO=None):
    try:
        body = json.loads(data.getvalue())
        source_bucket = body["sourceBucket"]
        target_bucket = body["targetBucket"]
        source_region = body["sourceRegion"]
        target_region = body["targetRegion"]
        operation = body["operation"]
    except Exception:
        raise Exception('Input a JSON object in the format: \'{"sourceBucket": "<bucket name>"}, {"targetBucket": "<bucket name>"}, {"sourceRegion": "<source region>"}, {"targetRegion": "<target region>"}, {"operation": "<switchover or failover>"}\' ')

    print ("\nInput validated", flush=True)

    #Validate operation type
    if operation.lower() != 'switchover' and operation.lower() != 'failover': 
        print ("\nInvalid operation type "+operation)
        raise SystemExit
    
    print ("\nOperation type validated", flush=True)

    #Invoke performDR
    resp = performDR(source_bucket, target_bucket, source_region, target_region, operation)

    return response.Response(
        ctx,
        response_data=json.dumps(resp),
        headers={"Content-Type": "application/json"}
    )

def performDR(source_bucket, target_bucket, source_region, target_region, operation):
    signer = oci.auth.signers.get_resource_principals_signer()

    source_region_config_dict = {"region": source_region}
    target_region_config_dict = {"region": target_region}
    
    source_client = oci.object_storage.ObjectStorageClient(config=source_region_config_dict, signer=signer)
    target_client = oci.object_storage.ObjectStorageClient(config=target_region_config_dict, signer=signer)

    print ("\nGetting namespace", flush=True)

    namespace = source_client.get_namespace().data

    print ("\nnamespace = "+namespace, flush=True)

    # Check if target bucket exist
    try:
        get_bucket_response = target_client.get_bucket(namespace, target_bucket)
    except Exception as e:
        print (e)
        print ("\nTarget bucket "+target_bucket+" doesn't exist \n")
        raise SystemExit

    
    #Switchover
    if operation.lower() == 'switchover':
        # Check if source bucket exist
        try:
            get_bucket_response = source_client.get_bucket(namespace, source_bucket)
        except Exception as e:
            print (e)
            print ("\nSource bucket "+source_bucket+" doesn't exist \n")
            raise SystemExit

        # Get replication ID from source bucket
        replication_id = ""
        try:
            list_replication_policies_response = source_client.list_replication_policies(
                namespace_name=namespace,
                bucket_name=source_bucket)
            replication_id = list_replication_policies_response.data[0].id
        except Exception as e:
            print (e)
            print ("\nNo replication policy found in source bucket \n")
            raise SystemExit

        print ("\nReplication ID in the source bucket "+source_bucket+" is "+replication_id)

        # Stop replication - Delete replication policy on source bucket (this will enable the target bucket read/write automatically)

        print ("\nDeleting replication policy from the source bucket : "+source_bucket)

        try:
            delete_replication_policy_response = source_client.delete_replication_policy(
                namespace_name=namespace,
                bucket_name=source_bucket,
                replication_id=replication_id)
        except Exception as e:
            print (e)
            print ("\nCould not delete replication policy in source bucket \n")
            raise SystemExit

        print ("\nReplication policy delete from source bucket successfully! and target bucket "+target_bucket+" is now in read/write mode")

        #Setup reverse replication in the target bucket (i.e., create replication policy in the target bucket)

        print ("\nSetting up reverse replication in the target bucket "+target_bucket)

        try:
            create_replication_policy_response = target_client.create_replication_policy(
                namespace_name=namespace,
                bucket_name=target_bucket,
                create_replication_policy_details=oci.object_storage.models.CreateReplicationPolicyDetails(
                    name="FullStackDR_Repliction_Policy_to_"+source_region,
                    destination_region_name=source_region,
                    destination_bucket_name=source_bucket))
        except Exception as e:
            print(e)
            print ("\nCould not create reverse replication policy in target bucket "+target_bucket)
            raise SystemExit
        
        print ("\nSetting up reverse replication is successful in the target bucket "+target_bucket)
    #Failover
    elif operation.lower() == 'failover':
        #Make target bucket write, this will stop the replication and removes the replication policy
        print ("\nMake target bucket "+target_bucket+" writable")

        try:
            make_bucket_writable_response = target_client.make_bucket_writable(
                namespace_name=namespace,
                bucket_name=target_bucket)
        except Exception as e:
            print (e)
            print ("\nCould not make target bucket "+target_bucket+" writbale")
            raise SystemExit

        print ("\nTarget bucket "+target_bucket+" is now writable. Replication is stopped and replication policy is removed from target bucket "+target_bucket)
    
    return { "result": "Full Stack DR OSS Function executed successfully !" }