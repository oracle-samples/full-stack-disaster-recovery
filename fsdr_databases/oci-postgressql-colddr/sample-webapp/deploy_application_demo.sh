#!/bin/bash

# Created by Piotr Kurzynoga @ Oracle Czech Republic
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v1.0 as shown at https://oss.oracle.com/licenses/upl.

# General Configuration
WEBAPP_HOME=/home/opc #Root location of the deployment
GO_API_ZIP="FSDR_WebApp.zip"
GO_API_PORT=8585
FRONTEND_PORT=3000
WEBAPP_URL="http://webapi.devwithphantom.eu:8000"

#Go PostgreSQL Configuration
PRIMARY_REGION="eu-frankfurt-1"
STANDBY_REGION="eu-amsterdam-1"
PRIMARY_SECRET_OCID="ocid1.vaultsecret.oc1.eu-frankfurt-1.xxxxxxxxxxx"
STANDBY_SECRET_OCID="ocid1.vaultsecret.oc1.eu-amsterdam-1.xxxxxxxxxxx"
PG_USER="phantompete"
PG_DB="postgres"
PG_HOST="postgre.pe.zone.yourprivate.zone"

# Helper function
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Install Go if not present
if command_exists go; then
  echo "Go is already installed."
else
  echo "Installing Go..."
  sudo yum install -y go
fi

# Install npm if not present
if command_exists npm; then
  echo "npm is already installed."
else
  echo "Installing Node.js and npm..."
  sudo yum install -y npm
fi

# Install serve if not present
if command_exists serve; then
  echo "serve is already installed globally."
else
  echo "Installing serve globally..."
  sudo npm install -g serve
fi

# Set up GO API
echo "Unzipping and starting GO API..."
unzip -o "$GO_API_ZIP" -d FSDR_WebApp
cd FSDR_WebApp || exit 1
cd backend || exit 1

# Update the OCI Secret, Region and OCI PostgreSQL Variables
sed -i "s|var primary_region = \".*\"|var primary_region = \"$PRIMARY_REGION\"|" main.go
sed -i "s|var standby_region = \".*\"|var standby_region = \"$STANDBY_REGION\"|" main.go
sed -i "s|var primary_secretOCID = \".*\"|var primary_secretOCID = \"$PRIMARY_SECRET_OCID\"|" main.go
sed -i "s|var standby_secretOCID = \".*\"|var standby_secretOCID = \"$STANDBY_SECRET_OCID\"|" main.go
sed -i "s|\"user\": *\"[^\"]*\"|\"user\":     \"$PG_USER\"|" main.go
sed -i "s|\"database\": *\"[^\"]*\"|\"database\": \"$PG_DB\"|" main.go
sed -i "s|\"host\": *\"[^\"]*\"|\"host\":     \"$PG_HOST\"|" main.go

echo "Resolving dependencies and building the application..."
go mod tidy
go build

# Configure the permissions for the application
sudo semanage fcontext -a -t bin_t "$WEBAPP_HOME/FSDR_WebApp/backend/go-fsdr-webapp"
sudo restorecon -v $WEBAPP_HOME/FSDR_WebApp/backend/go-fsdr-webapp

cd ..

# Configure the WebApp API URL
echo "{\"WEBAPP_URL\": \"$WEBAPP_URL\"}" > frontend/config.json

# Firewall rules
echo "Opening ports $FRONTEND_PORT and $GO_API_PORT in firewall..."
sudo firewall-cmd --permanent --zone=public --add-port=$FRONTEND_PORT/tcp
sudo firewall-cmd --permanent --zone=public --add-port=$GO_API_PORT/tcp
sudo systemctl restart firewalld

# Configure the environmental variable
echo "Configuring WEBAPP_HOME for services..."
sed -i "s|^WorkingDirectory=.*|WorkingDirectory=${WEBAPP_HOME}/FSDR_WebApp/frontend|" "frontend.service"
sed -i "s|^WorkingDirectory=.*|WorkingDirectory=${WEBAPP_HOME}/FSDR_WebApp/backend|" "backend.service"
sed -i "s|^ExecStart=.*|ExecStart=${WEBAPP_HOME}/FSDR_WebApp/backend/go-fsdr-webapp|" "backend.service"

# Move the service for future startups of the application
sudo mv frontend.service /etc/systemd/system/.
sudo mv backend.service /etc/systemd/system/.
sudo chown root:root /etc/systemd/system/frontend.service
sudo chown root:root /etc/systemd/system/backend.service
sudo restorecon -v /etc/systemd/system/frontend.service
sudo restorecon -v /etc/systemd/system/backend.service
sudo systemctl daemon-reload

# Start the services
echo "Starting frontend service..."
sudo systemctl start frontend.service
echo "Starting backend service..."
sudo systemctl start backend.service

# Persist service across restarts
echo "Services will be started automatically on boot"
sudo systemctl enable frontend.service
sudo systemctl enable backend.service

# Show the deployment info
echo "Deployment complete!"
echo "Frontend: http://$(hostname -I | awk '{print $1}'):$FRONTEND_PORT"
echo "Backend:  http://$(hostname -I | awk '{print $1}'):$GO_API_PORT"
