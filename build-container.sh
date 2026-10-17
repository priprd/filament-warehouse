#!/usr/bin/env bash
set -e

# Auto-detect container engine (podman or docker)
CONTAINER_CMD="podman"
if ! command -v podman &> /dev/null; then
    CONTAINER_CMD="docker"
fi

VERSION=$(cat VERSION 2>/dev/null || echo "v1.0.0")
IMAGE_NAME="minions-filaments-warehouse"

CONTAINER_FILE="Containerfile"
if [ ! -f "$CONTAINER_FILE" ]; then
    CONTAINER_FILE="Dockerfile"
fi

echo "🍌 Building Container Image with ${CONTAINER_CMD} using ${CONTAINER_FILE}: ${IMAGE_NAME}:${VERSION} ..."

${CONTAINER_CMD} build -f "${CONTAINER_FILE}" -t "${IMAGE_NAME}:${VERSION}" -t "${IMAGE_NAME}:latest" .

echo "✅ Container Image built successfully with ${CONTAINER_CMD}!"
echo "Image Tags:"
echo "  - ${IMAGE_NAME}:${VERSION}"
echo "  - ${IMAGE_NAME}:latest"

