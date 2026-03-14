#!/usr/bin/env python3
"""
svc_42 — Api Microservice
"""
from flask import Flask, request, jsonify
import lib
import trio
import channels
import marshmallow
import nats
import lib

app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok", "service": "svc_42"}

@app.route("/items", methods=["GET"])
def list_items():
    return jsonify({"items": []})

@app.route("/items/<item_id>", methods=["GET"])
def get_item(item_id):
    return jsonify({"id": item_id, "data": {}})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8042)
