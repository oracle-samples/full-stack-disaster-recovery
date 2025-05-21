#!/usr/bin/expect -f
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
spawn ssh -i private.key opc@xxxxxx
expect "$"
send "date\n"
expect "$"
send "sudo su - oracle\n"
expect "$"
send "dgmgrl sys/xxxxxxx\n"
expect "> "
send "show configuration \n"
expect "DGMGRL> "
send "switchover to ebsss_iii \n"
sleep 180
expect "DGMGRL> "
send "quit\n"
expect "$"
send "exit\n"
