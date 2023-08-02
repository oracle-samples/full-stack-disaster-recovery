#!/bin/bash
#
# Copyright (c) 2023, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
 PID=`ps -eaf | grep "elas" | awk '{print $2}'`
    echo "$PID"
    if [[ -z "$PID" ]];
     then(
            echo "Elastic Search is not running!"
    )else(
            kill -9 $PID
    )fi
