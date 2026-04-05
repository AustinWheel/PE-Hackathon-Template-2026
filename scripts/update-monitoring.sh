#!/bin/bash
# Pull latest config from git and restart the monitoring stack on the droplet.
#
# Usage: ./scripts/update-monitoring.sh [--reset]
#
# Environment variables:
#   MONITORING_IP    - droplet IP (default: 143.198.173.164)
#   MONITORING_USER  - SSH user (default: root)
#   REPO_BRANCH      - git branch to pull (default: main)
#   REPO_PATH        - path to repo on droplet (default: /opt/monitoring-repo)
#   COMPOSE_PATH     - path to docker-compose dir (default: /root/monitoring)

set -e

# Load .env if present
ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
  set -a; source "$ENV_FILE"; set +a
fi

IP="${MONITORING_IP:-143.198.173.164}"
USER="${MONITORING_USER:-root}"
BRANCH="${REPO_BRANCH:-main}"
REPO="${REPO_PATH:-/opt/monitoring-repo}"
COMPOSE="${COMPOSE_PATH:-/root/monitoring}"

echo "Pulling latest ($BRANCH) on $IP..."
ssh "$USER@$IP" "cd $REPO && git pull origin $BRANCH"

if [ "$1" = "--reset" ]; then
  echo "Resetting Grafana (wiping volume)..."
  ssh "$USER@$IP" "cd $COMPOSE && docker compose stop grafana && docker compose rm -f grafana && docker volume rm monitoring_grafana-data && docker compose up -d grafana"
else
  echo "Restarting Grafana and Prometheus..."
  ssh "$USER@$IP" "cd $COMPOSE && docker compose restart grafana prometheus"
fi

echo "Done. Grafana: http://$IP:3000"
