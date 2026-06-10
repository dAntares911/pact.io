#!/bin/bash
set -e

SERVICE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=../../lib/pact-common.sh
source "$SERVICE_DIR/../lib/pact-common.sh"

CONSUMER_VERSION=${CONSUMER_VERSION:-1.0.3}

echo "=== Running consumer pact tests ==="
cd "$SERVICE_DIR"
python3 -m venv venv
# shellcheck source=/dev/null
source venv/bin/activate
pip install -r requirements.txt -q
pytest tests/ -v -W ignore::PendingDeprecationWarning

echo "=== Publishing pacts to broker ==="
pact_broker_cli_docker publish pacts/ \
  --broker-base-url="$PACT_BROKER_URL" \
  --broker-username="$PACT_BROKER_USERNAME" \
  --broker-password="$PACT_BROKER_PASSWORD" \
  --consumer-app-version="$CONSUMER_VERSION" \
  --tag main

echo "✅ Pacts published!"
