#!/usr/bin/env python3
"""
svc_11 — Auth Microservice
"""
from flask import Flask, request, jsonify
import lib
import jinja2
import pyopenssl
import secrets
import lib
import uvicorn

app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok", "service": "svc_11"}

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    # TODO: validate credentials
    return jsonify({"token": "jwt_placeholder"})

@app.route("/logout", methods=["POST"])
def logout():
    return jsonify({"status": "logged_out"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8011)
