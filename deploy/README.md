# CloudOptima — Azure Deployment Guide

> Deploy CloudOptima on Azure infrastructure — two options: **Container Apps** (recommended) or **App Service** (free tier).

---

## Which Service Should You Use?

| Feature | Azure Container Apps | Azure App Service (Free F1) |
|---------|---------------------|---------------------------|
| **Cost** | ~$0.10/day (scales to zero) | $0/month (limited quota) |
| **Supports Docker?** | Yes (native) | No (Windows only, no custom containers) |
| **CPU quota** | Pay per execution | 60 CPU minutes/day |
| **Best for** | Real demos, any traffic level | Quick demo, very low traffic |
| **Deploy time** | 5 minutes | 10 minutes |
| **Recommended?** | **Yes** ✅ | Use if Container Apps is blocked |

**Bottom line:** Container Apps is the better choice for your Docker-based app. It costs nearly $0 for demo usage. Use App Service only if you have subscription restrictions.

---

## Option 1: Azure Container Apps (Recommended)

### Step 1: Build & Push Docker Image

You need Docker installed locally (you have it — v29.6.1).

```bash
# Option A: Push to Docker Hub (free, no Azure CLI needed)
export DOCKER_USERNAME="your-dockerhub-username"
bash deploy/build-and-push.sh dockerhub

# Option B: Push to Azure Container Registry (requires Azure CLI)
export ACR_NAME="cloudoptimaregistry"
bash deploy/build-and-push.sh acr
```

> Dont have Docker Hub? Create one free at hub.docker.com (2 minutes).

### Step 2: Deploy from Azure Cloud Shell

1. Go to **shell.azure.com** (Azure CLI is pre-installed)
2. Select **Bash** (not PowerShell)
3. Run:

```bash
git clone https://github.com/G-Narendra/CloudOptima.git
cd CloudOptima

# Deploy from Docker Hub (change username to yours!)
bash deploy/deploy.sh --image your-dockerhub-username/cloudoptima:latest
```

4. Wait 2-5 minutes
5. Open the URL shown at the end

### What You Get

| Resource | Plan | Cost |
|----------|------|------|
| Container Apps Environment | Consumption | $0/month at 0 replicas |
| Container App | 0.25 CPU, 0.5GB RAM | ~$0.10/day with light use |
| **Total** | | **~$3/month** (covered by your $100 credits) |

Auto-scales to zero when not in use.

---

## Option 2: Azure App Service Free Tier (Fallback)

If Container Apps is not available in your subscription:

### Deploy via Azure CLI Cloud Shell

```bash
# In Azure Cloud Shell
git clone https://github.com/G-Narendra/CloudOptima.git
cd CloudOptima

# Create App Service plan (Free F1 - Linux is not free, but B1 works)
# Note: Free F1 is Windows-only. We use B1 Linux for Python support.
az webapp up \
  --name cloudoptima-student \
  --resource-group rg-cloudoptima \
  --sku B1 \
  --location centralindia \
  --runtime "PYTHON:3.11"
```

However, App Service Free F1 is **Windows-only** and requires a different approach since your app uses a Docker container. The recommended path is always Container Apps.

---

## Configuration Options

### Set a Custom Region

```bash
bash deploy/deploy.sh \
  --image your-username/cloudoptima:latest \
  --location uaenorth
```

Options: `centralindia`, `uaenorth`, `westeurope`, `eastus`

### Switch to Live API Mode (requires NVIDIA API key)

```bash
az containerapp create \
  --name cloudoptima \
  --resource-group rg-cloudoptima \
  --environment cloudoptima-env \
  --image your-username/cloudoptima:latest \
  --target-port 8501 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1 \
  --env-vars \
    DEMO_MODE=false \
    NVIDIA_API_KEY=secretref:nvidia-api-key \
  --secrets nvidia-api-key="your-actual-key-here" \
  --cpu 0.5 \
  --memory 1Gi
```

---

## Continuous Deployment via GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Azure Container Apps
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Log in to Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - name: Build and deploy
        uses: azure/container-apps-deploy-action@v1
        with:
          appSourcePath: .
          containerAppName: cloudoptima
          resourceGroup: rg-cloudoptima
          containerAppEnvironment: cloudoptima-env
```

---

## Clean Up (Stop Costs)

```bash
az group delete --name rg-cloudoptima --yes --no-wait
```

---

## Cost Breakdown

| Usage Scenario | Monthly Cost |
|----------------|-------------|
| No visits (0 replicas) | $0.00 |
| 1-2 demos per day (~30 min) | ~$0.50 |
| Light usage (~2 hours/day) | ~$3.00 |
| Heavy demo day (8 hours) | ~$2.50/day |
| **Covered by your $100 credits?** | **Yes, easily** |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Image pull failed | Make Docker Hub repo public, check image name |
| Container crash looping | Check logs: `az containerapp logs show --name cloudoptima --resource-group rg-cloudoptima --tail 100` |
| App loads but shows error | Ensure DEMO_MODE=true (works without API keys) |
| Quota exceeded | Try a different region or request quota increase |
| Platform mismatch | Image must be linux/amd64 (build-and-push.sh already handles this) |

---

## Why This Matters for Microsoft

| What This Proves | How |
|-----------------|-----|
| Azure-native deployment | Running on Azure Container Apps, not third-party hosting |
| Container expertise | Using Docker + Azure container platform |
| Auto-scaling design | Scales to zero cost-conscious architecture |
| Student ambition | Going beyond basic VMs to serverless containers |
| Azure ecosystem | Using ACR, Container Apps, managed identity |
