#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
export SECRET_APPS_OCID=$1
export SECRET_APPS=$(oci secrets secret-bundle get --raw-output --secret-id $SECRET_APPS_OCID --query "data.\"secret-bundle-content\".content" | base64 -d)
echo $SECRET_APPS
export SECRET_WEBLOGIC_OCID=$2
export SECRET_WEBLOGIC=$(oci secrets secret-bundle get --raw-output --secret-id $SECRET_WEBLOGIC_OCID --query "data.\"secret-bundle-content\".content" | base64 -d)
echo $SECRET_WEBLOGIC
. /u01/install/APPS/EBSapps.env run
{ echo apps; echo $SECRET_APPS; echo $SECRET_WEBLOGIC; } | sh $ADMIN_SCRIPTS_HOME/adstpall.sh -nopromptmsg
sleep 10
#export APPLICATION_USER=`whoami`
#kill -9 `ps -ef|grep oracle|grep -v grep |grep -v bash|grep -v sshd |grep -v "ps -ef"| grep -v shutdownapps | awk '{print $2}'`
