#!/usr/bin/env bash
# Constroi as imagens Docker de todos os componentes.
# Uso: ./scripts/build-images.sh [TAG]   (TAG padrao: latest)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-latest}"

build() { docker build -t "hora-marcada/$1:${TAG}" "$ROOT/$2"; }

build auth-service       services/auth-service
build scheduling-service services/scheduling-service
build api-gateway        services/api-gateway
build web                apps/web

echo "Imagens construidas com a tag '${TAG}'."
