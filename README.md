# Docker Dashboard

A lightweight, web-based dashboard for managing and monitoring Docker containers, images, volumes, and networks. Built with Flask and the Docker API, this application provides real-time insights into your Docker environment with an intuitive user interface.

## Overview

The Docker Dashboard is a Flask-based web application that connects directly to the Docker daemon via the Docker API. It provides a centralized interface to view and manage Docker resources without needing to use the command line.

## Features

### Dashboard
- **Real-time Statistics**: View counts of running/stopped containers, images, volumes, and networks
- **Disk Usage Analysis**: Monitor disk space consumed by images, containers, volumes, and build cache
- **Connection Status**: Visual indicator showing Docker daemon connection status

### Containers Management
- **List View**: View all containers (running and stopped) with status, image names, and port mappings
- **Container Actions**: Start, stop, restart, and remove containers
- **Real-time Stats**: Monitor CPU and memory usage for running containers
- **Live Logs**: Stream container logs in real-time with timestamps
- **Container Information**: View uptime, ports, and image details

### Images Management
- **Image Listing**: Browse all Docker images with tags, size, and creation date
- **Image Inspection**: View detailed image metadata and attributes
- **Image Removal**: Delete unused images to free up disk space

### Volumes Management
- **Volume Listing**: View all Docker volumes with driver information and mount points
- **Volume Labels**: Display custom labels assigned to volumes
- **Volume Removal**: Remove volumes and reclaim storage

### Networks Management
- **Network Listing**: View all Docker networks with driver and scope information
- **Network Details**: Display subnet information and network configuration
- **Network Types**: Support for all Docker network drivers (bridge, overlay, host, etc.)

## Requirements

### System Requirements
- **Docker Engine**: Must be running and accessible (20.10+)
- **Python 3.9+**: For running the Flask application (if running locally)
- **Docker Socket Access**: Application needs access to `/var/run/docker.sock`
- **Linux kernel**: 4.x or newer
- **RAM**: Minimum 256 MB (512 MB recommended)
- **Disk space**: Minimum 100 MB (500 MB recommended)

### Tested Distributions
- Ubuntu 20.04, 22.04, 24.04
- Debian 11, 12
- CentOS 8, 9
- Fedora 38+
- Alpine Linux
- Arch Linux

### Python Dependencies
- Flask 3.0+
- Docker 7.0+

See [requirements.txt](requirements.txt) for detailed dependency versions.

## Installation & Setup

### Quickstart: Docker Compose (Recommended)

```bash
# Copy the hosts template and edit it with your remote hosts
cp hosts.json.template hosts.json

# Set a dashboard password before starting
export DASHBOARD_PASSWORD='choose-a-strong-password'

docker-compose up --build
```

Access the dashboard at `http://localhost:5000` and sign in with username `admin`
and the password from `DASHBOARD_PASSWORD`.

### Alternative: Run Locally (Python)

If you prefer to run the application directly with Python instead of Docker:

#### Prerequisites
- Python 3.9+ installed
- Docker Engine running and accessible
- User added to docker group:
  ```bash
  sudo usermod -aG docker $USER
  newgrp docker
  ```

#### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
DASHBOARD_PASSWORD='choose-a-strong-password' \
python app.py
```

Access the dashboard at `http://localhost:5000`

### Authentication

The dashboard uses HTTP Basic Authentication. Configure credentials with:

```bash
export DASHBOARD_USERNAME=admin
export DASHBOARD_PASSWORD='choose-a-strong-password'
```

Docker Compose defaults to `admin` / `changeme` if these variables are not set.
Change the password before using the dashboard on your LAN.

## Running the Application

### Using Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up --build

# For subsequent runs (without rebuilding):
docker-compose up

# Run in background
docker-compose up -d

# Stop the container
docker-compose down
```

### Local Python Development

For development with live code changes:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Changes to the code will be reflected immediately (with page refresh).

### Production Docker Deployment

For production environments:

```bash
docker build -t docker-dashboard .
docker run -d \
  --name docker-dashboard \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e FLASK_ENV=production \
  docker-dashboard
```

### Systemd Service

For persistent daemon deployment, create `/etc/systemd/system/docker-dashboard.service`:

```ini
[Unit]
Description=Docker Dashboard
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/docker_dashboard
ExecStart=/usr/local/bin/docker-compose up
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable docker-dashboard
sudo systemctl start docker-dashboard
```

## Usage

### Web Interface

1. **Open your browser** and navigate to `http://localhost:5000`

2. **Dashboard Tab**: View overall statistics and disk usage
   - Quick overview of container and image counts
   - Storage breakdown by resource type

3. **Containers Tab**: Manage running containers
   - View status, ports, and uptime
   - Click on a container to view real-time logs
   - Use action buttons to start, stop, restart, or remove containers

4. **Images Tab**: Browse and manage Docker images
   - Sort by name, size, or creation date
   - Remove unused images to free space

5. **Volumes Tab**: View and manage volumes
   - Monitor volume drivers and mount points
   - Remove unused volumes

6. **Networks Tab**: View Docker networks
   - See network drivers, scopes, and subnets
   - Identify custom and built-in networks

## API Endpoints

### Dashboard
- **GET** `/api/dashboard` - Retrieve dashboard statistics and disk usage

### Containers
- **GET** `/api/containers` - List all containers
- **POST** `/api/containers/<container_id>/start` - Start a container
- **POST** `/api/containers/<container_id>/stop` - Stop a container
- **POST** `/api/containers/<container_id>/restart` - Restart a container
- **DELETE** `/api/containers/<container_id>` - Remove a container
- **GET** `/api/containers/<container_id>/stats` - Get container CPU/memory stats
- **GET** `/api/containers/<container_id>/logs/stream` - Stream container logs (Server-Sent Events)

### Images
- **GET** `/api/images` - List all images
- **GET** `/api/images/<image_id>` - Inspect image details
- **DELETE** `/api/images/<image_id>` - Remove an image

### Volumes
- **GET** `/api/volumes` - List all volumes
- **DELETE** `/api/volumes/<volume_name>` - Remove a volume

### Networks
- **GET** `/api/networks` - List all networks

### Frontend Routes
- **GET** `/` - Main dashboard page
- **GET** `/containers` - Containers management page
- **GET** `/images` - Images management page
- **GET** `/volumes` - Volumes management page
- **GET** `/networks` - Networks management page
- **GET** `/containers/<container_id>/logs` - Container logs page

## Architecture

### Backend (`app.py`)
Flask-based web server providing:
- Page rendering with Jinja2 templates
- RESTful API endpoints for Docker operations
- Server-Sent Events (SSE) for real-time log streaming

### Docker Client (`docker_client.py`)
Abstraction layer over the Docker Python SDK providing:
- Connection management and error handling
- Container, image, volume, and network operations
- Real-time statistics and log streaming
- Human-readable formatting (disk size, uptime, etc.)

### Frontend (Static Files)
- **HTML Templates** (`templates/`): Responsive page layouts built with Bootstrap
- **CSS** (`static/css/app.css`): Styling and responsive design
- **JavaScript** (`static/js/`): Dynamic UI interactions and API calls
  - `dashboard.js`: Dashboard statistics and real-time updates
  - `containers.js`: Container management and log streaming
  - `images.js`: Image management operations
  - `volumes.js`: Volume management operations
  - `networks.js`: Network listing and information
  - `logs.js`: Real-time log display and formatting

## File Structure

```
docker_dashboard/
├── app.py                      # Flask application and routes
├── docker_client.py            # Docker API wrapper
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container build configuration
├── docker-compose.yml          # Docker Compose configuration
├── .env                        # Environment variables
├── hosts.json.template         # Template for hosts configuration (commit this)
├── hosts.json                  # Your local hosts config — copy from template (do not commit)
├── static/
│   ├── css/
│   │   └── app.css            # Application styling
│   └── js/
│       ├── dashboard.js        # Dashboard functionality
│       ├── containers.js       # Container management
│       ├── images.js           # Image management
│       ├── logs.js             # Log streaming
│       ├── volumes.js          # Volume management
│       └── networks.js         # Network listing
└── templates/
    ├── base.html               # Base template
    ├── dashboard.html          # Dashboard page
    ├── containers.html         # Containers page
    ├── images.html             # Images page
    ├── logs.html               # Logs page
    ├── volumes.html            # Volumes page
    └── networks.html           # Networks page
```

## Configuration

### hosts.json — Remote Host Configuration

`hosts.json` defines the Docker hosts available in the dashboard's host switcher. It is excluded from git (`.gitignore`) so your personal host list stays local.

**First-time setup:**
```bash
cp hosts.json.template hosts.json
```

Then edit `hosts.json` to add your remote hosts. Each entry requires:

| Field | Description |
|-------|-------------|
| `id` | Unique slug used in URLs and localStorage (e.g. `raspberry-pi`) |
| `name` | Display name shown in the dropdown |
| `url` | Docker connection URL (see below) |
| `is_local` | Set `true` only for the local Unix socket entry |

**Supported URL formats:**

```
unix:///var/run/docker.sock   # Local Unix socket (default local host)
tcp://192.168.1.50:2375       # Remote host, no TLS
tcp://192.168.1.50:2376       # Remote host, TLS (configure certs separately)
```

> Remote hosts require Docker's TCP listener to be enabled. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for setup instructions.

You can also add and remove hosts at runtime via the **Hosts** page in the sidebar — changes are written to `hosts.json` automatically.

---

### Docker Socket Connection
The application automatically attempts to connect to Docker using the standard Docker Python SDK, which respects:
- The `DOCKER_HOST` environment variable (if set)
- The default Docker socket location for your platform

### Environment Variables

```env
FLASK_ENV=production          # production or development
FLASK_DEBUG=False             # Disable debug in production
FLASK_HOST=0.0.0.0           # Listen on all interfaces
FLASK_PORT=5000              # Application port
```

### Docker Compose Overrides

To customize docker-compose without editing the main file, create `docker-compose.override.yml`:

```yaml
services:
  docker-dashboard:
    ports:
      - "8080:5000"  # Different port
    restart: always
    environment:
      - FLASK_ENV=development
```

### Flask Configuration
The Flask app runs in development mode by default. For production deployment:
- Consider using a WSGI server (Gunicorn, uWSGI)
- Add proper error logging and monitoring
- Implement authentication if exposed to untrusted networks

## Error Handling

The dashboard gracefully handles Docker connection failures:
- **Connection Lost**: Displays a connection status indicator
- **Invalid Operations**: Shows user-friendly error messages
- **Stream Errors**: Logs errors to container logs display
- **Resource Not Found**: Handles 404 errors for deleted containers/images

## Performance Considerations

- **Real-time Updates**: Use browser refresh or API polling for updated stats
- **Large Container Lists**: UI handles multiple containers efficiently
- **Log Streaming**: Server-Sent Events (SSE) provide efficient real-time log delivery
- **Disk Usage Calculation**: Dashboard stats cached per request (not real-time)
- **Memory Usage**: Typically 50-150 MB depending on Docker activity
- **CPU Usage**: Minimal; mainly idle waiting for API calls
- **Startup Time**: ~2-3 seconds for container to be ready

## Browser Compatibility

- **Chrome/Chromium 90+**
- **Firefox 88+**
- **Safari 14+**
- **Edge 90+**

## Troubleshooting

### Docker Connection Failed
- Ensure Docker daemon is running: `sudo systemctl start docker`
- Verify Docker socket exists: `ls -l /var/run/docker.sock`
- Ensure your user is in the docker group: `sudo usermod -aG docker $USER`
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting steps

### Port Already in Use
- Change the port in `.env`: `FLASK_PORT=5001`
- Or kill the process using port 5000: `lsof -ti :5000 | xargs kill -9`
- Then restart: `docker-compose up --build`

### Logs Not Appearing
- Verify the container is running: `docker ps`
- Check container permissions and stdout redirection
- Ensure container hasn't exited

### High Memory Usage
- Clear old container logs from the UI
- Restart the dashboard application
- Consider limiting log tail size in configuration

## Development

### Adding New Features
1. Add Docker API calls to `docker_client.py`
2. Create Flask routes in `app.py`
3. Add HTML template in `templates/`
4. Create JavaScript functionality in `static/js/`
5. Style with CSS in `static/css/app.css`

### Testing
```bash
# Run with verbose output
python -u app.py
```

## Maintenance

### Regular Tasks

```bash
# View logs
docker-compose logs -f

# Clean up
docker-compose down
docker system prune

# Update images
docker-compose pull
docker-compose up --build
```

### Backup

```bash
# Back up current state
docker-compose down
tar -czf dashboard-backup.tar.gz .
```

## Security Considerations

⚠️ **Important**: This dashboard provides direct access to Docker operations. Security recommendations:

1. **Docker Socket Access**: The application requires access to `/var/run/docker.sock`, which gives full Docker control. Only run this on trusted systems.

2. **Network Isolation**: Do not expose to untrusted networks without authentication
   - Run on localhost only, or
   - Use firewall rules to restrict access, or
   - Deploy behind a reverse proxy with authentication

3. **Access Control**: Restrict who can run the Docker daemon and access the application

4. **Container Privileges**: Be cautious when removing or restarting containers

5. **Authentication**: This application has no built-in authentication. Consider:
   - Running behind a reverse proxy with auth
   - Using firewall rules to restrict access
   - Running on localhost only

6. **HTTPS**: Use reverse proxy (nginx, traefik) to add HTTPS in production

**Example Nginx Reverse Proxy with Authentication**:

```nginx
server {
    listen 80;
    server_name docker-dashboard.local;

    location / {
        proxy_pass http://localhost:5000;
        auth_basic "Docker Dashboard";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

## License

This project is provided as-is for Docker management and monitoring purposes.

**Note**: This is a Linux-focused application designed to work with Docker Engine for optimal performance and minimal dependencies.

## Contributing

Contributions welcome! Areas for enhancement:
- Container statistics history and graphing
- Docker registry integration
- Container creation wizard
- Resource limit alerts
- Multi-host Docker management
- Advanced filtering and search
- Custom dashboard widgets

## Support

For issues or questions:
1. Check Docker daemon connectivity
2. Review application logs
3. Verify Docker API version compatibility
4. Ensure all dependencies are installed
