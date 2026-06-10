import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:5001")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:5002")


@app.route("/order/<int:user_id>/<int:product_id>")
def create_order(user_id, product_id):
    user = requests.get(f"{USER_SERVICE_URL}/users/{user_id}").json()
    product = requests.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}").json()
    return jsonify({
        "order_id": 1,
        "user": user,
        "product": product,
        "total": product["price"],
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
