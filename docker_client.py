import docker
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import os
import platform

_clients: dict = {}
_client_errors: dict = {}
_lock = threading.Lock()


def get_client(host_id: str, url: str):
    with _lock:
        if host_id not in _clients:
            _clients[host_id] = _create_client(host_id, url)
        return _clients[host_id]


def evict_client(host_id: str) -> None:
    with _lock:
        _clients.pop(host_id, None)
        _client_errors.pop(host_id, None)


def check_host_status(host_id: str, url: str) -> dict:
    c = get_client(host_id, url)
    if c is None:
        return {"connected": False, "error": _client_errors.get(host_id), "version": None}
    try:
        info = c.version()
        return {"connected": True, "error": None, "version": info.get("Version")}
    except Exception as e:
        evict_client(host_id)
        return {"connected": False, "error": str(e), "version": None}


def _create_client(host_id: str, url: str):
    try:
        if host_id == "local" or url.startswith("unix://"):
            c = docker.from_env()
        else:
            c = docker.DockerClient(base_url=url, timeout=5)
        c.ping()
        return c
    except Exception as e:
        system = platform.system()
        docker_host = os.getenv("DOCKER_HOST", "not set")
        error_msg = str(e)
        if host_id == "local":
            if system == "Windows" and "npipe" not in docker_host.lower():
                _client_errors[host_id] = f"{error_msg}. Windows users: ensure Docker Desktop is running."
            elif system in ("Linux", "Darwin") and "/var/run/docker.sock" not in error_msg:
                _client_errors[host_id] = f"{error_msg}. {system} users: ensure Docker daemon is running."
            else:
                _client_errors[host_id] = f"{error_msg}. DOCKER_HOST={docker_host}"
        else:
            _client_errors[host_id] = error_msg
        return None


def _fmt_size(bytes_val):
    if bytes_val is None:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


def _fmt_uptime(started_at_str):
    if not started_at_str or started_at_str.startswith("0001"):
        return "—"
    try:
        started = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - started
        s = int(delta.total_seconds())
        if s < 60:
            return f"{s}s"
        if s < 3600:
            return f"{s // 60}m {s % 60}s"
        if s < 86400:
            return f"{s // 3600}h {(s % 3600) // 60}m"
        return f"{s // 86400}d {(s % 86400) // 3600}h"
    except Exception:
        return "—"


def get_dashboard_stats(client) -> dict:
    if client is None:
        return {"error": "Docker client unavailable", "connected": False}
    try:
        containers = client.containers.list(all=True)
        running = sum(1 for c in containers if c.status == "running")
        stopped = len(containers) - running
        images = client.images.list()
        volumes = client.volumes.list()
        df = client.df()
        disk = {
            "images": _fmt_size(sum(i.get("Size", 0) for i in df.get("Images", []))),
            "containers": _fmt_size(sum(c.get("SizeRootFs", 0) for c in df.get("Containers", []))),
            "volumes": _fmt_size(sum(v.get("UsageData", {}).get("Size", 0) for v in df.get("Volumes", []))),
            "build_cache": _fmt_size(sum(b.get("Size", 0) for b in df.get("BuildCache", []))),
        }
        return {
            "running": running,
            "stopped": stopped,
            "total": len(containers),
            "images": len(images),
            "volumes": len(volumes),
            "disk": disk,
            "connected": True,
        }
    except Exception as e:
        return {"error": str(e), "connected": False}


def list_containers(client) -> list | dict:
    try:
        containers = client.containers.list(all=True)
        result = []
        for c in containers:
            ports = []
            for container_port, bindings in (c.ports or {}).items():
                if bindings:
                    for b in bindings:
                        ports.append(f"{b['HostPort']}→{container_port}")
                else:
                    ports.append(container_port)
            tags = c.image.tags
            image_name = tags[0] if tags else c.image.short_id
            result.append({
                "id": c.id,
                "short_id": c.short_id,
                "name": c.name,
                "image": image_name,
                "status": c.status,
                "ports": ", ".join(ports) if ports else "—",
                "uptime": _fmt_uptime(c.attrs.get("State", {}).get("StartedAt", "")),
            })
        return result
    except Exception as e:
        return {"error": str(e)}


def container_action(client, container_id, action):
    try:
        c = client.containers.get(container_id)
        if action == "start":
            c.start()
        elif action == "stop":
            c.stop(timeout=10)
        elif action == "restart":
            c.restart(timeout=10)
        else:
            return {"error": f"Unknown action: {action}"}
        return {"ok": True}
    except docker.errors.NotFound:
        return {"error": "Container not found"}, 404
    except docker.errors.APIError as e:
        return {"error": str(e)}, 500


def remove_container(client, container_id):
    try:
        c = client.containers.get(container_id)
        c.remove(force=True)
        return {"ok": True}
    except docker.errors.NotFound:
        return {"error": "Container not found"}, 404
    except docker.errors.APIError as e:
        return {"error": str(e)}, 500


def get_container_stats(client, container_id):
    try:
        c = client.containers.get(container_id)
        if c.status != "running":
            return {"cpu_percent": 0, "mem_usage": "—", "mem_limit": "—", "mem_percent": 0}
        stats = c.stats(stream=False)
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        num_cpus = stats["cpu_stats"].get("online_cpus") or len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [1]))
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100 if system_delta > 0 else 0
        mem = stats["memory_stats"]
        mem_usage = mem.get("usage", 0)
        mem_limit = mem.get("limit", 0)
        mem_percent = (mem_usage / mem_limit * 100) if mem_limit > 0 else 0
        networks = stats.get("networks", {})
        net_rx = sum(v.get("rx_bytes", 0) for v in networks.values())
        net_tx = sum(v.get("tx_bytes", 0) for v in networks.values())
        blkio = stats.get("blkio_stats", {}).get("io_service_bytes_recursive") or []
        blk_read = sum(e.get("value", 0) for e in blkio if e.get("op") == "Read")
        blk_write = sum(e.get("value", 0) for e in blkio if e.get("op") == "Write")
        return {
            "cpu_percent": round(cpu_percent, 1),
            "mem_usage": _fmt_size(mem_usage),
            "mem_limit": _fmt_size(mem_limit),
            "mem_percent": round(mem_percent, 1),
            "net_rx_bytes": net_rx,
            "net_tx_bytes": net_tx,
            "blk_read_bytes": blk_read,
            "blk_write_bytes": blk_write,
        }
    except docker.errors.NotFound:
        return {"error": "Container not found"}, 404
    except Exception:
        return {"cpu_percent": 0, "mem_usage": "—", "mem_limit": "—", "mem_percent": 0}


def get_all_container_stats(client) -> list | dict:
    try:
        containers = client.containers.list(filters={"status": "running"})
        if not containers:
            return []
        def fetch(c):
            s = get_container_stats(client, c.id)
            if isinstance(s, tuple):
                s = s[0]
            return {"id": c.id, "short_id": c.short_id, "name": c.name, **s}
        with ThreadPoolExecutor(max_workers=min(10, len(containers))) as ex:
            futures = [ex.submit(fetch, c) for c in containers]
            results = []
            for f in as_completed(futures):
                try:
                    results.append(f.result())
                except Exception:
                    pass
        return sorted(results, key=lambda x: x["name"])
    except Exception as e:
        return {"error": str(e)}


def stream_container_logs(client, container_id, tail=200):
    c = client.containers.get(container_id)
    return c.logs(stream=True, follow=True, tail=tail, timestamps=True)


def get_container_name(client, container_id):
    try:
        return client.containers.get(container_id).name
    except Exception:
        return container_id[:12]


def list_images(client) -> list | dict:
    try:
        images = client.images.list()
        result = []
        for img in images:
            tags = img.tags or ["<none>:<none>"]
            created_raw = img.attrs.get("Created", "")
            try:
                created = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except Exception:
                created = "—"
            result.append({
                "id": img.id,
                "short_id": img.short_id.replace("sha256:", ""),
                "tags": tags,
                "size": _fmt_size(img.attrs.get("Size", 0)),
                "created": created,
            })
        return result
    except Exception as e:
        return {"error": str(e)}


def inspect_image(client, image_id):
    try:
        return client.images.get(image_id).attrs
    except docker.errors.NotFound:
        return {"error": "Image not found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500


def remove_image(client, image_id):
    try:
        client.images.remove(image_id, force=True)
        return {"ok": True}
    except docker.errors.NotFound:
        return {"error": "Image not found"}, 404
    except docker.errors.APIError as e:
        return {"error": str(e)}, 409


def list_volumes(client) -> list | dict:
    try:
        vols = client.volumes.list()
        result = []
        for v in vols:
            result.append({
                "name": v.name,
                "driver": v.attrs.get("Driver", "—"),
                "mountpoint": v.attrs.get("Mountpoint", "—"),
                "labels": v.attrs.get("Labels") or {},
            })
        return result
    except Exception as e:
        return {"error": str(e)}


def remove_volume(client, name):
    try:
        v = client.volumes.get(name)
        v.remove()
        return {"ok": True}
    except docker.errors.NotFound:
        return {"error": "Volume not found"}, 404
    except docker.errors.APIError as e:
        return {"error": str(e)}, 409


def list_networks(client) -> list | dict:
    try:
        nets = client.networks.list()
        result = []
        for n in nets:
            ipam = n.attrs.get("IPAM", {}).get("Config") or []
            subnet = ipam[0].get("Subnet", "—") if ipam else "—"
            result.append({
                "id": n.short_id,
                "name": n.name,
                "driver": n.attrs.get("Driver", "—"),
                "scope": n.attrs.get("Scope", "—"),
                "subnet": subnet,
            })
        return result
    except Exception as e:
        return {"error": str(e)}


def is_connected() -> bool:
    status = check_host_status("local", "local")
    return status["connected"]
