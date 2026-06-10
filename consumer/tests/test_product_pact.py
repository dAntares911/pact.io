import requests
from pact import Like


def test_get_product(pact_product):
    expected = {"id": 1, "name": Like("Widget"), "price": Like(9.99)}

    (
        pact_product.given("product 1 exists")
        .upon_receiving("a request for product 1")
        .with_request("GET", "/products/1")
        .will_respond_with(200, body=expected)
    )

    with pact_product:
        result = requests.get("http://localhost:1235/products/1")
        assert result.status_code == 200
        data = result.json()
        assert "id" in data
        assert "name" in data
        assert "price" in data


def test_create_product(pact_product):
    request_body = {"name": Like("Gadget"), "prices": Like(19.99)}
    expected = {"id": Like(2), "name": Like("Gadget"), "prices": Like(19.99)}

    (
        pact_product.given("a product can be created")
        .upon_receiving("a request to create a product")
        .with_request(
            "POST",
            "/products",
            body=request_body,
            headers={"Content-Type": "application/json"},
        )
        .will_respond_with(201, body=expected)
    )

    with pact_product:
        result = requests.post(
            "http://localhost:1235/products",
            json={"name": "Gadget", "prices":19.99},
        )
        assert result.status_code == 201
