#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# Stop OHS
cd $MIDDLEWARE_HOME/user_projects/epmsystem1/httpConfig/ohs/bin
./stopComponent.sh ohs_component

# Delay after stopping OHS
sleep 20

# Stop Node Manager
cd $MIDDLEWARE_HOME/user_projects/epmsystem1/httpConfig/ohs/bin
./stopNodemanager.sh

# Delay after stopping Node Manager
sleep 20

# Stop Managed Servers in EPMSystem1
cd $MIDDLEWARE_HOME/user_projects/epmsystem1/bin/
./stop.sh

# Delay after stopping Managed Servers
sleep 120

# Stop WebLogic Server
cd $MIDDLEWARE_HOME/user_projects/domains/EPMSystem/bin
./stopWeblogic.sh

# Delay after stopping Managed Servers
sleep 60
