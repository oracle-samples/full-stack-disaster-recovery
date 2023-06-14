#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
. /u01/install/APPS/EBSapps.env run
{ echo $1; } | sh $ADMIN_SCRIPTS_HOME/adautocfg.sh
