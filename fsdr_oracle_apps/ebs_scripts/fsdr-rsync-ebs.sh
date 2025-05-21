#!/usr/bin/env bash
#
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
#
#
# Enhanced EBS rsync cron management for Full Stack DR
# Version: 2.0
# Last Modified: $(date +%Y-%m-%d)
#
# Features:
# - Atomic crontab updates with backup
# - Detailed logging
# - Dry-run mode
# - Pre/post validation
# - Locking mechanism
# - Email notifications

# Configuration
LOCK_FILE="/tmp/fsdr_rsync_cron.lock"
LOG_FILE="/var/log/fsdr_rsync_cron.log"
BACKUP_DIR="/var/backups/crontabs"
ADMIN_EMAIL="admin@yourdomain.com"
TEMP_CRON="/tmp/crontab_${USER}_$(date +%s).tmp"

# Initialize logging
exec > >(tee -a "$LOG_FILE") 2>&1

# Error handling
trap 'cleanup; error_handler' EXIT ERR SIGINT SIGTERM

function cleanup() {
    [ -f "$TEMP_CRON" ] && rm -f "$TEMP_CRON"
    [ -f "$LOCK_FILE" ] && rm -f "$LOCK_FILE"
}

function error_handler() {
    local exit_code=$?
    echo "[ERROR] $(date '+%Y-%m-%d %T') - Script failed with exit code $exit_code"
    send_notification "FAILURE: EBS Rsync Cron Management Failed"
    exit $exit_code
}

function send_notification() {
    local subject="$1"
    echo "$subject" | mailx -s "$subject" "$ADMIN_EMAIL"
}

function validate_environment() {
    # Check required commands
    for cmd in crontab mailx sed grep; do
        if ! command -v $cmd &> /dev/null; then
            echo "[ERROR] Required command '$cmd' not found"
            exit 1
        fi
    done

    # Check backup directory
    mkdir -p "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"
}

function backup_crontab() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    crontab -l > "${BACKUP_DIR}/crontab_${USER}_${timestamp}.bak"
    echo "[INFO] Crontab backed up to ${BACKUP_DIR}/crontab_${USER}_${timestamp}.bak"
}

function verify_changes() {
    local task=$1
    local ip=$2
    local count
    
    case $task in
        disable)
            count=$(crontab -l | grep -v '^#' | grep -c "$ip")
            if [ "$count" -ne 0 ]; then
                echo "[ERROR] Some jobs for $ip were not disabled"
                return 1
            fi
            ;;
        enable)
            count=$(crontab -l | grep '^#FSDR' | grep -c "$ip")
            if [ "$count" -ne 0 ]; then
                echo "[ERROR] Some jobs for $ip were not enabled"
                return 1
            fi
            ;;
    esac
    return 0
}

function manage_cron() {
    local task=$1
    local ip=$2
    local dry_run=${3:-false}
    local changes_made=false

    echo "[INFO] Starting $task operation for IP: $ip"
    echo "Current crontab:"
    crontab -l
    
    # Create temp crontab
    crontab -l > "$TEMP_CRON"

    case $task in
        disable)
            if grep -v '^#' "$TEMP_CRON" | grep -q "$ip"; then
                if $dry_run; then
                    echo "[DRY RUN] Would disable jobs for $ip"
                else
                    sed -i "/$ip/s/^/#FSDR /" "$TEMP_CRON"
                    changes_made=true
                fi
            else
                echo "[INFO] No active jobs found for $ip - nothing to disable"
            fi
            ;;
        enable)
            if grep '^#FSDR' "$TEMP_CRON" | grep -q "$ip"; then
                if $dry_run; then
                    echo "[DRY RUN] Would enable jobs for $ip"
                else
                    sed -i "/^#FSDR .*$ip/s/^#FSDR //" "$TEMP_CRON"
                    changes_made=true
                fi
            else
                echo "[INFO] No disabled jobs found for $ip - nothing to enable"
            fi
            ;;
    esac

    if $changes_made && ! $dry_run; then
        backup_crontab
        crontab "$TEMP_CRON"
        echo "Updated crontab:"
        crontab -l
        
        if verify_changes "$task" "$ip"; then
            echo "[SUCCESS] Crontab updated successfully"
            send_notification "SUCCESS: EBS Rsync Cron $task completed for $ip"
        else
            echo "[ERROR] Verification of changes failed"
            exit 1
        fi
    fi
}

# Main execution
function main() {
    # Check for lock file
    if [ -f "$LOCK_FILE" ]; then
        echo "[ERROR] Script is already running (lock file exists)"
        exit 1
    fi
    touch "$LOCK_FILE"

    # Validate arguments
    if [[ $# -lt 2 ]]; then
        echo "Usage: $0 <disable|enable|dry-run> <EBS_IP>"
        echo "Example: $0 disable 10.10.10.100"
        exit 1
    fi

    local task=$1
    local ip=$2
    local dry_run=false

    # Validate task
    case $task in
        disable|enable)
            ;;
        dry-run)
            dry_run=true
            ;;
        *)
            echo "[ERROR] Invalid task: $task. Use 'disable', 'enable', or 'dry-run'"
            exit 1
            ;;
    esac

    # Validate IP format
    if ! [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "[ERROR] Invalid IP address format: $ip"
        exit 1
    fi

    validate_environment
    manage_cron "$task" "$ip" "$dry_run"
}

main "$@"
cleanup
exit 0