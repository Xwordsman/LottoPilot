#!/usr/bin/env sh
set -eu
# helper for local developers without docker
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "created .env from .env.example"
fi
echo "Next: edit .env, then run: docker compose up -d --build"
