#ps1
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
# Start WebLogic Server
cd C:\Oracle\Middleware\user_projects\domains\EPMSystem\bin
Start-Process -FilePath ".\startWeblogic.cmd"

# Delay for WebLogic to fully start
Start-Sleep -Seconds 300

# Start Managed Servers in EPMSystem1
cd C:\Oracle\Middleware\user_projects\epmsystem1\bin\
Start-Process -FilePath ".\start.bat"

# Delay after starting Managed Servers
Start-Sleep -Seconds 30

# Start Node Manager
cd C:\Oracle\Middleware\user_projects\epmsystem1\httpConfig\ohs\bin
Start-Process -FilePath ".\startNodemanager.cmd"

# Delay after starting Node Manager
Start-Sleep -Seconds 30

# Start OHS
cd C:\Oracle\Middleware\user_projects\epmsystem1\httpConfig\ohs\bin
Start-Process -FilePath ".\startComponent.cmd" -ArgumentList "ohs_component"
