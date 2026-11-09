
import os
import hmac
import hashlib
import json
import time
from urllib.parse import parse_qsl

from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

ALLOWED_ORIGIN = "https://zigzagbingo.github.io"


def verify_telegram_data(init_data):
    if not BOT_TOKEN or not init_data:
        return None

    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True))

        received_hash = data.pop("hash", None)

        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(data.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        auth_date = int(data.get("auth_date", "0"))

        if time.time() - auth_date > 86400:
            return None

        user = json.loads(data.get("user", "{}"))

        if not user.get("id"):
            return None

        return user

    except (ValueError, TypeError, json.JSONDecodeError):
        return None


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")

    if origin == ALLOWED_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"

    return response


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Mini App backend is running"})


@app.route("/api/me", methods=["POST", "OPTIONS"])
def get_player():
@app.route("/api/me", methods=["POST", "OPTIONS"])
def get_player():
    print("Mini App connection request received")

    if request.method == "OPTIONS":
        return "", 204
    body = request.get_json(silent=True) or {}
    init_data = body.get("initData", "")

    user = verify_telegram_data(init_data)

    if not user:
        return jsonify({"error": "Telegram verification failed"}), 401

    return jsonify({
        "verified": True,
        "player": {
            "id": user["id"],
            "first_name": user.get("first_name", ""),
            "username": user.get("username", "")
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
