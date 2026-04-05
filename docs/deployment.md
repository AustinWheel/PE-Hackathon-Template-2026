# Deployment Guide

## Environments

| Environment | Platform | URL | Branch |
|---|---|---|---|
| Production | DO App Platform (2 instances) | https://pe-hackathon-hni9m.ondigitalocean.app | `main` |
| Staging | DO App Platform (1 instance) | https://pe-hackathon-staging-stj5i.ondigitalocean.app | `staging` |
| Monitoring | DO Droplet (143.198.173.164) | http://143.198.173.164:3000 | `main` |

## Automated Deployment (CI/CD)

Deployments are fully automated via GitHub Actions (`.github/workflows/tests.yml`):

1. **Push to `main`** triggers: tests → deploy to prod → health verification
2. **Push to `staging`** triggers: tests → deploy to staging → health verification
3. **Pull request** triggers: tests → deploy to staging → e2e smoke tests

Deploys are blocked if tests fail. The pipeline will not proceed to deployment.

## Manual Deployment

### Deploy to Production
```bash
doctl apps create-deployment $DO_APP_ID --wait
```

### Deploy to Staging
```bash
doctl apps create-deployment $DO_STAGING_APP_ID --wait
```

### Update Monitoring Stack
```bash
./scripts/update-monitoring.sh          # pull + restart
./scripts/update-monitoring.sh --reset  # pull + wipe Grafana + restart
```

### Verify Health
```bash
curl https://pe-hackathon-hni9m.ondigitalocean.app/health
curl https://pe-hackathon-staging-stj5i.ondigitalocean.app/health
```

## Rollback

DigitalOcean App Platform keeps deployment history. To rollback:

1. Go to the App Platform dashboard
2. Navigate to the app's **Activity** tab
3. Find the last successful deployment
4. Click **Rollback to this deployment**

Or via CLI — redeploy from a known-good commit:
```bash
git revert HEAD
git push origin main
# CI will automatically deploy the reverted commit
```

## Local Development

```bash
# Start all services (app + db + redis + monitoring)
docker compose up -d

# Run the app directly (requires local Postgres)
uv run python run.py

# Run tests
uv run pytest tests/ -v
```

## Infrastructure Management

### App IDs (for doctl)
```
Prod:    20ade529-aeb0-49f4-be02-779b07d6734e
Staging: 44e51338-6249-4469-92e7-4d9b4e3571cf
```

### Secrets Required in GitHub
| Secret | Purpose |
|---|---|
| `DIGITALOCEAN_ACCESS_TOKEN` | doctl authentication |
| `DO_APP_ID` | Prod app deployment |
| `DO_STAGING_APP_ID` | Staging app deployment |
| `APP_URL` | Prod health check URL |
| `STAGING_APP_URL` | Staging health check URL |
