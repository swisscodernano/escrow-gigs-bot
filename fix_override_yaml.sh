#!/bin/bash
set -euo pipefail
cat > docker-compose.override.yml <<'YAML'
services:
  app:
    env_file:
      - .env
YAML
echo "Override YAML riscritto."
