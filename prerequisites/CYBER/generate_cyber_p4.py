#!/usr/bin/env python3
"""
CYBER-P4: Supply Chain Sentinel
Generates dependency graph, microservices, SBOMs, and hidden compromised package info.
"""

import os
import json
import random
import uuid
import string

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CYBER-P4")

random.seed(77777)

# ─── Package pools ────────────────────────────────────────────────────────────

# Legitimate PyPI packages (realistic names)
LEGIT_PYPI = [
    "requests", "numpy", "flask", "django", "fastapi", "aiohttp",
    "sqlalchemy", "alembic", "celery", "redis", "pymongo", "psycopg2",
    "boto3", "botocore", "paramiko", "cryptography", "pyjwt", "bcrypt",
    "pydantic", "marshmallow", "click", "typer", "rich", "loguru",
    "httpx", "httpcore", "urllib3", "certifi", "charset-normalizer",
    "pillow", "scipy", "pandas", "matplotlib", "seaborn", "scikit-learn",
    "tensorflow", "torch", "transformers", "huggingface-hub",
    "pytest", "pytest-asyncio", "pytest-cov", "coverage", "mypy",
    "black", "flake8", "isort", "pylint", "bandit",
    "uvicorn", "gunicorn", "starlette", "werkzeug", "jinja2",
    "toml", "pyyaml", "python-dotenv", "environs", "dynaconf",
    "grpcio", "protobuf", "kafka-python", "pika", "nats-py",
    "prometheus-client", "opentelemetry-api", "opentelemetry-sdk",
    "sentry-sdk", "datadog", "structlog", "python-json-logger",
    "arrow", "pendulum", "pytz", "dateutil",
    "passlib", "itsdangerous", "secrets-manager", "keyring",
    "fabric", "invoke", "sh", "subprocess32",
    "tenacity", "backoff", "retry", "circuitbreaker",
    "cachetools", "diskcache", "dogpile.cache",
    "elasticsearch", "opensearch-py", "pinecone-client",
    "stripe", "twilio", "sendgrid", "mailchimp-marketing",
    "google-cloud-storage", "google-cloud-pubsub", "azure-storage-blob",
    "minio", "s3transfer",
    "networkx", "igraph", "pydot",
    "lxml", "beautifulsoup4", "scrapy", "playwright",
    "docker", "kubernetes", "ansible", "terraform",
    "jsonschema", "cerberus", "voluptuous",
    "asyncpg", "aiomysql", "aiosqlite", "motor",
    "channels", "daphne", "twisted",
    "pyserial", "usb", "hid",
    "ftplib", "smtplib", "imaplib",
    "zipfile", "tarfile", "py7zr",
    "hashlib", "hmac", "secrets",
    "multiprocessing", "concurrent-futures", "joblib",
    "pexpect", "ptyprocess",
    "Pillow", "imageio", "opencv-python",
    "shapely", "geopandas", "folium",
    "flask-sqlalchemy", "flask-migrate", "flask-login",
    "django-rest-framework", "django-cors-headers", "django-filter",
    "marshmallow-sqlalchemy", "apispec", "flasgger",
    "python-multipart", "aiofiles", "anyio",
    "trio", "curio", "gevent",
    "pyzmq", "msgpack", "cbor2",
    "arrow", "orjson", "ujson", "simplejson",
    "tabulate", "prettytable", "texttable",
    "colorama", "termcolor", "blessed",
    "psutil", "py-cpuinfo", "gputil",
    "watchdog", "schedule", "apscheduler",
    "cryptography", "pyopenssl", "truststore",
    "xmlsec", "lxml-stubs",
    "email-validator", "phonenumbers", "stdnum",
    "braintree", "paypalrestsdk",
    "gitpython", "dulwich",
    "parameterized", "faker", "factory-boy", "hypothesis",
    "locust", "molotov", "artillery",
]

# Legitimate npm packages
LEGIT_NPM = [
    "lodash", "express", "axios", "react", "vue", "angular",
    "typescript", "webpack", "babel", "eslint", "prettier",
    "jest", "mocha", "chai", "sinon", "supertest",
    "mongoose", "sequelize", "typeorm", "prisma",
    "redis", "ioredis", "bull", "bullmq",
    "socket.io", "ws", "uWebSockets.js",
    "passport", "passport-jwt", "passport-local", "jsonwebtoken",
    "bcrypt", "bcryptjs", "argon2", "speakeasy",
    "dotenv", "config", "convict", "nconf",
    "winston", "pino", "bunyan", "debug",
    "morgan", "helmet", "cors", "compression",
    "multer", "formidable", "busboy",
    "nodemailer", "mailgun-js", "sendgrid",
    "stripe", "braintree", "paypal",
    "aws-sdk", "googleapis", "azure-sdk",
    "sharp", "jimp", "imagemin",
    "cheerio", "puppeteer", "playwright",
    "graphql", "apollo-server", "apollo-client",
    "grpc", "protobufjs",
    "moment", "dayjs", "luxon", "date-fns",
    "uuid", "nanoid", "shortid",
    "yup", "joi", "zod", "ajv",
    "lodash.merge", "lodash.clonedeep", "lodash.get",
    "ramda", "immutable", "immer",
    "rxjs", "rxjs-compat",
    "next", "nuxt", "gatsby",
    "tailwindcss", "styled-components", "emotion",
    "redux", "mobx", "zustand", "recoil",
    "framer-motion", "react-spring", "anime",
    "d3", "chart.js", "echarts", "highcharts",
    "three", "babylon.js", "pixi.js",
    "node-fetch", "got", "superagent", "needle",
    "cheerio", "html-parser2", "parse5",
    "csv-parser", "papaparse", "fast-csv",
    "xlsx", "exceljs", "pdfkit",
    "archiver", "adm-zip", "node-tar",
    "crypto-js", "node-forge", "openpgp",
    "pm2", "forever", "nodemon",
    "docker", "dockerode",
    "nock", "sinon", "proxyquire",
    "istanbul", "nyc", "c8",
    "husky", "lint-staged", "commitizen",
    "rollup", "parcel", "vite",
    "esbuild", "swc",
]

# Compromised package names (50 total — mix of typosquats, dependency confusion, backdoored, miners)
COMPROMISED_PACKAGES = [
    # Typosquatting (10)
    {"name": "requets",           "version": "2.28.2", "ecosystem": "pypi",
     "type": "typosquat", "mimics": "requests",
     "payload": "HTTP POST credentials to 203.0.113.99/exfil"},
    {"name": "numpyy",            "version": "1.24.1", "ecosystem": "pypi",
     "type": "typosquat", "mimics": "numpy",
     "payload": "Exfiltrate environment variables on import"},
    {"name": "numpy-ml",          "version": "0.5.0",  "ecosystem": "pypi",
     "type": "typosquat", "mimics": "numpy",
     "payload": "Backdoor: reverse shell on TCP 203.0.113.99:4444"},
    {"name": "flask-utils",       "version": "1.0.3",  "ecosystem": "pypi",
     "type": "typosquat", "mimics": "flask",
     "payload": "Log all HTTP request bodies and POST to 203.0.113.99/log"},
    {"name": "expres",            "version": "4.18.2", "ecosystem": "npm",
     "type": "typosquat", "mimics": "express",
     "payload": "Monkey-patch res.json to exfiltrate responses"},
    {"name": "lod4sh",            "version": "4.17.21","ecosystem": "npm",
     "type": "typosquat", "mimics": "lodash",
     "payload": "Override lodash.merge with backdoored version (prototype pollution)"},
    {"name": "axi0s",             "version": "1.4.0",  "ecosystem": "npm",
     "type": "typosquat", "mimics": "axios",
     "payload": "Intercept all HTTP requests and copy to 203.0.113.99"},
    {"name": "djang0",            "version": "4.2.7",  "ecosystem": "pypi",
     "type": "typosquat", "mimics": "django",
     "payload": "Replace Django SECRET_KEY with fixed known value"},
    {"name": "cryptographyy",     "version": "41.0.5", "ecosystem": "pypi",
     "type": "typosquat", "mimics": "cryptography",
     "payload": "Weak RNG: patch os.urandom to use predictable PRNG"},
    {"name": "psycopg2-binary2",  "version": "2.9.7",  "ecosystem": "pypi",
     "type": "typosquat", "mimics": "psycopg2",
     "payload": "Log all DB queries and credentials to 203.0.113.99/db"},

    # Dependency confusion (10)
    {"name": "internal-auth-lib",      "version": "3.1.0", "ecosystem": "pypi",
     "type": "dependency_confusion", "mimics": "internal package",
     "payload": "Exfiltrate sys.path and installed packages"},
    {"name": "company-config",         "version": "2.0.1", "ecosystem": "pypi",
     "type": "dependency_confusion", "mimics": "internal package",
     "payload": "Read /etc/passwd, /etc/shadow and POST to 203.0.113.99"},
    {"name": "svc-common-utils",       "version": "1.5.0", "ecosystem": "pypi",
     "type": "dependency_confusion", "mimics": "internal package",
     "payload": "Cloud metadata SSRF: curl http://169.254.169.254/latest/meta-data/"},
    {"name": "platform-sdk",           "version": "0.9.0", "ecosystem": "npm",
     "type": "dependency_confusion", "mimics": "internal package",
     "payload": "Exfiltrate process.env to 203.0.113.99/env"},
    {"name": "infra-shared",           "version": "1.1.0", "ecosystem": "npm",
     "type": "dependency_confusion", "mimics": "internal package",
     "payload": "Read ~/.aws/credentials and ~/.kube/config"},
    {"name": "data-pipeline-core",     "version": "2.3.0", "ecosystem": "pypi",
     "type": "dependency_confusion", "mimics": "internal package",
     "payload": "Pickle deserialization RCE backdoor in serializer"},
    {"name": "ml-feature-store",       "version": "0.4.2", "ecosystem": "pypi",
     "type": "dependency_confusion", "mimics": "internal package",
     "payload": "Model weight exfiltration to 203.0.113.99/models"},
    {"name": "event-bus-client",       "version": "1.0.5", "ecosystem": "npm",
     "type": "dependency_confusion", "mimics": "internal package",
     "payload": "Duplicate all event messages to attacker endpoint"},
    {"name": "shared-crypto-utils",    "version": "1.2.0", "ecosystem": "pypi",
     "type": "dependency_confusion", "mimics": "internal package",
     "payload": "Replace AES implementation with RSA 512-bit (weak)"},
    {"name": "service-mesh-helpers",   "version": "0.7.1", "ecosystem": "npm",
     "type": "dependency_confusion", "mimics": "internal package",
     "payload": "Register rogue service in service mesh"},

    # Backdoored (20) — popular package maintainer compromise simulation
    {"name": "celery-backdoor",     "version": "5.3.4", "ecosystem": "pypi",
     "type": "backdoor", "mimics": "celery",
     "payload": "Execute arbitrary Python from task queue message headers"},
    {"name": "sqlalchemy-extra",    "version": "2.0.23","ecosystem": "pypi",
     "type": "backdoor", "mimics": "sqlalchemy",
     "payload": "Log all SQL queries + connection strings to 203.0.113.99"},
    {"name": "pydantic-extras",     "version": "2.5.2", "ecosystem": "pypi",
     "type": "backdoor", "mimics": "pydantic",
     "payload": "Serialize validated models and exfiltrate via UDP"},
    {"name": "fastapi-security",    "version": "0.104.1","ecosystem": "pypi",
     "type": "backdoor", "mimics": "fastapi",
     "payload": "Bypass JWT validation on endpoints tagged 'secure'"},
    {"name": "httpx-async",         "version": "0.25.2","ecosystem": "pypi",
     "type": "backdoor", "mimics": "httpx",
     "payload": "MITM: log all HTTP request/response bodies"},
    {"name": "redis-cluster-py",    "version": "4.6.0", "ecosystem": "pypi",
     "type": "backdoor", "mimics": "redis",
     "payload": "Exfiltrate all Redis GET/SET operations"},
    {"name": "boto3-enhanced",      "version": "1.33.0","ecosystem": "pypi",
     "type": "backdoor", "mimics": "boto3",
     "payload": "Copy all S3 PUT operations to attacker bucket"},
    {"name": "jwt-extended",        "version": "4.5.3", "ecosystem": "pypi",
     "type": "backdoor", "mimics": "pyjwt",
     "payload": "Accept tokens signed with hardcoded attacker key"},
    {"name": "uvicorn-pro",         "version": "0.24.0","ecosystem": "pypi",
     "type": "backdoor", "mimics": "uvicorn",
     "payload": "Add hidden /debug endpoint returning system info"},
    {"name": "grpcio-tools2",       "version": "1.59.3","ecosystem": "pypi",
     "type": "backdoor", "mimics": "grpcio",
     "payload": "Intercept gRPC calls and copy metadata to 203.0.113.99"},
    {"name": "passport-oauth-extra","version": "0.6.0", "ecosystem": "npm",
     "type": "backdoor", "mimics": "passport",
     "payload": "Store OAuth tokens in attacker-controlled location"},
    {"name": "mongoose-plugin-audit","version":"7.4.0", "ecosystem": "npm",
     "type": "backdoor", "mimics": "mongoose",
     "payload": "POST all document writes to 203.0.113.99/mongo"},
    {"name": "winston-remote",      "version": "3.11.0","ecosystem": "npm",
     "type": "backdoor", "mimics": "winston",
     "payload": "Forward all log entries to 203.0.113.99/logs"},
    {"name": "helmet-plus",         "version": "7.1.0", "ecosystem": "npm",
     "type": "backdoor", "mimics": "helmet",
     "payload": "Disable CSP headers while appearing to set them"},
    {"name": "jsonwebtoken-verify",  "version": "9.0.2","ecosystem": "npm",
     "type": "backdoor", "mimics": "jsonwebtoken",
     "payload": "Accept 'alg:none' tokens bypassing signature verification"},
    {"name": "prisma-client-extra",  "version": "5.6.0","ecosystem": "npm",
     "type": "backdoor", "mimics": "prisma",
     "payload": "Log all DB queries to 203.0.113.99/prisma"},
    {"name": "socket.io-admin",      "version": "4.6.2","ecosystem": "npm",
     "type": "backdoor", "mimics": "socket.io",
     "payload": "Add hidden admin namespace with no authentication"},
    {"name": "bullmq-worker-extra",  "version": "5.1.0","ecosystem": "npm",
     "type": "backdoor", "mimics": "bullmq",
     "payload": "Execute shell commands embedded in job data"},
    {"name": "axios-oauth-client",   "version": "1.6.0","ecosystem": "npm",
     "type": "backdoor", "mimics": "axios",
     "payload": "Exfiltrate OAuth2 access tokens on each request"},
    {"name": "typeorm-audit-log",    "version": "0.3.17","ecosystem": "npm",
     "type": "backdoor", "mimics": "typeorm",
     "payload": "Mirror all entity writes to attacker DB at 203.0.113.99"},

    # Cryptominer injections (10)
    {"name": "image-optimizer-pro",  "version": "2.1.0","ecosystem": "pypi",
     "type": "cryptominer", "mimics": "pillow",
     "payload": "Install XMRig miner in postinstall; mine to attacker pool"},
    {"name": "ml-accelerate",        "version": "1.3.0","ecosystem": "pypi",
     "type": "cryptominer", "mimics": "numpy/scipy",
     "payload": "GPU cryptomining using CUDA when idle cycles detected"},
    {"name": "data-compress-fast",   "version": "0.8.0","ecosystem": "pypi",
     "type": "cryptominer", "mimics": "lz4/zstd",
     "payload": "CPU miner disguised as compression utility"},
    {"name": "pdf-render-engine",    "version": "3.0.1","ecosystem": "npm",
     "type": "cryptominer", "mimics": "pdfkit",
     "payload": "Browser-based cryptominer injected into rendered PDFs"},
    {"name": "color-palette-gen",    "version": "1.2.0","ecosystem": "npm",
     "type": "cryptominer", "mimics": "color utilities",
     "payload": "Web worker mining JavaScript injected into package"},
    {"name": "cache-optimizer",      "version": "2.0.5","ecosystem": "pypi",
     "type": "cryptominer", "mimics": "cachetools",
     "payload": "Uses 'cache warm-up' thread as cover for CPU mining"},
    {"name": "fast-json-parser",     "version": "1.0.6","ecosystem": "npm",
     "type": "cryptominer", "mimics": "fast-json-stringify",
     "payload": "Monero mining in worker thread, throttled to 30% CPU"},
    {"name": "network-monitor-lite", "version": "0.3.0","ecosystem": "pypi",
     "type": "cryptominer", "mimics": "psutil",
     "payload": "Uses 'network polling' cover for sustained CPU hashing"},
    {"name": "font-loader-utils",    "version": "1.1.3","ecosystem": "npm",
     "type": "cryptominer", "mimics": "webfontloader",
     "payload": "Loads mining WASM module under guise of font optimization"},
    {"name": "video-thumbnail-gen",  "version": "0.5.0","ecosystem": "pypi",
     "type": "cryptominer", "mimics": "opencv-python",
     "payload": "Frame extraction disguises GPU cryptomining operations"},
]

# Services that are anomalous
ANOMALOUS_SERVICES = {"svc_03", "svc_17", "svc_42"}

def pick_compromised_for_service(svc_name):
    """Return 1–2 compromised package names for anomalous services."""
    if svc_name == "svc_03":
        return ["requets", "internal-auth-lib"]
    elif svc_name == "svc_17":
        return ["numpyy", "celery-backdoor", "cryptominer_pkg:image-optimizer-pro"]
    elif svc_name == "svc_42":
        return ["lod4sh", "platform-sdk", "fast-json-parser"]
    return []

# ─── Microservice code templates ─────────────────────────────────────────────

PYTHON_SVC_TEMPLATE = """\
#!/usr/bin/env python3
\"\"\"
{svc_name} — {role} Microservice
\"\"\"
{imports}

app = Flask(__name__)

@app.route("/health")
def health():
    return {{"status": "ok", "service": "{svc_name}"}}

{routes}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port={port})
"""

NODE_ROUTES = {
    "auth":       "POST /login, POST /logout, POST /refresh",
    "api":        "GET /api/v1/items, POST /api/v1/items",
    "data":       "GET /data, POST /data/ingest",
    "analytics":  "GET /metrics, GET /stats/{resource}",
    "notify":     "POST /notify, POST /subscribe",
    "storage":    "GET /files/{id}, POST /files/upload",
    "search":     "GET /search?q={query}, POST /index",
    "payments":   "POST /payment, GET /payment/{id}",
    "users":      "GET /users/{id}, PUT /users/{id}",
    "orders":     "POST /orders, GET /orders/{id}",
}

SERVICE_ROLES = list(NODE_ROUTES.keys()) * 5  # 50 services, cycling through roles

def gen_python_imports(pkgs):
    lines = ["from flask import Flask, request, jsonify"]
    for p in pkgs[:6]:
        mod = p.replace("-", "_").replace(".", "_").split("_")[0]
        lines.append(f"import {mod}")
    return "\n".join(lines)

def gen_routes(role):
    if role == "auth":
        return """\
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    # TODO: validate credentials
    return jsonify({"token": "jwt_placeholder"})

@app.route("/logout", methods=["POST"])
def logout():
    return jsonify({"status": "logged_out"})
"""
    elif role == "data":
        return """\
@app.route("/data", methods=["GET"])
def get_data():
    return jsonify({"records": []})

@app.route("/data/ingest", methods=["POST"])
def ingest():
    payload = request.json
    return jsonify({"ingested": True, "count": len(payload.get("items", []))})
"""
    else:
        return """\
@app.route("/items", methods=["GET"])
def list_items():
    return jsonify({"items": []})

@app.route("/items/<item_id>", methods=["GET"])
def get_item(item_id):
    return jsonify({"id": item_id, "data": {}})
"""

def make_requirements_txt(pkgs):
    lines = []
    for p in pkgs:
        # Assign fake version
        major = random.randint(1, 5)
        minor = random.randint(0, 12)
        patch = random.randint(0, 9)
        lines.append(f"{p}=={major}.{minor}.{patch}")
    return "\n".join(lines) + "\n"

def make_package_json(svc_name, npm_pkgs):
    obj = {
        "name": svc_name,
        "version": "1.0.0",
        "description": f"{svc_name} microservice",
        "main": "index.js",
        "scripts": {"start": "node index.js", "test": "jest"},
        "dependencies": {p: f"^{random.randint(1,5)}.{random.randint(0,12)}.{random.randint(0,9)}" for p in npm_pkgs},
        "devDependencies": {"jest": "^29.0.0", "eslint": "^8.0.0"},
    }
    return json.dumps(obj, indent=2)

def make_sbom(svc_name, all_deps):
    components = []
    for dep in all_deps:
        eco = "pypi" if random.random() < 0.6 else "npm"
        ver = f"{random.randint(1,5)}.{random.randint(0,12)}.{random.randint(0,9)}"
        components.append({
            "type": "library",
            "name": dep,
            "version": ver,
            "purl": f"pkg:{eco}/{dep}@{ver}",
        })
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": svc_name,
                "version": "1.0.0",
            }
        },
        "components": components,
    }

def generate():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "microservices"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "sbom"), exist_ok=True)

    print("[CYBER-P4] Generating dependency graph and microservices...")

    # Build package pool
    # 300 legit pypi + 150 legit npm + 50 compromised = 500
    legit_pypi_pool = LEGIT_PYPI[:300]
    while len(legit_pypi_pool) < 300:
        legit_pypi_pool.append(f"lib-{random.randint(1000,9999)}")
    legit_pypi_pool = legit_pypi_pool[:300]

    legit_npm_pool = LEGIT_NPM[:150]
    while len(legit_npm_pool) < 150:
        legit_npm_pool.append(f"pkg-{random.randint(1000,9999)}")
    legit_npm_pool = legit_npm_pool[:150]

    comp_names = [c["name"] for c in COMPROMISED_PACKAGES]

    all_packages = []
    for p in legit_pypi_pool:
        ver = f"{random.randint(1,5)}.{random.randint(0,12)}.{random.randint(0,9)}"
        all_packages.append({
            "name": p,
            "version": ver,
            "ecosystem": "pypi",
            "description": f"Python package {p}",
        })
    for p in legit_npm_pool:
        ver = f"{random.randint(1,5)}.{random.randint(0,12)}.{random.randint(0,9)}"
        all_packages.append({
            "name": p,
            "version": ver,
            "ecosystem": "npm",
            "description": f"Node.js package {p}",
        })
    for c in COMPROMISED_PACKAGES:
        all_packages.append({
            "name": c["name"],
            "version": c["version"],
            "ecosystem": c["ecosystem"],
            "description": f"{c['type'].title()} package mimicking {c.get('mimics','unknown')}",
        })

    # Build services
    services = []
    edges = []

    for i in range(1, 51):
        svc_name = f"svc_{i:02d}"
        role_idx = (i - 1) % len(SERVICE_ROLES)
        role = SERVICE_ROLES[role_idx]
        port = 8000 + i

        # Pick 5-15 direct legit pypi deps
        n_pypi = random.randint(3, 8)
        n_npm  = random.randint(2, 6)
        direct_pypi = random.sample(legit_pypi_pool, n_pypi)
        direct_npm  = random.sample(legit_npm_pool, n_npm)
        direct_deps = direct_pypi + direct_npm

        # Inject compromised packages for anomalous services
        compromised_injected = []
        if svc_name in ANOMALOUS_SERVICES:
            inj = pick_compromised_for_service(svc_name)
            for cname in inj:
                real_name = cname.replace("cryptominer_pkg:", "")
                compromised_injected.append(real_name)
                if real_name not in direct_deps:
                    direct_deps.append(real_name)

        # Transitive deps: add 5-15 more
        n_trans = random.randint(5, 15)
        available_pool = legit_pypi_pool + legit_npm_pool
        trans = random.sample(available_pool, n_trans)
        all_deps = list(set(direct_deps + trans))

        services.append({
            "name": svc_name,
            "role": role,
            "port": port,
            "direct_deps": direct_deps,
            "all_deps": all_deps,
            "compromised": compromised_injected,
        })

        for dep in direct_deps:
            edges.append({"from": svc_name, "to": dep})

        # Create microservice directory
        svc_dir = os.path.join(OUTPUT_DIR, "microservices", svc_name)
        os.makedirs(svc_dir, exist_ok=True)

        # main.py
        py_imports = gen_python_imports(direct_pypi)
        routes = gen_routes(role)
        main_py = PYTHON_SVC_TEMPLATE.format(
            svc_name=svc_name, role=role.title(),
            imports=py_imports, routes=routes, port=port
        )
        with open(os.path.join(svc_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write(main_py)

        # requirements.txt (python deps only)
        with open(os.path.join(svc_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write(make_requirements_txt(direct_pypi + compromised_injected))

        # package.json
        with open(os.path.join(svc_dir, "package.json"), "w", encoding="utf-8") as f:
            f.write(make_package_json(svc_name, direct_npm))

        # SBOM
        sbom = make_sbom(svc_name, all_deps)
        with open(os.path.join(OUTPUT_DIR, "sbom", f"{svc_name}_sbom.json"), "w", encoding="utf-8") as f:
            json.dump(sbom, f, indent=2)

    print("[CYBER-P4] Microservices and SBOMs generated.")

    # dependency_graph.json
    dg = {
        "packages": all_packages,
        "services": [
            {
                "name": s["name"],
                "role": s["role"],
                "direct_deps": s["direct_deps"],
                "all_deps": s["all_deps"],
            }
            for s in services
        ],
        "edges": edges,
    }
    dg_path = os.path.join(OUTPUT_DIR, "dependency_graph.json")
    with open(dg_path, "w", encoding="utf-8") as f:
        json.dump(dg, f, indent=2)
    print(f"[CYBER-P4] dependency_graph.json written: {dg_path}")

    # HIDDEN_compromised_packages.json
    hcp = {
        "compromised_packages": COMPROMISED_PACKAGES,
        "anomalous_services": [
            {
                "service": s["name"],
                "compromised_deps": s["compromised"],
                "exfil_endpoint": "http://203.0.113.99/exfil",
                "description": (
                    "Service uses one or more compromised packages that perform "
                    "data exfiltration via HTTP POST to 203.0.113.99 (TEST-NET — safe)."
                ),
            }
            for s in services if s["name"] in ANOMALOUS_SERVICES
        ],
        "attack_c2": "203.0.113.99",
        "notes": (
            "203.0.113.99 is in TEST-NET-3 (RFC 5737) and is NOT a real attacker address. "
            "Used for simulation purposes only."
        ),
    }
    hcp_path = os.path.join(OUTPUT_DIR, "HIDDEN_compromised_packages.json")
    with open(hcp_path, "w", encoding="utf-8") as f:
        json.dump(hcp, f, indent=2)
    print(f"[CYBER-P4] HIDDEN_compromised_packages.json written: {hcp_path}")

    # anomaly_report.txt
    anomaly_path = os.path.join(OUTPUT_DIR, "anomaly_report.txt")
    with open(anomaly_path, "w", encoding="utf-8") as f:
        f.write("""\
SUPPLY CHAIN SECURITY ANOMALY REPORT
=====================================
Date: 2024-01-15 03:42:17 UTC
Reported by: Automated SIEM (Rule: OUTBOUND_SUSPICIOUS_POST)

SUMMARY
-------
Our network monitoring systems have flagged unusual outbound HTTP POST requests
originating from within the production Kubernetes cluster. The traffic is directed
to 203.0.113.99 and contains structured data that does not match any known
legitimate service integration.

OBSERVED INDICATORS
-------------------
1. Destination IP: 203.0.113.99
   - Not present in any approved egress whitelist
   - First seen: 2024-01-14 22:10:04 UTC
   - Request frequency: variable (1–10 req/min per source pod)

2. Request Pattern:
   - Method: HTTP POST
   - Paths observed: /exfil, /log, /env, /db, /mongo, /logs
   - Content-Type: application/json
   - Payload structure suggests structured data export (credentials, env vars, DB queries)

3. Source Pods / Services:
   - Multiple microservices appear to be the origin
   - Exact services not yet identified — requires dependency analysis

4. Timeline:
   - 2024-01-14 22:10 UTC: First POST to 203.0.113.99/exfil
   - 2024-01-14 22:15 UTC: POST to 203.0.113.99/log observed
   - 2024-01-14 23:00 UTC: Sustained traffic from 3 distinct service IPs
   - 2024-01-15 03:30 UTC: Automated rule triggered, incident opened

HYPOTHESIS
----------
A software supply chain attack may have introduced malicious packages into
one or more microservices' dependency trees. The malicious code activates
on service startup and begins exfiltrating sensitive data.

REQUESTED ACTIONS
-----------------
1. Identify which microservices are making connections to 203.0.113.99
2. Determine which dependency packages contain malicious code
3. Classify each malicious package by attack type:
   - Typosquatting (look-alike package names)
   - Dependency confusion (internal package names on public registries)
   - Backdoored packages (legitimate packages with injected code)
   - Cryptominer injections (packages with mining code in install hooks)
4. Provide a remediation plan with affected service list and replacement packages

ARTEFACTS
---------
- dependency_graph.json: Full dependency graph for all 50 microservices (500 packages)
- microservices/: Source code and dependency manifests for each service
- sbom/: Software Bill of Materials (CycloneDX 1.4 format) for each service

PRIORITY: CRITICAL
ESCALATION: CISO + DevSecOps Lead notified
""")
    print(f"[CYBER-P4] anomaly_report.txt written: {anomaly_path}")

    # README.md
    readme_path = os.path.join(OUTPUT_DIR, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("""\
# CYBER-P4: Supply Chain Sentinel

## Overview
A sophisticated supply chain attack has been detected in the production environment.
Malicious packages have been introduced into the dependency trees of several microservices,
causing data exfiltration to an external command-and-control server.

Your mission: identify all compromised packages, determine which microservices are
affected, classify the attack vectors, and produce a remediation report.

## Objective
1. Identify all 50 compromised packages across the 500-package dependency graph
2. Determine which of the 50 microservices are affected (3 are known to be compromised)
3. Classify each malicious package by attack type
4. Explain the payload/behavior of each malicious package
5. Propose specific remediation steps

## Files
| Path                                   | Description                                  |
|----------------------------------------|----------------------------------------------|
| `anomaly_report.txt`                   | Initial incident report given to participants |
| `dependency_graph.json`                | Full dependency graph (500 pkgs, 50 services) |
| `microservices/svc_NN/`                | Source code for each of 50 microservices      |
| `microservices/svc_NN/main.py`         | Service implementation                        |
| `microservices/svc_NN/requirements.txt`| Python dependencies                           |
| `microservices/svc_NN/package.json`    | Node.js dependencies                          |
| `sbom/svc_NN_sbom.json`               | CycloneDX 1.4 SBOM per service                |
| `HIDDEN_compromised_packages.json`     | **Hidden.** Ground truth for scoring.         |
| `README.md`                            | This file                                     |

## Scoring

| Task                                         | Points |
|----------------------------------------------|--------|
| Identify each compromised package (50 total) | 1 pt each (50 pts) |
| Correctly classify attack type               | 1 pt each (50 pts) |
| Identify the 3 affected services             | 10 pts each (30 pts) |
| Describe payload/behavior accurately         | 0.5 pt each (25 pts) |
| Complete remediation plan                    | up to 20 pts |
| **Total**                                    | **175 pts** |

## Attack Taxonomy

### Typosquatting (10 packages)
Packages with names nearly identical to popular libraries. Installed accidentally
via typos in requirements files. Example: `requets` instead of `requests`.

### Dependency Confusion (10 packages)
Internal package names (e.g., `internal-auth-lib`) that an attacker published
to public registries. When the build system resolves dependencies, it may
prefer the public (malicious) version over the private internal one.

### Backdoored Packages (20 packages)
Legitimate-looking packages with injected malicious code. These simulate
maintainer account compromise scenarios where a popular package is updated
with hidden functionality.

### Cryptominer Injections (10 packages)
Packages with cryptocurrency mining code in install hooks (`setup.py`,
`postinstall` scripts). The mining runs as a background process.

## Investigation Tips
- Start with `anomaly_report.txt` to understand the network indicators
- Cross-reference `dependency_graph.json` with `sbom/` files to trace which
  services depend on which packages
- Look for packages with suspicious naming patterns in `requirements.txt` files
- The C2 IP address is 203.0.113.99 (RFC 5737 TEST-NET-3 — safe for simulation)
- Three specific services (svc_03, svc_17, svc_42) are confirmed to be making
  outbound connections; trace their dependencies to find the malicious packages

## Output Format
Submit a JSON report:
```json
{
  "compromised_packages": [
    {
      "name": "requets",
      "attack_type": "typosquatting",
      "mimics": "requests",
      "payload": "...",
      "affected_services": ["svc_03"]
    }
  ],
  "affected_services": ["svc_03", "svc_17", "svc_42"],
  "remediation": {
    "immediate": ["..."],
    "long_term": ["..."]
  }
}
```
""")
    print(f"[CYBER-P4] README.md written: {readme_path}")
    print("[CYBER-P4] All files generated successfully.")


if __name__ == "__main__":
    generate()
    print("[CYBER-P4] Done.")
