export SECRET_APPS_OCID=$1
export SECRET_APPS=$(oci secrets secret-bundle get --raw-output --secret-id $SECRET_APPS_OCID --query "data.\"secret-bundle-content\".content" | base64 -d)
echo $SECRET_APPS
. /u01/install/APPS/EBSapps.env run
{ echo $SECRET_APPS; } | sh $ADMIN_SCRIPTS_HOME/adautocfg.sh
