#!/bin/bash
#====================================================
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script oac-register-snapshot.sh imports OAC (Oracle Analytics Cloud) snapshot backup in the desired Region.
# This will be automatically executed during a switchover or failover orchestrated by Full Stack DR.
#
# You will have  to call oac-register-snapshot.sh use Parameters Region ID IAD/PHX uppercase.
#
# ----
# Usage
# ----
# oac-register-snapshot.sh <region ID>
#
# ----
# How to add this script to Full Stack DR plans
# ----
# You need to create one Plan Group for each switchover or failover plan in the
# DR protection group at both regions. The script needs to be installed on the movable
# compute instance you added as a member of the DR protection group.
#
# ----
# Examples
# ----
# Add following plan group to switchover & failover DR plans at PHX
#
# Plan Group: Switchover OAC snapshot to PHX (Standby)
#   Plan step 1: Recover OAC Snapshot (Standby) at PHX
#   Local script: /WheverYouPutTheScript/oac-register-snapshot.sh PHX
#   User: opc
#
# Add following plan group to switchover & failover DR plans at IAD
#
# Plan Group: Switchover OAC snapshot to IAD (Standby)
#   Plan step 1: Recover OAC Snapshot (Standby) at IAD
#   Local script: /WheverYouPutTheScript/oac-register-snapshot.sh IAD
#   User: opc
#
#======================================================

#User API Key Configuration File Info
# Region: us-ashburn-1, us-phoenix-1
# OCID of Tenancy and User
ociregion1=us-ashburn-1
ociregion2=us-phoenix-1
tenancy=ocid1.tenancy.oc1..xxxxxx
user=ocid1.user.oc1..xxxxxxx
fingerprint=44:22:05:xxxxxx
#Copy the downloaded API private key to the client VM and specify the absolute path (/home/opc/.oci/oci_api_key.pem)
oci_privateKey=/home/opc/keys/private.pem

#Enter the namespace for the object storage bucket. Get the Namespace value from the Bucket Information tab of the bucket.
namespace=xxxxxxx
#------------------------------------------------------------------------------------------------------------------------#
#REGION1
#------------------------------------------------------------------------------------------------------------------------#
#Enter the OCI Region Code. For example, IAD for us-ashburn-1 and PHX for us-phoenix-1 regions.
region1=IAD
#Enter the bucket name created for respective regions to store snapshots and data files.
bucket1=phxBucketReplication

### Provide the following information for the Target environemnt. ###
#Get the Target OAC Hostname
#Example: target_hostname=https://oacinstancename-namespace-xx.analytics.ocp.oraclecloud.com
target_hostname1=https://oacprimaryash-xxxxxx-ia.analytics.ocp.oraclecloud.com

#Get the IDCS URL or IAM Identity Domain URL
#Example: target_idcs_url=https://idcs-<guid>.identity.oraclecloud.com
target_idcs_url1=https://idcs-xxxxxxxxx.identity.oraclecloud.com

#Get the Scope of the Target OAC instance added to the Confidential Application
#Example: target_scope=https://xxxxxxxxxxxxxxxxxxxxxxx.analytics.ocp.oraclecloud.comurn:opc:resource:consumer::all
target_scope1=https://xxxxxxxxx.analytics.ocp.oraclecloud.comurn:opc:resource:consumer::all

#Run the below cmd on a shell and enter the output value
#echo -n "<ClientID>:<ClientSecret>" | base64 -w 0
target_AuthBase1=xxxxxxxxx

#------------------------------------------------------------------------------------------------------------------------#

#REGION2
#------------------------------------------------------------------------------------------------------------------------#
### Provide the following information for the Target environemnt. ###

#Enter the OCI Region Code. For example, IAD for us-ashburn-1 and PHX for us-phoenix-1 regions.
region2=PHX
#Enter the bucket name created for respective regions to store snapshots and data files.
bucket2=iadBucketReplication

### Provide the following information for the Target environemnt. ###
#Get the Target OAC Hostname
#Example: target_hostname=oacinstancename-namespace-xx.analytics.ocp.oraclecloud.com
target_hostname2=https://oacsecondaryphx-xxxxxxxxx.analytics.ocp.oraclecloud.com

#Get the IDCS URL or IAM Identity Domain URL
#Example: target_idcs_url=https://idcs-<guid>.identity.oraclecloud.com
target_idcs_url2=https://idcs-xxxxxxxxx.identity.oraclecloud.com

#Get the Scope of the Target OAC instance added to the Confidential Application
#Example: target_scope=https://xxxxxxxxxxxxxxxxxxxxxxx.analytics.ocp.oraclecloud.comurn:opc:resource:consumer::all
target_scope2=https://xxxxxxxxx.analytics.ocp.oraclecloud.comurn:opc:resource:consumer::all

#Run the below cmd on a shell and enter the output value
#echo -n "<ClientID>:<ClientSecret>" | base64 -w 0
target_AuthBase2=xxxxxxxxx

#------------------------------------------------------------------------------------------------------------------------#

#--------------CONDITION CHECK AND SET THE VARIABLES BASED ON OCI REGION SELECTED-------------#
if [ -z ${1} ]; then
        echo "This script needs an OCI Region code as an argument. For example, IAD for ashburn and PHX for phoenix regions."
        echo "Usage: $0 {region_code}"
        echo "Exiting......."
        exit
fi

regioncode=$1

echo "OCI Region Selected: $regioncode."

if [ "$region1" == "$regioncode" ]; then
        region=$ociregion1
        bucket=$bucket1
        target_hostname=$target_hostname1
        target_idcs_url=$target_idcs_url1
        target_scope=$target_scope1
        target_AuthBase=$target_AuthBase1
elif [ "$region2" == "$regioncode" ]; then
        region=$ociregion2
        bucket=$bucket2
        target_hostname=$target_hostname2
        target_idcs_url=$target_idcs_url2
        target_scope=$target_scope2
        target_AuthBase=$target_AuthBase2
else
        echo "Valid oci region code is not provided. Exiting......."
        exit
fi

rm -rf oci_config

echo '[DEFAULT]
user='$user'
fingerprint='$fingerprint'
key_file='$oci_privateKey'
tenancy='$tenancy'
region='$region'' > oci_config

chmod 400 oci_config

#---------------------------------------------------------------------------------------------#


#------SCRIPT-----

#workDir should be same as the workDir used in createSnapshot script.
workDir=$PWD/tmp

createTmpDir()
{
 if [ ! -d "$workDir" ]
  then
  #echo "make sure the work dir is same as create snapshot script"
  mkdir $workDir
 fi
}

getKeyWrapped()
{
 if [ ! -f $oci_privateKey ]
  then
  echo "exiting need private Key"
  exit
 fi

 cat $oci_privateKey|base64 -w 0 > $workDir/target_Keywrapped.txt
 targetKeywrapped=$(cat $workDir/target_Keywrapped.txt)
}

setRefreshToken()
{
 $PWD/getTargetRefreshToken.sh $regioncode
 refreshToken=$(cat targetRefreshToken.txt)
 accessToken=$(cat targetAccessToken.txt)
}

# Downloading the bar file and the data files from object storage
downloadBarZipFiles()
{
 oci os object list -ns $namespace -bn $bucket --config-file oci_config > bucketFiles.json
 fileName=`jq -r '.data[] | .name + ", " + ."time-created"' bucketFiles.json | sort -t"," -k2,2r | awk -F", " 'NR==1{print $1}' | awk -F"." '{print $1}'`
 rm -f bucketFiles.json
 # download the files
 barFile=$fileName.bar
 zipFile=$fileName.zip
 echo $fileName > $workDir/fileName.txt
 echo "DOWNLOADING THE BAR FILE FROM THE OBJECT STORAGE- - - - - - - - - - - - - - - - - - - - "$barFile
 oci os object get -ns $namespace -bn $bucket --name $barFile --file $barFile --config-file oci_config
 echo "DOWNLOADING THE DATA ZIP FILE FILE FROM THE OBJECT STORAGE- - - - - - - - - - - - - - - - - - - - "$zipFile
 oci os object get -ns $namespace -bn $bucket --name $zipFile --file $zipFile --config-file oci_config
}

validateFileName()
{
fileName=$(cat $workDir/fileName.txt)
 if [ -f $fileName.bar ];then
  echo "following bar file will be registered"
  echo $fileName.bar
 else
  echo "$fileName doesn't exit"
  exit
 fi
}

deleteRegSnap()
{

accessToken=$(cat $workDir/targetAccessToken.txt)

getSnapShotID

echo "DELETEING---"

if [ -s $workDir/snapshotID.txt ];then
 while read -r snapID;
 do
  echo "deleting this snapId - $snapID"
  curl -i --header "Authorization: Bearer $accessToken" --request DELETE $target_hostname/api/20210901/snapshots/$snapID
 done < $workDir/snapshotID.txt
fi
}


getSnapShotID()
{
accessToken=$(cat $workDir/targetAccessToken.txt)

 echo "gettting list of registered Snapshots"
 curl -i --header "Authorization: Bearer $accessToken" --request GET $target_hostname/api/20210901/snapshots >$workDir/allSnapshot.txt
 sed -i 's/"id":"/\n&/g' $workDir/allSnapshot.txt
 sed -i 's/"id":"/{"id":" /g' $workDir/allSnapshot.txt
 sed -i 's/","name"/ ","name"/g' $workDir/allSnapshot.txt
 grep -E '{"id":"|","name"' $workDir/allSnapshot.txt |awk '{print $2}' > $workDir/snapshotID.txt

 while read -r snapID;
 do
  echo "registered snapshot -  $snapID"
 done < $workDir/snapshotID.txt
}


registerSnapshot()
{

echo '{
    "type": "REGISTER",
    "name": "'$fileName'",
    "storage": {
        "type": "OCI_NATIVE",
        "bucket": "'$bucket'",
        "auth": {
            "type": "OSS_AUTH_OCI_USER_ID",
            "ociRegion": "'$region'",
            "ociTenancyId": "'$tenancy'",
            "ociUserId": "'$user'",
            "ociKeyFingerprint": "'$fingerprint'",
            "ociPrivateKeyWrapped": "'$targetKeywrapped'"
        }
    },
    "bar": {
        "uri": "file:///'$fileName'.bar"
    }
}' > $workDir/registerSnapshot.json


curl -i --header "Authorization: Bearer $accessToken" --header "Content-Type: application/json" --request POST $target_hostname/api/20210901/snapshots -d @$workDir/registerSnapshot.json

}


#RefreshToken Function

getNewRefreshAccessToken()
{
#This function will get a new RefreshToken - for next Run
# and get Access Token.

setRefreshToken


echo "curl --location --request POST '"$target_idcs_url"/oauth2/v1/token' \\
--header 'Authorization: Basic "$target_AuthBase"' \
--header 'Content-Type: application/x-www-form-urlencoded' \\
--data-urlencode 'grant_type=refresh_token' \\
--data-urlencode 'refresh_token="$refreshToken"' \\
--data-urlencode 'scope="$target_scope"'
" > targetToken.sh

chmod -fR 777 targetToken.sh
./targetToken.sh > $workDir/_targetToken.txt

cat $workDir/_targetToken.txt |sed 's/^.*refresh_token":"//' | sed 's/"}//' |awk '{print $0}'> targetRefreshToken.txt
cat $workDir/_targetToken.txt |sed 's/","token_type.*//'|sed 's/^.*":"//' |awk '{print $0}'> $workDir/targetAccessToken.txt
rm -rf $workDir/_targetToken.txt
}


restoreSnap()
{
getSnapShotID
snapID=$(cat $workDir/snapshotID.txt)
echo "restoring!!!!!!!!!!!!!!!!!!!!!!!"
echo sleep 7
echo '{
   "snapshot": {
      "id" : "'$snapID'",
      "password" : "Admin123"
   }
}' > $workDir/restore.json

echo "restore $snapID - in progress"

curl -i --header "Authorization: Bearer $accessToken" --header "Content-Type: application/json" --request POST $target_hostname/api/20210901/system/actions/restoreSnapshot -d @$workDir/restore.json > $workDir/restoreStatus.txt

sleep 5

}


requestStatus()
{
grep -r 'oa-work-request-id:' $workDir/restoreStatus.txt |awk '{print $2}' > $workDir/workid.txt
workid=$(cat $workDir/workid.txt)
url=$target_hostname/api/20210901/workrequests/$workid
curl -i --header "Authorization: Bearer $accessToken" --request GET "$url"
}

cleanUP()
{
rm -f targetAccessToken.txt
rm -f targetRefreshToken.txt
rm -f fileStatus.tmp
rm -f downloadData.prop
rm -f oci_config
rm -f $barFile
rm -f $zipFile
rm -rf $workDir
rm -f targetToken.sh
}


#------ Calling Function -----
createTmpDir
getKeyWrapped

#------

##### Getting AccessToken using Refresh Token ####
getNewRefreshAccessToken
downloadBarZipFiles
validateFileName
deleteRegSnap
registerSnapshot
restoreSnap
#requestStatus
cleanUP

exit
