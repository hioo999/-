#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
echo "Preparing platform control-plane scaffold"
mkdir -p .platform-data
echo "Platform scaffold ready. Use deploy/env.platform.example as the environment template."
