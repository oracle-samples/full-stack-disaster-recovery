REM
REM Copyright (c) 2024, Oracle and/or its affiliates.
REM Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
REM

REM Run this script after moving the compute instance from primary to the standby region.

@echo off
mount -o sec=sys 10.0.1.6:/epmsystem E:
