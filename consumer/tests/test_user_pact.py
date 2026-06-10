import requests
from pact import Like, Term


def test_get_user(pact_user):
    expected = {
        "id": 1,
        "name": Like("John Doe"),
        "email": Term(r".+@.+\..+", "john@example.com"),
    }

    (
        pact_user.given("user 1 exists")
        .upon_receiving("a request for user 1")
        .with_request("GET", "/users/1")
        .will_respond_with(200, body=expected)
    )

    with pact_user:
        result = requests.get("http://localhost:1234/users/1")
        assert result.status_code == 200
        data = result.json()
        assert "id" in data
        assert "name" in data
        assert "email" in data
