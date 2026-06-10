# Pact Contract Testing POC

A contract testing demo with Pact Broker and Jenkins CI/CD.

## Quick start

```bash
docker-compose up --build
```

The first run may take a few minutes (image builds, DB migrations, Jenkins startup).

## Services

| Service         | URL                    |
|-----------------|------------------------|
| Pact Broker UI  | http://localhost:9292  |
| Jenkins         | http://localhost:8080  |
| Order Service   | http://localhost:5003  |
| User Service    | http://localhost:5001  |
| Product Service | http://localhost:5002  |

Credentials everywhere: **admin** / **admin**

Order service is mapped to host port **5003** (not 5000) to avoid conflicts with macOS AirPlay Receiver.

## Architecture

```
order-service (consumer)
    ├── consumes → user-service (provider)
    └── consumes → product-service (provider)
```

Consumer tests generate pact files and publish them to Pact Broker. Provider verification checks that real APIs match the contracts.

## Workflow

1. Run Jenkins job **01-consumer-pact-tests** — consumer tests and contract publishing
2. Run **02-provider-user-verify** and **03-provider-product-verify** — provider verification
3. Open Pact Broker UI — compatibility matrix, contracts, verifications
4. Try breaking a contract (see Demo section)

### Manual run (without Jenkins)

Start the stack first (`docker compose up -d`). Each service has its own scripts; shared broker helpers live in `lib/pact-common.sh`.

- `pact-broker` CLI — via the `consumer` Docker container if the Ruby gem is not installed on the host

```bash
chmod +x consumer/scripts/*.sh provider-user/scripts/*.sh provider-product/scripts/*.sh

# Consumer: tests + publish (requires running pact-broker)
./consumer/scripts/publish-pacts.sh

# Providers: verify against broker (ports 5001/5002 on localhost)
# Records deployment in production automatically after a successful verify
./provider-user/scripts/verify.sh
./provider-product/scripts/verify.sh

# Consumer: deployment readiness (both providers must be verified first)
./consumer/scripts/can-i-deploy.sh order-service 1.0.0
```

`can-i-deploy` returns **no** if providers are not verified or their versions are not recorded in `production`.
To record deployments manually without re-running verification:

```bash
./provider-user/scripts/record-deployment.sh 1.0.0
./provider-product/scripts/record-deployment.sh 1.0.0
```

### Verify via Docker

```bash
docker-compose ps
curl http://localhost:9292/diagnostic/status/heartbeat
docker-compose exec consumer bash -c "cd /app && pytest tests/ -v"
```

## Demo: Breaking Contract

1. Replace `provider-product/app.py` with the contents of `app_broken.py`
2. Restart the container: `docker-compose restart provider-product`
3. Run Jenkins job **03-provider-product-verify**
4. Watch verification fail with: expected `price` but got `cost`
5. Pact Broker UI shows a red status in the matrix
6. `can-i-deploy` returns **NO** — deployment blocked

```bash
cp provider-product/app_broken.py provider-product/app.py
docker-compose up --build -d provider-product
./provider-product/scripts/verify.sh
```

## Project structure

```
├── lib/
│   └── pact-common.sh      # shared broker CLI helpers
├── consumer/
│   ├── pacts/              # generated contract JSON files
│   ├── scripts/
│   │   ├── publish-pacts.sh
│   │   └── can-i-deploy.sh
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_user_pact.py
│   │   └── test_product_pact.py
│   └── app.py
├── provider-user/
│   ├── scripts/
│   │   ├── verify.sh
│   │   └── record-deployment.sh
│   ├── tests/
│   │   └── test_provider_verification.py
│   └── app.py
├── provider-product/
│   ├── scripts/
│   │   ├── verify.sh
│   │   └── record-deployment.sh
│   ├── tests/
│   │   └── test_provider_verification.py
│   ├── app.py
│   └── app_broken.py       # breaking change demo
├── jenkins/                # Jenkins + JCasC pipelines
└── docker-compose.yml
```

## Jenkins

Jobs are created automatically via JCasC on startup:

- `01-consumer-pact-tests`
- `02-provider-user-verify`
- `03-provider-product-verify`

If jobs did not appear after the first start:

```bash
docker-compose restart jenkins
docker-compose logs jenkins | grep -i casc
```

Jenkins pipelines expect a git repo at `http://host.docker.internal/pact-poc`. For local development, use the scripts under each service folder.

## Known issues

- **pact-broker unhealthy**: the image has no `curl` — healthcheck uses `wget` + `127.0.0.1`. If broker is `unhealthy`, consumer and jenkins won't start: `docker compose up -d --force-recreate pact-broker consumer jenkins`
- **pact-python + Ruby**: consumer Dockerfile installs `pact-mock_service` (Ruby gem)
- **Jenkins first start**: 2–3 minutes until ready
# pact.io
