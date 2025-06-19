# README

## Web Application

The web application shows a simple **"Vehicle Monitoring Report"** which lists vehicles and their telemetry. The primary goal of this application is to demonstrate a Disaster Recovery scenario where the application remains functional in the new region after failover without user intervention.

The web application itself consists of a **React** frontend which displays the report and connects to the **GO** backend which is exposed as an API, the backend itself connects to an **OCI Database with PostgreSQL** as well as OCI services such as **OCI Vault**. To guarantee the application remains functional after switchvover a primary and a secondary region is configured, when the application is started the current region is determined using [instance principals](https://github.com/oracle/oci-go-sdk/blob/master/example/example_instance_principals_test.go).

Further the web application is served via a Load Balancer (LB) that exposes the API and the Frontend visible to the user. 

### Networking

With default setup being used the LB listens on port **80** and **8000** for the **frontend** and **webapp_url**(the API or backend) respectively, the **frontend** and the **backend** is exposed on port **3000** and **8585**.

### FSDR_WebApp.zip Contents

- **frontend** - This is where the react frontend lives. (Do not modify)
- **backend** - This is where the GO API backend lives. (Do not modify)
- **frontend.service** (Do not modify)
- **backend.service** (Do not modify)

### deploy_application_demo.sh

This contains all the configuration required

- **WEBAPP_HOME** - Root location of the deployment (Location where you execute the script from i.e /home/opc)
- **GO_API_ZIP** - Zip file to be unzipped by the script (Default: FSDR_WebApp.zip)
- **GO_API_PORT** - Listener for GO API (Default:8585)
- **FRONTEND_PORT** - Listener for Frontend (Default:3000)
- **WEBAPP_URL** - The URL pointing to the compute with the API - "http://webapi.yoururl.eu:8000"
- **PRIMARY_REGION** - OCI Primary Region (Format: eu-frankfurt-1)
- **STANDBY_REGION** - OCI Standby Region
- **PRIMARY_SECRET_OCID** - The vault secret with the PostgreSQL password in Primary Region ("ocid1.vaultsecret.oc1.eu-frankfurt-1.xxxxxx")
- **STANDBY_SECRET_OCID** - The vault secret with the PostgreSQL password in Primary Region ("ocid1.vaultsecret.oc1.eu-frankfurt-1.xxxxxx")
- **PG_USER** - The Database user you will use.
- **PG_DB** - The Database you will use. (Default: postgres)
- **PG_HOST** - The FQDN of the Private Zone of the Database.

### postgresql_sample.sql

For the sample application to work the **postgresql_sample.sql** script needs to be executed inside the database.
It will create:

1. The schema "iot"
2. The table "cars"
3. Populate the cars table with entries.

### Steps

1. Copy "FSDR_WebApp.zip" and "deploy_application_demo.sh" to the target compute.
2. Execute "chmod +x deploy_application_demo.sh"
3. Execute the script "./deploy_application_demo.sh"
