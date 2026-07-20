#!/usr/bin/env bash
# CloudOptima — Deploy to Azure Container Apps (Consumption Plan)
# Run this from Azure Cloud Shell (https://shell.azure.com)
#
# Prerequisites:
#   1. Build and push Docker image (see build-and-push.sh)
#   2. Run this script in Azure Cloud Shell
#
# Usage:
#   bash deploy/deploy.sh --image your-dockerhub-username/cloudoptima:latest

set -euo pipefail

IMAGE=""
RESOURCE_GROUP="rg-cloudoptima"
LOCATION="centralindia"
ENV_NAME="cloudoptima-env"
APP_NAME="cloudoptima"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image) IMAGE="$2"; shift 2 ;;
    --rg) RESOURCE_GROUP="$2"; shift 2 ;;
    --location) LOCATION="$2"; shift 2 ;;
    --env-name) ENV_NAME="$2"; shift 2 ;;
    --app-name) APP_NAME="$2"; shift 2 ;;
    --help)
      echo "Usage: bash deploy.sh --image <image> [options]"
      echo "  --image <image>     Docker image to deploy (required)"
      echo "  --rg <name>         Resource group (default: rg-cloudoptima)"
      echo "  --location <region> Azure region (default: centralindia)"
      echo "  --env-name <name>   Environment name (default: cloudoptima-env)"
      echo "  --app-name <name>   App name (default: cloudoptima)"
      exit 0
      ;;
    *) echo "Error: Unknown option: $1"; exit 1 ;;
  esac
done

if [ -z "$IMAGE" ]; then
  echo "Error: --image is required"
  echo "Usage: bash deploy.sh --image your-dockerhub-username/cloudoptima:latest"
  exit 1
fi

echo "CloudOptima — Azure Deployment"
echo "  Image:       $IMAGE"
echo "  Resource Grp: $RESOURCE_GROUP"
echo "  Location:    $LOCATION"
echo ""

# Login check
if ! az account show &>/dev/null; then
  echo "Error: Not logged in. Run 'az login' first."
  exit 1
fi
echo "Logged into Azure"

# Resource Group
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
echo "Resource group ready: $RESOURCE_GROUP"

# Container Apps Environment
if ! az containerapp env show --name "$ENV_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  az containerapp env create \
    --name "$ENV_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none
  echo "Environment created: $ENV_NAME"
else
  echo "Environment already exists: $ENV_NAME"
fi

# Deploy
echo "Deploying CloudOptima (2-5 minutes)..."
az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENV_NAME" \
  --image "$IMAGE" \
  --target-port 8501 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1 \
  --env-vars DEMO_MODE=true LOG_LEVEL=INFO \
  --cpu 0.25 \
  --memory 0.5Gi \
  --output table

echo ""
echo "Deployment complete!"

FQDN=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv 2>/dev/null || echo "")

if [ -n "$FQDN" ]; then
  echo "Your CloudOptima is live at: https://$FQDN"
fi

echo ""
echo "Useful commands:"
echo "  View logs:     az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --tail 50"
echo "  Stream logs:   az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo "  Delete all:    az group delete --name $RESOURCE_GROUP --yes --no-wait"
