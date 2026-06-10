#!/bin/bash
set -e

SERVICE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=../../lib/pact-common.sh
source "$SERVICE_DIR/../lib/pact-common.sh"

VERSION=${1:-1.0.0}

echo "=== Recording user-service v$VERSION → production ==="
record_deployment user-service "$VERSION"

echo "✅ user-service deployment recorded."
