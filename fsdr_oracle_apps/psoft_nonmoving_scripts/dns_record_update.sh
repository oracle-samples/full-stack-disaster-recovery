#!/bin/bash
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
oci dns record rrset update --config-file /u01/app/psoft/fscm92-dbaas-vinay-app/home/psadm2/.oci/config --zone-name-or-id "psftchatbot.tk" --domain "fscm92.psftchatbot.tk" --rtype "A" --items '[{"domain":"fscm92.psftchatbot.tk","rdata":"129.158.218.175","rtype":"A","ttl":60}]' --force