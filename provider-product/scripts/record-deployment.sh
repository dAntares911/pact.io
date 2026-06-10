#!/bin/bash
set -e

SERVICE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=../../lib/pact-common.sh
source "$SERVICE_DIR/../lib/pact-common.sh"

VERSION=${1:-1.0.0}

echo "=== Recording product-service v$VERSION → production ==="
record_deployment product-service "$VERSION"

echo "✅ product-service deployment recorded."
