Rem
Rem Copyright (c) 2023, Oracle and/or its affiliates.
Rem Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
Rem
@ECHO OFF
SET TUXDIR=D:\psft\pt\bea\tuxedo\tuxedo12.2.2.0.0_VS2017
SET PS_HOME=D:\psft\pt\ps_home
SET PS_CFG_HOME=D:\psft\hcm92-fsdr-prcs\ps_cfg_home
d:
cd D:\psft\pt\ps_home\appserv
D:\psft\pt\ps_home\appserv\psadmin.exe -p stop -d PRCSDOM01
