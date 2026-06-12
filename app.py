from flask import Flask, render_template, jsonify, Response, abort
import docker_client as dc
import os
import sys

# Python version check
if sys.version_info < (3, 9):
    print(f"Error: Python 3.9+ required (you have {sys.version_info.major}.{sys.version_info.minor})")
    sys.exit(1)

app = Flask(__name__)

# Configuration
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))


# ── Page routes ──────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    stats = dc.get_dashboard_stats()
    return render_template("dashboard.html", stats=stats, connected=stats.get("connected", False))


@app.route("/containers")
def containers():
    items = dc.list_containers()
    connected = not isinstance(items, dict)
    return render_template("containers.html", containers=items if connected else [], connected=connected)


@app.route("/images")
def images():
    items = dc.list_images()
    connected = not isinstance(items, dict)
    return render_template("images.html", images=items if connected else [], connected=connected)


@app.route("/volumes")
def volumes():
    items = dc.list_volumes()
    connected = not isinstance(items, dict)
    return render_template("volumes.html", volumes=items if connected else [], connected=connected)


@app.route("/networks")
def networks():
    items = dc.list_networks()
    connected = not isinstance(items, dict)
    return render_template("networks.html", networks=items if connected else [], connected=connected)


@app.route("/containers/<container_id>/logs")
def container_logs(container_id):
    name = dc.get_container_name(container_id)
    return render_template("logs.html", container_id=container_id, container_name=name, connected=True)


# ── API routes ────────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(dc.get_dashboard_stats())


@app.route("/api/containers")
def api_containers():
    return jsonify(dc.list_containers())


@app.route("/api/containers/<container_id>/start", methods=["POST"])
def api_container_start(container_id):
    result = dc.container_action(container_id, "start")
    return _action_response(result)


@app.route("/api/containers/<container_id>/stop", methods=["POST"])
def api_container_stop(container_id):
    result = dc.container_action(container_id, "stop")
    return _action_response(result)


@app.route("/api/containers/<container_id>/restart", methods=["POST"])
def api_container_restart(container_id):
    result = dc.container_action(container_id, "restart")
    return _action_response(result)


@app.route("/api/containers/<container_id>", methods=["DELETE"])
def api_container_remove(container_id):
    result = dc.remove_container(container_id)
    return _action_response(result)


@app.route("/api/containers/<container_id>/stats")
def api_container_stats(container_id):
    result = dc.get_container_stats(container_id)
    return _action_response(result)


@app.route("/api/containers/<container_id>/logs/stream")
def api_container_logs_stream(container_id):
    def generate():
        try:
            for line in dc.stream_container_logs(container_id):
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                if text:
                    yield f"data: {text}\n\n"
        except Exception as e:
            yield f"data: [stream error: {e}]\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.route("/api/images")
def api_images():
    return jsonify(dc.list_images())


@app.route("/api/images/<path:image_id>/inspect")
def api_image_inspect(image_id):
    result = dc.inspect_image(image_id)
    return _action_response(result)


@app.route("/api/images/<path:image_id>", methods=["DELETE"])
def api_image_remove(image_id):
    result = dc.remove_image(image_id)
    return _action_response(result)


@app.route("/api/volumes")
def api_volumes():
    return jsonify(dc.list_volumes())


@app.route("/api/volumes/<path:name>", methods=["DELETE"])
def api_volume_remove(name):
    result = dc.remove_volume(name)
    return _action_response(result)


@app.route("/api/networks")
def api_networks():
    return jsonify(dc.list_networks())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _action_response(result):
    if isinstance(result, tuple):
        data, status = result
        return jsonify(data), status
    return jsonify(result)


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, threaded=True)
