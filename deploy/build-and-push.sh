#!/usr/bin/env bash
# CloudOptima — Build & Push Docker Image
#
# Usage:
#   Option A: Push to Docker Hub (free, no Azure CLI needed)
#     export DOCKER_USERNAME="your-dockerhub-username"
#     bash deploy/build-and-push.sh dockerhub
#
#   Option B: Push to Azure Container Registry
#     az login
#     export ACR_NAME="cloudoptimaregistry"
#     bash deploy/build-and-push.sh acr
#
#   Option C: Push to GitHub Container Registry
#     export GH_USERNAME="G-Narendra"
#     export CR_PAT="your-github-classic-token"
#     bash deploy/build-and-push.sh ghcr

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="cloudoptima"
IMAGE_TAG="${IMAGE_TAG:-latest}"

cd "$PROJECT_DIR"

echo "CloudOptima — Build & Push"
echo ""

echo "Building Docker image (linux/amd64): $IMAGE_NAME:$IMAGE_TAG ..."
docker build --platform linux/amd64 -t "$IMAGE_NAME:$IMAGE_TAG" -f Dockerfile .
echo "Build complete"
echo ""

TARGET="${1:-dockerhub}"

case "$TARGET" in
  dockerhub)
    if [ -z "${DOCKER_USERNAME:-}" ]; then
      echo "Error: Set DOCKER_USERNAME=<your-dockerhub-username> first"
      exit 1
    fi
    REMOTE_TAG="$DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$REMOTE_TAG"
    echo "Pushing to Docker Hub: $REMOTE_TAG ..."
    docker push "$REMOTE_TAG"
    echo "Pushed to Docker Hub"
    echo ""
    echo "Next step: Go to https://shell.azure.com and run:"
    echo "  git clone https://github.com/G-Narendra/CloudOptima.git"
    echo "  cd CloudOptima"
    echo "  bash deploy/deploy.sh --image \"$REMOTE_TAG\""
    ;;

  acr)
    if [ -z "${ACR_NAME:-}" ]; then
      echo "Error: Set ACR_NAME=<your-acr-name> first"
      exit 1
    fi
    echo "Logging into Azure Container Registry: $ACR_NAME ..."
    az acr login --name "$ACR_NAME"
    REMOTE_TAG="$ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG"
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$REMOTE_TAG"
    echo "Pushing to ACR: $REMOTE_TAG ..."
    docker push "$REMOTE_TAG"
    echo "Pushed to ACR"
    echo ""
    echo "Next step: Run deploy/deploy.sh from Azure Cloud Shell."
    ;;

  ghcr)
    if [ -z "${GH_USERNAME:-}" ]; then
      echo "Error: Set GH_USERNAME=<your-github-username> first"
      exit 1
    fi
    if [ -z "${CR_PAT:-}" ]; then
      echo "Error: Set CR_PAT=<your-github-classic-token> first"
      echo "Create a classic token at: https://github.com/settings/tokens"
      echo "Required scope: write:packages"
      exit 1
    fi
    REMOTE_TAG="ghcr.io/$GH_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    echo "$CR_PAT" | docker login ghcr.io -u "$GH_USERNAME" --password-stdin
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$REMOTE_TAG"
    echo "Pushing to GHCR: $REMOTE_TAG ..."
    docker push "$REMOTE_TAG"
    echo "Pushed to GitHub Container Registry"
    echo ""
    echo "Next step: Go to https://shell.azure.com and run deploy.sh"
    ;;

  *)
    echo "Error: Unknown target: $TARGET"
    echo "Usage: bash deploy/build-and-push.sh [dockerhub|acr|ghcr]"
    exit 1
    ;;
esac
