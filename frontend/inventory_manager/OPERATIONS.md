# Operations Manual - Inventory Manager

## Service Overview
- **URL**: https://inventory.lexmakesit.com
- **Internal DNS**: `inventory.internal`
- **Port**: 8010 (Internal Only)
- **Framework**: Flask

## Common Tasks

### Restart Service
```bash
cd /srv/inventory_manager
docker compose -p inventory_manager-green restart app
```

### View Logs
**Via CLI**:
```bash
docker logs -f inventory_manager-green-app-1
```

**Via Grafana**:
Query: `{container="inventory_manager-green-app-1"}`

## Environment Variables
Located at: `/srv/env/inventory_manager/.env`
**Permissions**: `600` (root:root)

To update:
1.  Edit file: `sudo nano /srv/env/inventory_manager/.env`
2.  Restart service.
