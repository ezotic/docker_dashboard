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

    const select = document.getElementById('host-select');
    if (select) {
      const active = getActiveHost();
      select.innerHTML = hosts.map(h =>
        `<option value="${h.id}"${h.id === active ? ' selected' : ''}>${h.name}</option>`
      ).join('');

      select.addEventListener('change', () => {
        setActiveHost(select.value);
        const url = new URL(window.location);
        if (select.value === 'local') {
          url.searchParams.delete('host');
        } else {
          url.searchParams.set('host', select.value);
        }
        window.location = url.toString();
      });
    }

    // Sync status dot to active host's real connection state
    const activeId = getActiveHost();
    const activeHost = hosts.find(h => h.id === activeId);
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
      _updateNavLinks(activeId);
    }
  } catch (_) {}
})();
