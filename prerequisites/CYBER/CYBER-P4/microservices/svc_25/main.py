#!/usr/bin/env python3
"""
svc_25 — Notify Microservice
"""
from flask import Flask, request, jsonify
import gevent
import lib
import phonenumbers

app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok", "service": "svc_25"}

@app.route("/items", methods=["GET"])
def list_items():
    return jsonify({"items": []})

@app.route("/items/<item_id>", methods=["GET"])
def get_item(item_id):
    return jsonify({"id": item_id, "data": {}})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8025)
