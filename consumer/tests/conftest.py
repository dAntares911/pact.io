import os

import pytest
from pact import Consumer, Provider

PACT_DIR = os.path.join(os.path.dirname(__file__), "..", "pacts")
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
PACT_MOCK_HOST = "localhost"


@pytest.fixture(scope="session")
def pact_user():
    pact = Consumer("order-service").has_pact_with(
        Provider("user-service"),
        host_name=PACT_MOCK_HOST,
        port=1234,
        pact_dir=PACT_DIR,
        log_dir=LOG_DIR,
    )
    pact.start_service()
    yield pact
    pact.stop_service()


@pytest.fixture(scope="session")
def pact_product():
    pact = Consumer("order-service").has_pact_with(
        Provider("product-service"),
        host_name=PACT_MOCK_HOST,
        port=1235,
        pact_dir=PACT_DIR,
        log_dir=LOG_DIR,
    )
    pact.start_service()
    yield pact
    pact.stop_service()
