#!/usr/bin/env bash
# AFDC downloads use the exported NLR_API_KEY (legacy NREL_API_KEY also works).
# No API key is stored or printed by this entry point.
set -euo pipefail
SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "${PYTHON:-python}" "$SCRIPT_ROOT/scripts/review_generate.py" "$@"
