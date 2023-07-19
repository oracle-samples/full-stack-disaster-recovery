#!/bin/bash
#====================================================
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script oac-create-snapshot.sh exports OAC (Oracle Analytics Cloud) snapshot backup in the desired Region.
# This will be in crontab process during a switchover or failover orchestrated by Full Stack DR using oac-chg-cronjob.sh.
#
# You will have  to call oac-create-snapshot.sh use Parameters Region ID IAD/PHX uppercase.
#
# ----
# Usage
# ----
# oac-create-snapshot.sh <region ID>
# 
# ----
# How to add this script to Full Stack DR plans
# ----
# This Script will not be added in the Full Stack DR Plans. However, when swithover or Failover happens
# oac-chg-cronjob.sh will do the swaping of crontab job 
#
#======================================================

#User API Key Configuration File Info
# Region: us-ashburn-1, us-phoenix-1
# OCID of Tenancy and User
ociregion1=us-ashburn-1
ociregion2=us-phoenix-1
tenancy=xxxxxxxxx
user=xxxxxxxxx
fingerprint=xxxxxxxxx
#Copy the downloaded API private key to the client VM and specify the absolute path (/home/opc/.oci/oci_api_key.pem)
oci_privateKey=/home/opc/keys/private.pem

#Enter the namespace for the object storage bucket. Get the Namespace value from the Bucket Information tab of the bucket.
namespace=xxxxxxxxx

#REGION1
#------------------------------------------------------------------------------------------------------------------------#
#Enter the OCI Region Code. For example, IAD for us-ashburn-1 and PHX for us-phoenix-1 regions.
region1=IAD
#Enter the bucket name created for respective regions to store snapshots and data files.
bucket1=iadBucket

### Provide the following information for the source environemnt. ###
#Get the Source OAC Hostname
#Example: source_hostname=oacinstancename-namespace-xx.analytics.ocp.oraclecloud.com 
source_hostname1=xxxxxxxxx

#Get the IDCS URL or IAM Identity Domain URL
#Example: source_idcs_url=https://idcs-<guid>.identity.oraclecloud.com
source_idcs_url1=xxxxxxxxx

#Get the Scope of the Source OAC instance added to the Confidential Application
#Example: source_scope=https://xxxxxxxxxxxxxxxxxxxxxxx.analytics.ocp.oraclecloud.comurn:opc:resource:consumer::all
source_scope1=xxxxxxxxx

#Run the below cmd on a shell and enter the output value
#echo -n "<ClientID>:<ClientSecret>" | base64 -w 0
source_AuthBase1=xxxxxxxxx

#Data Migration Utility Info
#-------------------------------------#
#Example: JAVA_HOME=/home/opc/jdk1.8.0_361
JAVA_HOME1=/home/opc/jdk1.8.0_361

#Example: dataMigrationHome=/home/opc/migrate-oac-data
dataMigrationHome1=/home/opc/migrate-oac-data

SOURCE_ENVIRONMENT1=OAC

#Example: SOURCE_URL=https://oacinstancename-namespace-xx.analytics.ocp.oraclecloud.com:443
SOURCE_URL1=xxxxxxxxx

#Example: SOURCE_USERNAME=oacadmin
SOURCE_USERNAME1=xxxxxxxxx

#Example: DATA_FRAGMENTS_DIRECTORY=/tmp/automate/DF  If any Folders doesnt exist create and use them in the script with absolute path.
DATA_FRAGMENTS_DIRECTORY1=/home/opc/migrate-oac-data

#Example: MAX_DATA_FRAGMENT_SIZE_IN_MB=500
MAX_DATA_FRAGMENT_SIZE_IN_MB1=500

#Example: SOURCE_PASSWORD=<Password@12345>
SOURCE_PASSWORD1=xxxxxxxxx

#Example: ENCRYPTION_PASSWORD=Admin123
ENCRYPTION_PASSWORD1=xxxxxxxxx
#-------------------------------------#
#------------------------------------------------------------------------------------------------------------------------#

#REGION2
#------------------------------------------------------------------------------------------------------------------------#
#Enter the OCI Region Code. For example, IAD for us-ashburn-1 and PHX for us-phoenix-1 regions.
region2=PHX
#Enter the bucket name created for respective regions to store snapshots and data files.
bucket2=phxBucket

### Provide the following information for the source environemnt. ###
#Get the Source OAC Hostname
#Example: source_hostname=oacinstancename-namespace-xx.analytics.ocp.oraclecloud.com
source_hostname2=

#Get the IDCS URL or IAM Identity Domain URL
#Example: source_idcs_url=https://idcs-<guid>.identity.oraclecloud.com
source_idcs_url2=

#Get the Scope of the Source OAC instance added to the Confidential Application
#Example: source_scope=https://xxxxxxxxxxxxxxxxxxxxxxx.analytics.ocp.oraclecloud.comurn:opc:resource:consumer::all
source_scope2=

#Run the below cmd on a shell and enter the output value
#echo -n "<ClientID>:<ClientSecret>" | base64 -w 0
source_AuthBase2=

#Data Migration Utility Info
#-------------------------------------#
#Example: JAVA_HOME=/home/opc/jdk1.8.0_361
JAVA_HOME2=/home/opc/jdk1.8.0_361

#Example: dataMigrationHome=/home/opc/migrate-oac-data
dataMigrationHome=/home/opc/migrate-oac-data

SOURCE_ENVIRONMENT2=OAC

#Example: SOURCE_URL=https://oacinstancename-namespace-xx.analytics.ocp.oraclecloud.com:443
SOURCE_URL2=

#Example: SOURCE_USERNAME=oacadmin
SOURCE_USERNAME2=

#Example: DATA_FRAGMENTS_DIRECTORY=/tmp/automate/DF  If any Folders doesnt exist create and use them in the script with absolute path.
DATA_FRAGMENTS_DIRECTORY2=/home/opc/migrate-oac-data

#Example: MAX_DATA_FRAGMENT_SIZE_IN_MB=500
MAX_DATA_FRAGMENT_SIZE_IN_MB2=500

#Example: SOURCE_PASSWORD=<Password@12345>
SOURCE_PASSWORD2=

#Example: ENCRYPTION_PASSWORD=Admin123
ENCRYPTION_PASSWORD2=Admin123
#-------------------------------------#
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
	source_hostname=$source_hostname1
	source_idcs_url=$source_idcs_url1
	source_scope=$source_scope1
	source_AuthBase=$source_AuthBase1
	JAVA_HOME=$JAVA_HOME1
	dataMigrationHome=$dataMigrationHome1
	SOURCE_ENVIRONMENT=$SOURCE_ENVIRONMENT1
	SOURCE_URL=$SOURCE_URL1
	SOURCE_USERNAME=$SOURCE_USERNAME1
	DATA_FRAGMENTS_DIRECTORY=$DATA_FRAGMENTS_DIRECTORY1
	MAX_DATA_FRAGMENT_SIZE_IN_MB=$MAX_DATA_FRAGMENT_SIZE_IN_MB1
	SOURCE_PASSWORD=$SOURCE_PASSWORD1
	ENCRYPTION_PASSWORD=$ENCRYPTION_PASSWORD1
elif [ "$region2" == "$regioncode" ]; then
        region=$ociregion2
        bucket=$bucket2
	source_hostname=$source_hostname2
	source_idcs_url=$source_idcs_url2
	source_scope=$source_scope2
	source_AuthBase=$source_AuthBase2
	JAVA_HOME=$JAVA_HOME2
	dataMigrationHome=$dataMigrationHome2
	SOURCE_ENVIRONMENT=$SOURCE_ENVIRONMENT2
	SOURCE_URL=$SOURCE_URL2
	SOURCE_USERNAME=$SOURCE_USERNAME2
	DATA_FRAGMENTS_DIRECTORY=$DATA_FRAGMENTS_DIRECTORY2
	MAX_DATA_FRAGMENT_SIZE_IN_MB=$MAX_DATA_FRAGMENT_SIZE_IN_MB2
	SOURCE_PASSWORD=$SOURCE_PASSWORD2
	ENCRYPTION_PASSWORD=$ENCRYPTION_PASSWORD2
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

#---------------------------------------SNAPSHOT SCRIPT---------------------------------------#

workDir=$PWD/tmp

createTmpDir()
{
 if [ ! -d "$workDir" ]
  then
  mkdir $workDir
 fi 
}

getFileName()
{
 if [ -f $workDir/fileName.txt ]
  then
  cp $workDir/fileName.txt $workDir/fileNameOld.txt
 fi 
 date +%Y%m%d_%H%M >$workDir/fileName.txt
 fileName=$(cat $workDir/fileName.txt)

}


getKeyWrapped()
{
 if [ ! -f $oci_privateKey ]
  then
  echo "exiting need private Key"
  exit
 fi

 cat $oci_privateKey|base64 -w 0 > $workDir/sourceKeyWrapped.txt
 keyWrapped=$(cat $workDir/sourceKeyWrapped.txt)
}

getRefreshToken()
{
 $PWD/getSourceRefreshToken.sh $regioncode	 
 refreshToken=$(cat source_refreshToken.txt)
}


isSnapshotRequestAccepted()
{
 if grep -q 'workRequestId' _snapshot.tmp; then
  checkSuccess
 else
  echo "Exit - Snapshot Request wasn't accepted."
  exit
 fi

}

#start of CreateSnapShotFunction. 
createSnapShot()
{

echo '{
    "type": "CREATE",
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
            "ociPrivateKeyWrapped": "'$keyWrapped'"
        }
    },
    "bar": {
        "uri": "file:///'$fileName'.bar",
        "password": "'$ENCRYPTION_PASSWORD'"
    }
}' > createSnapshot.json


#Check If file Exist before creating with same name.

isFileExist


### curl for creating Snap

accessToken=$(cat $workDir/source_accessToken.txt)

curl --silent -i --header "Authorization: Bearer $accessToken" --header "Content-Type: application/json" --request POST https://$source_hostname/api/20210901/snapshots -d @createSnapshot.json > _snapshot.tmp

isSnapshotRequestAccepted

rm -rf createSnapshot.json

}
#---- END

checkSuccess()
{
 echo "checking if the file is created successfully"
 touch bucketFiles.json
 oci os object list -ns $namespace -bn $bucket --config-file oci_config > bucketFiles.json
 jq .data[].name bucketFiles.json |sed -rn 's/(")([^"]+)(.*)/\2/p' > fileStatus.tmp
 barfilecheck=$filename.bar
 if grep -q "$barfilecheck" "fileStatus.tmp"; then
         echo "BAR FILE EXISTS IN THE BUCKET AND IS READY TO BE DOWNLOADED"
 else
         sleep 30
         checkSuccess
 fi
}


deleteLocalFile()
{
 
 newfileName=$(cat $workDir/fileName.txt)
 newbarFile=$newfileName.bar
 newdataFile=$newfileName.zip

 oldfileName=$(cat $workDir/fileNameOld.txt)
 oldbarFile=$oldfileName.bar
 olddataFile=$oldfileName.zip
 
 if [ -f $newbarFile ]
  then
  if [ -f $oldbarFile ]
   then
   echo "removing older bar file -- " $oldfileName
   rm $oldbarFile
  fi
 fi

 if [ -f $newdataFile ]
  then
  if [ -f $olddataFile ]
   then
   echo "removing older data file -- " $oldfileName
   sleep 10
   rm $olddataFile
  fi
 fi

 rm -rf $fileName
}

isFileExist()
{
 touch checkFiles.json
 oci os object list -ns $namespace -bn $bucket --config-file oci_config > checkFiles.json
 jq .data[].name checkFiles.json |sed -rn 's/(")([^"]+)(.*)/\2/p' > filecheck.tmp
 if grep -q "$fileName.bar" "filecheck.tmp"; then
	 echo $fileName".bar already exist -"
	 echo "Deleting "$fileName".bar IN PROGRESS"
	 sleep 10
 else
	 echo "NEW BAR FILE DOESNT EXIST IN THE BUCKET"
	 echo "ready to create a new snapshot"
 fi
}


#RefreshToken Function

getRefreshAccessToken()
{
#This function will get a new RefreshToken - for next Run
# and get Access Token.


getRefreshToken

echo "curl --location --request POST '"$source_idcs_url"/oauth2/v1/token' \\
--header 'Authorization: Basic "$source_AuthBase"' \
--header 'Content-Type: application/x-www-form-urlencoded' \\
--data-urlencode 'grant_type=refresh_token' \\
--data-urlencode 'refresh_token="$refreshToken"' \\
--data-urlencode 'source_scope="$source_scope"'
" > curlToken.sh

chmod -fR 777 curlToken.sh
./curlToken.sh > $workDir/_sourceToken.tmp

cat $workDir/_sourceToken.tmp |sed 's/^.*refresh_token":"//' | sed 's/"}//' |awk '{print $0}'> source_refreshToken.txt
cat $workDir/_sourceToken.tmp |sed 's/","token_type.*//'|sed 's/^.*":"//' |awk '{print $0}'> $workDir/source_accessToken.txt
rm -rf curlToken.sh
}

downloadBarFile()
{
 barFile=$fileName.bar
 echo "DOWNLOADING THE BAR FILE FROM THE OBJECT STORAGE- - - - - - - - - - - - - - - - - - - - "$barFile
 oci os object get -ns $namespace -bn $bucket --name $barFile --file $barFile --config-file oci_config
}


createDownloadConfig()
{

echo '# Download Data Files: 
[DownloadDataFiles]
SOURCE_ENVIRONMENT='$SOURCE_ENVIRONMENT'
SOURCE_URL='$SOURCE_URL'
SOURCE_USERNAME='$SOURCE_USERNAME'
SOURCE_PASSWORD='$SOURCE_PASSWORD'
BAR_PATH='$fileName'.bar
ENCRYPTION_PASSWORD='$ENCRYPTION_PASSWORD'
DATA_FRAGMENTS_DIRECTORY='$fileName'
MAX_DATA_FRAGMENT_SIZE_IN_MB='$MAX_DATA_FRAGMENT_SIZE_IN_MB  >$workDir/downloadData.prop
}

downloadDataFile()
{
mkdir $fileName
echo "Downloading the data files using the snapshot file $fileName.bar"
$JAVA_HOME/bin/java -jar $dataMigrationHome/migrate-oac-data.jar -d -config $workDir/downloadData.prop > $workDir/dataOutput.txt
}

uploadDataToSource()
{
 dataFile=$fileName.zip
 echo "uploading the "$dataFile "file to the object storage"
 oci os object put -ns $namespace -bn $bucket --name $dataFile --file $dataFile --config-file oci_config --no-overwrite --storage-tier Standard 
}

zipDataFile()
{
zip -r $fileName.zip $fileName
}

cleanUP()
{
rm -f fileStatus.tmp
rm -f downloadData.prop
rm -f _snapshot.tmp
rm -f oci_config
rm -f bucketFiles.json
rm -f fileStatus.tmp
rm -f checkFiles.json
rm -f filecheck.tmp
rm -rf tmp
rm -f $fileName.bar
rm -f $fileName.zip
rm -f source_refreshToken.txt 
}

#------ Calling Function -----

createTmpDir
getKeyWrapped

#------

##### Getting AccessToken using Refresh Token ####

getRefreshAccessToken


#checkRefreshToken
##### CREATING BAR FILE ####

getFileName
createSnapShot
sleep 60
downloadBarFile
sleep 60

#last step is to increment the counter for next run. 

sleep 5
createDownloadConfig

sleep 5
downloadDataFile

zipDataFile

deleteLocalFile
uploadDataToSource
cleanUP

exit

