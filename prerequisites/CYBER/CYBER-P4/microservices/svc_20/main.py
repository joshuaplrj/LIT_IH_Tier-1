#!/usr/bin/env python3
"""
svc_20 — Orders Microservice
"""
from flask import Flask, request, jsonify
import msgpack
import lib
import pyzmq
import scikit
import stdnum

app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok", "service": "svc_20"}

@app.route("/items", methods=["GET"])
def list_items():
    return jsonify({"items": []})

@app.route("/items/<item_id>", methods=["GET"])
def get_item(item_id):
    return jsonify({"id": item_id, "data": {}})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8020)
