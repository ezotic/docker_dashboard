from flask import Flask, render_template, jsonify, Response, request
import docker_client as dc
import os
import sys
import json
import re
import secrets

# Python version check
if sys.version_info < (3, 9):
    print(f"Error: Python 3.9+ required (you have {sys.version_info.major}.{sys.version_info.minor})")
    sys.exit(1)

app = Flask(__name__)

# Configuration
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
HOSTS_FILE = os.getenv("HOSTS_FILE", os.path.join(os.path.dirname(__file__), "hosts.json"))
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "changeme")
CSRF_TOKEN = secrets.token_urlsafe(32)

_DEFAULT_HOSTS = {"hosts": [
    {"id": "local", "name": "Local", "url": "unix:///var/run/docker.sock", "is_local": True}
]}


def _auth_challenge():
    return Response(
        "Authentication required\n",
        401,
        {"WWW-Authenticate": 'Basic realm="Docker Dashboard"'},
    )


@app.before_request
def require_basic_auth():
    auth = request.authorization
    if not auth:
        return _auth_challenge()
    username_ok = secrets.compare_digest(auth.username or "", DASHBOARD_USERNAME)
    password_ok = secrets.compare_digest(auth.password or "", DASHBOARD_PASSWORD)
    if not username_ok or not password_ok:
        return _auth_challenge()
    return None


@app.before_request
def require_csrf_token():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    token = request.headers.get("X-CSRF-Token", "")
    if not secrets.compare_digest(token, CSRF_TOKEN):
        return jsonify({"error": "Invalid CSRF token"}), 403
    return None


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": CSRF_TOKEN}


# ── Host helpers ──────────────────────────────────────────────────────────────

def _load_hosts() -> dict:
    if not os.path.exists(HOSTS_FILE) or os.path.isdir(HOSTS_FILE):
        if os.path.isdir(HOSTS_FILE):
            os.rmdir(HOSTS_FILE)
        _save_hosts(_DEFAULT_HOSTS)
        return _DEFAULT_HOSTS
    try:
        with open(HOSTS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        _save_hosts(_DEFAULT_HOSTS)
        return _DEFAULT_HOSTS


def _save_hosts(data: dict) -> None:
    with open(HOSTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _get_host_by_id(host_id: str) -> dict | None:
    for h in _load_hosts()["hosts"]:
        if h["id"] == host_id:
            return h
    return None


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower().strip()).strip("-")


def _resolve_client():
    """Read ?host= from request, return (host_dict, docker_client).
    Falls back to local host if param is missing. Returns (None, None) if host not found."""
    host_id = request.args.get("host", "local")
    host = _get_host_by_id(host_id)
    if not host:
        return None, None
    return host, dc.get_client(host["id"], host["url"])


# ── Page routes ──────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    host, client = _resolve_client()
    if host is None:
        host = _get_host_by_id("local")
        client = dc.get_client("local", host["url"])
    stats = dc.get_dashboard_stats(client)
    return render_template("dashboard.html", stats=stats,
                           connected=stats.get("connected", False),
                           active_host=host)


@app.route("/containers")
def containers():
    host, client = _resolve_client()
    if host is None:
        host = _get_host_by_id("local")
        client = dc.get_client("local", host["url"])
    items = dc.list_containers(client) if client else {"error": "Unreachable"}
    connected = not isinstance(items, dict)
    return render_template("containers.html", containers=items if connected else [],
                           connected=connected, active_host=host)


@app.route("/images")
def images():
    host, client = _resolve_client()
    if host is None:
        host = _get_host_by_id("local")
        client = dc.get_client("local", host["url"])
    items = dc.list_images(client) if client else {"error": "Unreachable"}
    connected = not isinstance(items, dict)
    return render_template("images.html", images=items if connected else [],
                           connected=connected, active_host=host)


@app.route("/volumes")
def volumes():
    host, client = _resolve_client()
    if host is None:
        host = _get_host_by_id("local")
        client = dc.get_client("local", host["url"])
    items = dc.list_volumes(client) if client else {"error": "Unreachable"}
    connected = not isinstance(items, dict)
    return render_template("volumes.html", volumes=items if connected else [],
                           connected=connected, active_host=host)


@app.route("/networks")
def networks():
    host, client = _resolve_client()
    if host is None:
        host = _get_host_by_id("local")
        client = dc.get_client("local", host["url"])
    items = dc.list_networks(client) if client else {"error": "Unreachable"}
    connected = not isinstance(items, dict)
    return render_template("networks.html", networks=items if connected else [],
                           connected=connected, active_host=host)


@app.route("/containers/<container_id>/logs")
def container_logs(container_id):
    host, client = _resolve_client()
    if host is None:
        host = _get_host_by_id("local")
        client = dc.get_client("local", host["url"])
    name = dc.get_container_name(client, container_id) if client else container_id[:12]
    return render_template("logs.html", container_id=container_id,
                           container_name=name, connected=client is not None,
                           active_host=host)


@app.route("/hosts")
def hosts_page():
    return render_template("hosts.html", active_host={"id": "local", "name": "Local"}, connected=True)


@app.route("/graphs")
def graphs():
    host, client = _resolve_client()
    if host is None:
        host = _get_host_by_id("local")
        client = dc.get_client("local", host["url"])
    return render_template("graphs.html", connected=client is not None, active_host=host)


# ── Host API ──────────────────────────────────────────────────────────────────

@app.route("/api/hosts")
def api_hosts():
    data = _load_hosts()
    result = []
    for h in data["hosts"]:
        status = dc.check_host_status(h["id"], h["url"])
        result.append({**h, **status})
    return jsonify(result)


@app.route("/api/hosts", methods=["POST"])
def api_host_add():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    url = (body.get("url") or "").strip()
    if not name or not url:
        return jsonify({"error": "name and url are required"}), 400
    data = _load_hosts()
    base_id = _slugify(name) or "host"
    new_id, counter = base_id, 2
    existing_ids = {h["id"] for h in data["hosts"]}
    while new_id in existing_ids:
        new_id = f"{base_id}-{counter}"
        counter += 1
    data["hosts"].append({"id": new_id, "name": name, "url": url, "is_local": False})
    _save_hosts(data)
    return jsonify({"id": new_id, "name": name, "url": url}), 201


@app.route("/api/hosts/<host_id>", methods=["DELETE"])
def api_host_delete(host_id):
    if host_id == "local":
        return jsonify({"error": "Cannot remove the local host"}), 400
    data = _load_hosts()
    original_len = len(data["hosts"])
    data["hosts"] = [h for h in data["hosts"] if h["id"] != host_id]
    if len(data["hosts"]) == original_len:
        return jsonify({"error": "Host not found"}), 404
    dc.evict_client(host_id)
    _save_hosts(data)
    return jsonify({"ok": True})


# ── Container API ─────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
def api_dashboard():
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable", "connected": False}), 503
    return jsonify(dc.get_dashboard_stats(client))


@app.route("/api/containers")
def api_containers():
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return jsonify(dc.list_containers(client))


@app.route("/api/containers/<container_id>/start", methods=["POST"])
def api_container_start(container_id):
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return _action_response(dc.container_action(client, container_id, "start"))


@app.route("/api/containers/<container_id>/stop", methods=["POST"])
def api_container_stop(container_id):
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return _action_response(dc.container_action(client, container_id, "stop"))


@app.route("/api/containers/<container_id>/restart", methods=["POST"])
def api_container_restart(container_id):
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return _action_response(dc.container_action(client, container_id, "restart"))


@app.route("/api/containers/<container_id>", methods=["DELETE"])
def api_container_remove(container_id):
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return _action_response(dc.remove_container(client, container_id))


@app.route("/api/containers/<container_id>/stats")
def api_container_stats(container_id):
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return _action_response(dc.get_container_stats(client, container_id))


@app.route("/api/containers/<container_id>/logs/stream")
def api_container_logs_stream(container_id):
    host, client = _resolve_client()
    if client is None:
        def _err():
            yield "data: [host not found or unreachable]\n\n"
        return Response(_err(), mimetype="text/event-stream",
                        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    def generate(c):
        try:
            for line in dc.stream_container_logs(c, container_id):
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                if text:
                    yield f"data: {text}\n\n"
        except Exception as e:
            yield f"data: [stream error: {e}]\n\n"

    return Response(
        generate(client),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


# ── Image API ─────────────────────────────────────────────────────────────────

@app.route("/api/images")
def api_images():
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return jsonify(dc.list_images(client))


@app.route("/api/images/<path:image_id>/inspect")
def api_image_inspect(image_id):
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return _action_response(dc.inspect_image(client, image_id))


@app.route("/api/images/<path:image_id>", methods=["DELETE"])
def api_image_remove(image_id):
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return _action_response(dc.remove_image(client, image_id))


# ── Volume API ────────────────────────────────────────────────────────────────

@app.route("/api/volumes")
def api_volumes():
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return jsonify(dc.list_volumes(client))


@app.route("/api/volumes/<path:name>", methods=["DELETE"])
def api_volume_remove(name):
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return _action_response(dc.remove_volume(client, name))


# ── Network API ───────────────────────────────────────────────────────────────

@app.route("/api/networks")
def api_networks():
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return jsonify(dc.list_networks(client))


# ── Graphs API ────────────────────────────────────────────────────────────────

@app.route("/api/graphs/stats")
def api_graphs_stats():
    host, client = _resolve_client()
    if client is None:
        return jsonify({"error": "Host not found or unreachable"}), 503
    return jsonify(dc.get_all_container_stats(client))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _action_response(result):
    if isinstance(result, tuple):
        data, status = result
        return jsonify(data), status
    return jsonify(result)


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True)
