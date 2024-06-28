#!/bin/bash
#
# Copyright (c) 2024, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
#Run this script after moving the compute instance from standby to the primary region.

sudo mount -o nosuid,resvport,sec=sys 10.0.1.6:/epmsystem /u01/epmsystem
