#ps1
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# Stop OHS
cd C:\Oracle\Middleware\user_projects\epmsystem1\httpConfig\ohs\bin
Start-Process -FilePath ".\stopComponent.cmd" -ArgumentList "ohs_component"

# Delay
Start-Sleep -Seconds 30

# Stop Node Manager
cd C:\Oracle\Middleware\user_projects\epmsystem1\httpConfig\ohs\bin
Start-Process -FilePath ".\stopNodemanager.cmd"

# Delay
Start-Sleep -Seconds 30

# Stop Managed Servers in EPMSystem1
cd C:\Oracle\Middleware\user_projects\epmsystem1\bin\
Start-Process -FilePath ".\stop.bat"

# Delay
Start-Sleep -Seconds 120

# Stop WebLogic Server
cd C:\Oracle\Middleware\user_projects\domains\EPMSystem\bin
Start-Process -FilePath ".\stopWeblogic.cmd"

# Delay
Start-Sleep -Seconds 60
