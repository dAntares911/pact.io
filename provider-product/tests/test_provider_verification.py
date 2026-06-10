import os

from pact import Verifier

PACT_BROKER_URL = os.getenv("PACT_BROKER_URL", "http://localhost:9292")
PACT_BROKER_USERNAME = os.getenv("PACT_BROKER_USERNAME", "admin")
PACT_BROKER_PASSWORD = os.getenv("PACT_BROKER_PASSWORD", "admin")
PROVIDER_BASE_URL = os.getenv("PROVIDER_BASE_URL", "http://localhost:5002")
PROVIDER_VERSION = os.getenv("PROVIDER_VERSION", "1.0.0")


def test_verify_consumer_contracts():
    verifier = Verifier(
        provider="product-service",
        provider_base_url=PROVIDER_BASE_URL,
    )
    output, _ = verifier.verify_with_broker(
        broker_url=PACT_BROKER_URL,
        broker_username=PACT_BROKER_USERNAME,
        broker_password=PACT_BROKER_PASSWORD,
        provider_states_setup_url=f"{PROVIDER_BASE_URL}/pact-setup",
        enable_pending=False,
        publish_verification_results=True,
        publish_version=PROVIDER_VERSION,
    )
    assert output == 0, "Pact verification failed"
