#!/bin/bash
# ============================================================
# Server B (104.236.100.245) Maintenance Script
# Handles: zombie processes, Caddy health check,
#          disk cleanup, unattended security updates
# ============================================================
set -euo pipefail

LOG_FILE="/home/lex/logs/maintenance.log"
mkdir -p /home/lex/logs
CADDYFILE="/home/lex/antigravity_bundle/apps/Caddyfile"
CADDY_CONTAINER="antigravity_caddy"
MAX_LOG_LINES=1000

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

rotate_log() {
    if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt "$MAX_LOG_LINES" ]; then
        tail -n "$MAX_LOG_LINES" "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    fi
}

# ----------------------------------------------------------
# 1. Kill zombie processes
# ----------------------------------------------------------
kill_zombies() {
    local zombies
    zombies=$(ps aux | awk '$8=="Z"' | wc -l)
    if [ "$zombies" -gt 0 ]; then
        log "ZOMBIES: found $zombies zombie process(es), signalling parents"
        ps aux | awk '$8=="Z" {print $3}' | sort -u | while read -r ppid; do
            if [ "$ppid" -gt 1 ] 2>/dev/null; then
                kill -SIGCHLD "$ppid" 2>/dev/null || true
            fi
        done
        sleep 2
        local remaining
        remaining=$(ps aux | awk '$8=="Z"' | wc -l)
        if [ "$remaining" -gt 0 ]; then
            log "ZOMBIES: $remaining remain after SIGCHLD — may need manual investigation"
        else
            log "ZOMBIES: all reaped"
        fi
    fi
}

# ----------------------------------------------------------
# 2. Ensure Caddy is running and config is valid
# ----------------------------------------------------------
ensure_caddy_running() {
    # Caddy runs as a Docker container on this server
    local caddy_status
    caddy_status=$(docker inspect --format '{{.State.Status}}' "$CADDY_CONTAINER" 2>/dev/null || echo "missing")

    if [ "$caddy_status" != "running" ]; then
        log "CADDY: container '$CADDY_CONTAINER' is '$caddy_status' — restarting"
        docker start "$CADDY_CONTAINER" 2>&1 | while read -r line; do log "  $line"; done
    else
        log "CADDY: container running ok"
    fi
}

# ----------------------------------------------------------
# 3. Disk cleanup for non-Docker server
# ----------------------------------------------------------
disk_cleanup_if_needed() {
    local disk_pct
    disk_pct=$(df / | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
    if [ "$disk_pct" -gt 80 ]; then
        log "DISK: usage ${disk_pct}% — pruning Docker"
        docker system prune -f --filter "until=24h" 2>&1 | tail -3 | while read -r line; do log "  $line"; done
        docker image prune -f --filter "until=72h" 2>&1 | tail -2 | while read -r line; do log "  $line"; done
        disk_pct=$(df / | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
        log "DISK: usage now ${disk_pct}% after prune"
    else
        log "DISK: usage ${disk_pct}% ok"
    fi
}

# ----------------------------------------------------------
# 4. Unattended security updates
# ----------------------------------------------------------
security_updates() {
    # Requires sudo — add to root crontab instead: 0 3 * * 0 /usr/bin/unattended-upgrade -d
    log "UPDATES: skipped (requires root — see root crontab)"
}

# ----------------------------------------------------------
# Main
# ----------------------------------------------------------
rotate_log
log "=== Maintenance start ==="
kill_zombies
ensure_caddy_running
disk_cleanup_if_needed
# security_updates called from its own Sunday cron entry
log "=== Maintenance done ==="
