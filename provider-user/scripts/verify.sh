#!/bin/bash
set -e

SERVICE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=../../lib/pact-common.sh
source "$SERVICE_DIR/../lib/pact-common.sh"

PROVIDER_VERSION=${PROVIDER_VERSION:-1.0.0}

echo "=== Verifying user-service ==="
cd "$SERVICE_DIR"
python3 -m venv venv
# shellcheck source=/dev/null
source venv/bin/activate
pip install -r requirements.txt -q
PACT_BROKER_URL="$PACT_BROKER_URL" \
PACT_BROKER_USERNAME="$PACT_BROKER_USERNAME" \
PACT_BROKER_PASSWORD="$PACT_BROKER_PASSWORD" \
PROVIDER_BASE_URL=http://localhost:5001 \
PROVIDER_VERSION="$PROVIDER_VERSION" \
pytest tests/test_provider_verification.py -v -W ignore::PendingDeprecationWarning

echo "=== Recording deployment to production ==="
record_deployment user-service "$PROVIDER_VERSION"

echo "✅ user-service verified and recorded in production!"
