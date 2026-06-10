from flask import Flask, jsonify, request

app = Flask(__name__)

PRODUCTS = {
    1: {"id": 1, "name": "Widget", "price": 9.99},
    2: {"id": 2, "name": "Gadget", "price": 19.99},
}
_next_id = 3


@app.route("/products/<int:product_id>")
def get_product(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)


@app.route("/products", methods=["POST"])
def create_product():
    global _next_id
    data = request.json
    product = {"id": _next_id, "name": data["name"], "prices": data["prices"]}
    PRODUCTS[_next_id] = product
    _next_id += 1
    return jsonify(product), 201


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/pact-setup", methods=["POST"])
def pact_setup():
    state = request.json.get("state", "")
    if state == "product 1 exists":
        PRODUCTS[1] = {"id": 1, "name": "Widget", "price": 9.99}
    if state == "a product can be created":
        pass
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
