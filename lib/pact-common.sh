# Shared Pact Broker CLI helpers (used by service scripts).

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$LIB_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

export PACT_BROKER_URL="${PACT_BROKER_URL:-http://localhost:9292}"
export PACT_BROKER_USERNAME="${PACT_BROKER_USERNAME:-admin}"
export PACT_BROKER_PASSWORD="${PACT_BROKER_PASSWORD:-admin}"

PACT_BROKER_URL_DOCKER="${PACT_BROKER_URL_DOCKER:-http://pact-broker:9292}"

pact_broker_cli_docker() {
  local args=()
  for arg in "$@"; do
    case "$arg" in
      --broker-base-url=http://localhost:*|--broker-base-url=http://127.0.0.1:*)
        args+=(--broker-base-url="$PACT_BROKER_URL_DOCKER")
        ;;
      *)
        args+=("$arg")
        ;;
    esac
  done

  if command -v pact-broker >/dev/null 2>&1; then
    pact-broker "${args[@]}"
    return
  fi

  if ! docker compose -f "$COMPOSE_FILE" ps -q pact-broker 2>/dev/null | grep -q .; then
    echo "pact-broker container is not running. Start: docker compose up -d" >&2
    exit 1
  fi

  docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
    -v "$PROJECT_ROOT/consumer/pacts:/app/pacts:ro" \
    consumer pact-broker "${args[@]}"
}

record_deployment() {
  local pacticipant=$1
  local version=${2:-1.0.0}
  local environment=${3:-production}

  pact_broker_cli_docker record-deployment \
    --broker-base-url="$PACT_BROKER_URL" \
    --broker-username="$PACT_BROKER_USERNAME" \
    --broker-password="$PACT_BROKER_PASSWORD" \
    --pacticipant="$pacticipant" \
    --version="$version" \
    --environment="$environment"
}
