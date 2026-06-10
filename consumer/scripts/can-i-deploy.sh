#!/bin/bash
set -e

SERVICE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=../../lib/pact-common.sh
source "$SERVICE_DIR/../lib/pact-common.sh"

SERVICE=${1:-"order-service"}
VERSION=${2:-"1.0.0"}

echo "=== Can I deploy $SERVICE v$VERSION? ==="
pact_broker_cli_docker can-i-deploy \
  --broker-base-url="$PACT_BROKER_URL" \
  --broker-username="$PACT_BROKER_USERNAME" \
  --broker-password="$PACT_BROKER_PASSWORD" \
  --pacticipant "$SERVICE" \
  --version "$VERSION" \
  --to-environment production
