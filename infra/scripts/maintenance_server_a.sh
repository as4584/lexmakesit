#!/bin/bash
# ============================================================
# Server A (174.138.67.169) Maintenance Script
# Handles: zombie processes, Docker container health, disk cleanup
# ============================================================
set -euo pipefail

LOG_FILE="/var/log/ai_receptionist_maintenance.log"
COMPOSE_DIR="/opt/ai-receptionist"
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
#    Zombies can't be killed directly — send SIGCHLD to parent
#    so it reaps them. If parent is stuck, kill it.
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
        # Check if any remain after SIGCHLD
        local remaining
        remaining=$(ps aux | awk '$8=="Z"' | wc -l)
        if [ "$remaining" -gt 0 ]; then
            log "ZOMBIES: $remaining zombie(s) remain after SIGCHLD — may require container restart"
        else
            log "ZOMBIES: all zombies reaped"
        fi
    fi
}

# ----------------------------------------------------------
# 2. Ensure Docker Compose services are running
#    Uses `docker compose up -d` which is idempotent —
#    only starts stopped containers, ignores healthy ones.
# ----------------------------------------------------------
ensure_containers_running() {
    cd "$COMPOSE_DIR"

    # Backend
    if [ -f "docker-compose.yml" ]; then
        local exited_count
        exited_count=$(docker compose -f docker-compose.yml ps --status exited --quiet 2>/dev/null | wc -l)
        if [ "$exited_count" -gt 0 ]; then
            log "DOCKER: $exited_count backend container(s) exited — restarting"
            docker compose -f docker-compose.yml up -d 2>&1 | tail -5 | while read -r line; do log "  $line"; done
        fi
    fi

    # Dashboard frontend
    if [ -d "$COMPOSE_DIR/frontend" ] && [ -f "$COMPOSE_DIR/frontend/docker-compose.prod.yml" ]; then
        local dash_exited
        dash_exited=$(docker compose -f "$COMPOSE_DIR/frontend/docker-compose.prod.yml" ps --status exited --quiet 2>/dev/null | wc -l)
        if [ "$dash_exited" -gt 0 ]; then
            log "DOCKER: dashboard container exited — restarting"
            cd "$COMPOSE_DIR/frontend"
            docker compose -f docker-compose.prod.yml up -d 2>&1 | tail -3 | while read -r line; do log "  $line"; done
            cd "$COMPOSE_DIR"
        fi
    fi

    # Auth frontend
    if [ -d "$COMPOSE_DIR/auth-frontend" ] && [ -f "$COMPOSE_DIR/auth-frontend/docker-compose.prod.yml" ]; then
        local auth_exited
        auth_exited=$(docker compose -f "$COMPOSE_DIR/auth-frontend/docker-compose.prod.yml" ps --status exited --quiet 2>/dev/null | wc -l)
        if [ "$auth_exited" -gt 0 ]; then
            log "DOCKER: auth container exited — restarting"
            cd "$COMPOSE_DIR/auth-frontend"
            docker compose -f docker-compose.prod.yml up -d 2>&1 | tail -3 | while read -r line; do log "  $line"; done
            cd "$COMPOSE_DIR"
        fi
    fi
}

# ----------------------------------------------------------
# 3. Docker disk cleanup (only when disk > 80%)
#    Removes dangling images and stopped containers
#    that are older than 24h. Never removes named volumes.
# ----------------------------------------------------------
docker_prune_if_needed() {
    local disk_pct
    disk_pct=$(df / | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
    if [ "$disk_pct" -gt 80 ]; then
        log "DISK: usage ${disk_pct}% — running docker prune (images older than 24h)"
        docker image prune -f --filter "until=24h" 2>&1 | while read -r line; do log "  $line"; done
        docker container prune -f --filter "until=24h" 2>&1 | while read -r line; do log "  $line"; done
    fi
}

# ----------------------------------------------------------
# 4. Unattended security updates (runs only on Sunday at 3am
#    when called from that cron slot; harmless otherwise)
# ----------------------------------------------------------
security_updates() {
    if command -v unattended-upgrade &>/dev/null; then
        log "UPDATES: running unattended security upgrades"
        unattended-upgrade -d 2>&1 | tail -5 | while read -r line; do log "  $line"; done
    fi
}

# ----------------------------------------------------------
# Main
# ----------------------------------------------------------
rotate_log
log "=== Maintenance start ==="
kill_zombies
ensure_containers_running
docker_prune_if_needed
# security_updates is called directly from its own cron entry
log "=== Maintenance done ==="
