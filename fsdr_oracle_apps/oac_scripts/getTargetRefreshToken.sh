#!/bin/bash
#====================================================
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# This script generates the Refresh token for oac-register-snapshot.sh consumption, No need to call explicitly.
#
#====================================================

#################################################---OCI REGION 1---################################################################

#Enter the OCI Region Code. For example, IAD for us-ashburn-1 and PHX for us-phoenix-1 regions.
region1=IAD

IDCS_URL1=https://idcs-xxxxxxxxx.identity.oraclecloud.com
Client_ID1=xxxxxxxxx
Client_Secret1=xxxxxxxxx

# Enter the Region1 Scope of the Confidential Application
# Example: https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.analytics.ocp.oraclecloud.comurn:opc:resource:consumer::all
ConfAppScope1=https://xxxxxxxxx.analytics.ocp.oraclecloud.comurn:opc:resource:consumer::all

# Enter the Region1 OAC Instance URL till oraclecloud.com
# Example: https://xxxxxx-xxxxxxxxxxx-xx.analytics.ocp.oraclecloud.com
OACURL1=https://oacprimaryash-xxxxxxxxx-ia.analytics.ocp.oraclecloud.com

# Prompt the user to enter UserName and Password for input.
#read -p "Please enter UserName: " OAPUserName
#read -s -p "Please enter Password: " OAPPassword
OACUserName1=xxxxxxxxx
OACPassword1=xxxxxxxxx

###################################################################################################################################

#################################################---OCI REGION 2---################################################################

#Enter the OCI Region Code. For example, IAD for us-ashburn-1 and PHX for us-phoenix-1 regions.
region2=PHX

IDCS_URL2=https://idcs-xxxxxxxxx.identity.oraclecloud.com
Client_ID2=xxxxxxxxx
Client_Secret2=xxxxxxxxx

# Enter Scope of the Confidential Application
# Example: https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.analytics.ocp.oraclecloud.comurn:opc:resource:consumer::all
ConfAppScope2=https://xxxxxxxxx.analytics.ocp.oraclecloud.comurn:opc:resource:consumer::all

# Enter the OAP Instance URL till oraclecloud.com
# Example: https://xxxxxx-xxxxxxxxxxx-xx.analytics.ocp.oraclecloud.com
OACURL2=https://oacsecondaryphx-xxxxxxxxx-px.analytics.ocp.oraclecloud.com

# Prompt the user to enter UserName and Password for input.
#read -p "Please enter UserName: " OAPUserName
#read -s -p "Please enter Password: " OAPPassword
OACUserName2=xxxxxxxxx
OACPassword2=xxxxxxxxx

###################################################################################################################################

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
	IDCS_URL=$IDCS_URL1
	Client_ID=$Client_ID1
	Client_Secret=$Client_Secret1
	ConfAppScope=$ConfAppScope1
	OACURL=$OACURL1
	OACUserName=$OACUserName1
	OACPassword=$OACPassword1
elif [ "$region2" == "$regioncode" ]; then
	IDCS_URL=$IDCS_URL2
        Client_ID=$Client_ID2
        Client_Secret=$Client_Secret2
        ConfAppScope=$ConfAppScope2
        OACURL=$OACURL2
	OACUserName=$OACUserName2
	OACPassword=$OACPassword2
else
        echo "Valid oci region code is not provided. Exiting......."
        exit
fi

#---------------------------------------------------------------------------------------------#

getRefreshToken()
{
AuthToken=`echo -n "$Client_ID:$Client_Secret" | base64 -w 0`

export TOKENS=`curl --request POST "${IDCS_URL}/oauth2/v1/token" --header "Authorization: Basic ${AuthToken} " --header 'Content-Type: application/x-www-form-urlencoded' --data-urlencode 'grant_type=password' --data-urlencode "username=${OACUserName}" --data-urlencode "password=${OACPassword}" --data-urlencode "scope=${ConfAppScope} offline_access"`

echo ""
echo $TOKENS
echo ""

if echo "$TOKENS" | grep -q "You entered an incorrect user name or password.";
then
 echo "Exiting Script - You entered an incorrect user name or password."
 echo "Run the Script with correct UserName and Password."
 exit
elif echo "$TOKENS" | grep -q "Invalid grant type.";
then
 echo "Ensure Resource Owner and Refresh Token grant types are selected for the Confidential Application."
 echo "Run the Script after selecting the required Grant Types for the Confidential Application."
 exit
else
 echo $TOKENS | sed 's/^.*refresh_token":"//' | sed 's/"}//' |awk '{print $0}' > $PWD/targetRefreshToken.txt
 echo $TOKENS | awk -F'"access_token":"|","token_type"' '{print $2}' > $PWD/targetAccessToken.txt
 echo "New Refresh Token saved to the targetRefreshToken.txt and targetAccessToken.txt files is as below:"
 echo $(cat $PWD/targetRefreshToken.txt)
 echo ""
 echo $(cat $PWD/targetAccessToken.txt)
fi
}

#Call Function
getRefreshToken
