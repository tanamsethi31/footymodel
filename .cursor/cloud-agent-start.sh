#!/usr/bin/env bash
set -euo pipefail
cd /workspace/dashboard
exec npm run dev -- --hostname 0.0.0.0 --port 3000
