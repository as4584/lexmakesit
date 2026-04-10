# Server Hardening Guide

## 1. SSH Hardening
Edit `/etc/ssh/sshd_config`:

```bash
# Disable root login
PermitRootLogin no

# Disable password authentication
PasswordAuthentication no
ChallengeResponseAuthentication no

# Use SSH keys only
PubkeyAuthentication yes
```

Restart SSH: `sudo systemctl restart sshd`

## 2. Firewall (UFW)
Enforce default deny policy:

```bash
# Reset to default
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow essential ports
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Enable firewall
sudo ufw enable
```

## 3. Fail2Ban
Install and configure:

```bash
sudo apt install fail2ban
sudo cp security/fail2ban.conf /etc/fail2ban/jail.d/custom.conf
sudo systemctl restart fail2ban
```

## 4. Automatic Updates
Enable unattended upgrades:

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

## 5. Verification Checklist
Run these commands on production hosts to confirm controls are active:

```bash
# SSH is key-only and root login disabled
sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|pubkeyauthentication'

# UFW is active and default deny incoming
sudo ufw status verbose

# Fail2Ban service and jails are active
sudo systemctl is-active fail2ban
sudo fail2ban-client status

# Containers are running non-root users
docker inspect ai-receptionist-app-1 --format '{{.Config.User}}'
docker inspect portfolio-web-1 --format '{{.Config.User}}'

# Redis is not publicly exposed (prod) and requires auth
docker compose -f /opt/ai-receptionist/backend/docker-compose.prod.yml ps
docker exec $(docker ps --filter name=redis -q | head -n1) redis-cli ping
docker exec $(docker ps --filter name=redis -q | head -n1) redis-cli -a "$REDIS_PASSWORD" ping

# Auth refresh/logout endpoints reachable (expect 401 without token)
curl -i https://api.lexmakesit.com/api/auth/refresh
curl -i https://api.lexmakesit.com/api/auth/logout
```
