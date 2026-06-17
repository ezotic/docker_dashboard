const HOST_KEY = 'dockerDashboardHost';

function getActiveHost() {
  return localStorage.getItem(HOST_KEY) || 'local';
}

function setActiveHost(id) {
  localStorage.setItem(HOST_KEY, id);
}

function apiUrl(path) {
  const h = getActiveHost();
  if (h === 'local') return path;
  const sep = path.includes('?') ? '&' : '?';
  return `${path}${sep}host=${encodeURIComponent(h)}`;
}

function _updateNavLinks(hostId) {
  if (hostId === 'local') return;
  document.querySelectorAll('.nav-link[href]').forEach(link => {
    const href = link.getAttribute('href');
    if (href && href.startsWith('/') && !href.includes('host=')) {
      link.setAttribute('href', `${href}?host=${encodeURIComponent(hostId)}`);
    }
  });
}

(async function initHostSwitcher() {
  try {
    const res = await fetch('/api/hosts');
    if (!res.ok) return;
    const hosts = await res.json();

    const list = document.getElementById('host-list');
    if (!list) return;

    const active = getActiveHost();

    list.replaceChildren(...hosts.map(h => {
      const btn = document.createElement('button');
      btn.className = 'host-item nav-link text-light w-100 text-start' + (h.id === active ? ' active' : '');
      btn.dataset.id = h.id;

      const dot = document.createElement('span');
      dot.className = `status-dot ${h.connected ? 'dot-green' : 'dot-red'} me-2`;

      btn.appendChild(dot);
      btn.appendChild(document.createTextNode(h.name));

      btn.addEventListener('click', () => {
        setActiveHost(h.id);
        const url = new URL(window.location);
        if (h.id === 'local') {
          url.searchParams.delete('host');
        } else {
          url.searchParams.set('host', h.id);
        }
        window.location = url.toString();
      });

      return btn;
    }));

    // Sync status dot to active host's real connection state
    const activeHost = hosts.find(h => h.id === active);
    if (activeHost) {
      const dot = document.getElementById('daemon-dot');
      const label = document.getElementById('daemon-label');
      if (dot) {
        dot.className = `status-dot ${activeHost.connected ? 'dot-green' : 'dot-red'}`;
      }
      if (label) {
        label.textContent = activeHost.connected
          ? `${activeHost.name} connected`
          : `${activeHost.name} offline`;
      }
      _updateNavLinks(active);
    }
  } catch (_) {}
})();
