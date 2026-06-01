#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
echo "Preparing Agent local data-plane scaffold"
mkdir -p .agent-data/storage
echo "Agent scaffold ready. Use deploy/env.agent.example as the environment template."
