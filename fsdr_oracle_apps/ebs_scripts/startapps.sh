#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
. /u01/install/APPS/EBSapps.env run
{ echo apps; echo $1; echo $2; } | sh $ADMIN_SCRIPTS_HOME/adstrtal.sh -nopromptmsg
