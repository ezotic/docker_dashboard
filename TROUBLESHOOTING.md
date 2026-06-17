# Troubleshooting Guide - Linux

## Docker Compose Issues

### Container fails to start with "Cannot connect to Docker daemon"

**Solutions:**

1. Ensure Docker daemon is running:
   ```bash
   sudo systemctl start docker
   sudo systemctl status docker  # Verify it's running
   ```

2. Add your user to the docker group:
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker  # Apply group changes immediately
   ```

3. Verify Docker socket exists and has correct permissions:
   ```bash
   ls -l /var/run/docker.sock
   ```

4. Test Docker connection:
   ```bash
   docker ps
   ```

5. Restart the dashboard:
   ```bash
   docker-compose down
   docker-compose up --build
   ```

### Permission denied while trying to connect to Docker daemon

**Solution:** Add your user to the docker group:
```bash
sudo usermod -aG docker $USER
newgrp docker
docker-compose down
docker-compose up --build
```

### Port 5000 already in use

**Find and kill the process:**
```bash
# Find process using port 5000
lsof -i :5000

# Kill process (replace PID with actual process ID)
kill -9 <PID>
```

**Or use a different port:**
```bash
# Edit .env
FLASK_PORT=5001

# Then restart
docker-compose down
docker-compose up --build
```

## Docker Daemon Issues

### Docker daemon won't start

**Check logs:**
```bash
sudo systemctl status docker
sudo journalctl -u docker -n 50
```

**Restart Docker:**
```bash
sudo systemctl restart docker
```

### "Cannot get Docker socket location" error

1. Verify socket exists:
   ```bash
   ls -l /var/run/docker.sock
   ```

2. Check Docker is running:
   ```bash
   sudo systemctl status docker
   ```

3. If socket doesn't exist, restart Docker:
   ```bash
   sudo systemctl restart docker
   ```

## Application Issues

### Dashboard shows "Docker connection error"

1. Verify Docker is running:
   ```bash
   docker ps
   ```

2. Check socket permissions:
   ```bash
   ls -l /var/run/docker.sock
   ```

3. Test Docker connection directly:
   ```bash
   python3 -c "import docker; print(docker.from_env().ping())"
   ```

4. If that fails, check if you need to be in docker group:
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

### Containers page won't load

1. Verify Docker API is responding:
   ```bash
   docker ps
   docker inspect <any-container-id>
   ```

2. Check container logs:
   ```bash
   docker-compose logs docker-dashboard
   ```

3. Restart the dashboard:
   ```bash
   docker-compose restart
   ```

### Logs not streaming in real-time

1. Verify container is running:
   ```bash
   docker ps | grep docker-dashboard
   ```

2. Check Docker API socket:
   ```bash
   docker logs docker-dashboard
   ```

3. Restart the dashboard container:
   ```bash
   docker-compose down
   docker-compose up --build
   ```

## Local Python Development Issues

### "Cannot connect to Docker daemon" in local mode

1. Ensure Docker is running:
   ```bash
   sudo systemctl start docker
   ```

2. Add yourself to docker group:
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. Test Docker connection:
   ```bash
   docker ps
   ```

### Python version too old

Check your Python version:
```bash
python3 --version
```

Requires Python 3.9+. Install if needed:
```bash
sudo apt-get install python3.9 python3-pip
```

### Module import errors

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

## Complete Linux Setup Verification

Verify your system is properly configured:

```bash
#!/bin/bash
echo "=== Docker Installation ==="
docker --version
docker-compose --version

echo ""
echo "=== Docker Service ==="
sudo systemctl status docker

echo ""
echo "=== Docker Socket ==="
ls -l /var/run/docker.sock

echo ""
echo "=== User Groups ==="
groups $USER

echo ""
echo "=== Docker Connection Test ==="
docker ps

echo ""
echo "=== Python ==="
python3 --version

echo ""
echo "=== Docker Daemon Running ==="
ps aux | grep -i docker | grep -v grep
```

Save as `check-setup.sh`, run with `bash check-setup.sh`

## Remote Host (Raspberry Pi) Issues

### Raspberry Pi not appearing in the host dropdown

The host dropdown is populated from `hosts.json`. If your Pi is missing, it has not been added yet.

**To add it:**
1. Open the dashboard and go to **Hosts** in the sidebar
2. Enter a name (e.g. `Raspberry Pi`) and the Docker TCP URL
3. Click **Add**

URL format:
- Without TLS: `tcp://192.168.x.x:2375`
- With TLS: `tcp://192.168.x.x:2376`

---

### Docker on the Raspberry Pi is not listening on TCP

By default Docker only listens on the Unix socket. You must explicitly enable the TCP listener.

**Option 1 — `daemon.json` (recommended):**

Edit (or create) `/etc/docker/daemon.json` on the Pi:
```json
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}
```

Then reload and restart Docker:
```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

> If Docker fails to start after this change, check for a conflicting `-H` flag in the systemd unit:
> ```bash
> sudo systemctl edit docker
> # Add under [Service]:
> # ExecStart=
> # ExecStart=/usr/bin/dockerd
> ```

**Option 2 — systemd override only:**
```bash
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/override.conf <<EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:2375
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

**Verify TCP is listening on the Pi:**
```bash
ss -tlnp | grep 2375
# Or test from the dashboard host:
curl http://192.168.x.x:2375/version
```

---

### Host shows "offline" / red badge after adding it

The dashboard tried to connect but got no response. Check:

1. **Is Docker running on the Pi?**
   ```bash
   sudo systemctl status docker
   ```

2. **Is port 2375 open?** Check firewall on the Pi:
   ```bash
   sudo ufw status
   # If UFW is active and blocking:
   sudo ufw allow 2375/tcp
   ```

3. **Can the dashboard host reach the Pi?**
   ```bash
   # From the machine running the dashboard:
   curl http://192.168.x.x:2375/version
   ```

4. **Check the dashboard logs for the actual error:**
   ```bash
   docker-compose logs docker-dashboard
   ```

---

### Security warning — unencrypted TCP

Port 2375 is **unauthenticated and unencrypted**. Anyone on the network with access to that port has full root-level control of Docker on the Pi.

- Only expose port 2375 on a **trusted private network** (home LAN, VPN)
- For internet-facing or shared networks, configure **Docker with TLS** on port 2376 and use a `tcp://` URL with your client certificate paths

---

## Getting Help

If you continue to experience issues:

1. Check Docker logs:
   ```bash
   sudo journalctl -u docker -n 100
   docker-compose logs docker-dashboard
   ```

2. Verify system requirements:
   - Docker Engine installed and running
   - Python 3.9+ (if running locally)
   - User in docker group (for non-root access)
   - Port 5000 available (or configured differently)

3. Try a clean restart:
   ```bash
   docker-compose down
   docker system prune
   docker-compose up --build
   ```
