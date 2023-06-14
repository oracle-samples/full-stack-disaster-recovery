#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
. /u01/install/APPS/EBSapps.env run
{ echo apps; echo $1; echo $2; } | sh $ADMIN_SCRIPTS_HOME/adstpall.sh -nopromptmsg
sleep 10
#export APPLICATION_USER=`whoami`
#kill -9 `ps -ef|grep oracle|grep -v grep |grep -v bash|grep -v sshd |grep -v "ps -ef"| grep -v shutdownapps | awk '{print $2}'`
