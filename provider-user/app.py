from flask import Flask, jsonify, request

app = Flask(__name__)

USERS = {
    1: {"id": 1, "name": "John Doe", "email": "john@example.com"},
    2: {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
}


@app.route("/users/<int:user_id>")
def get_user(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/pact-setup", methods=["POST"])
def pact_setup():
    state = request.json.get("state", "")
    if state == "user 1 exists":
        USERS[1] = {"id": 1, "name": "John Doe", "email": "john@example.com"}
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
