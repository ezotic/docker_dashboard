async function loadHosts() {
  const tbody = document.getElementById('hosts-tbody');
  try {
    const res = await fetch('/api/hosts');
    if (!res.ok) throw new Error('Failed to load hosts');
    const hosts = await res.json();

    if (!hosts.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No hosts configured.</td></tr>';
      return;
    }

    tbody.innerHTML = hosts.map(h => `
      <tr data-id="${h.id}">
        <td class="fw-semibold">${escHtml(h.name)}</td>
        <td class="font-monospace small text-muted d-none d-sm-table-cell">${escHtml(h.url)}</td>
        <td>
          ${h.connected
            ? '<span class="badge bg-success">connected</span>'
            : `<span class="badge bg-danger" title="${escHtml(h.error || '')}"">offline</span>`}
        </td>
        <td class="text-muted small d-none d-md-table-cell">${escHtml(h.version || '—')}</td>
        <td class="text-end">
          ${h.is_local ? '' : `
            <button class="btn btn-sm btn-outline-danger delete-host-btn"
                    data-id="${h.id}" data-name="${escHtml(h.name)}">
              <i class="bi bi-trash3"></i>
            </button>
          `}
        </td>
      </tr>
    `).join('');

    tbody.querySelectorAll('.delete-host-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm(`Remove host "${btn.dataset.name}"?`)) return;
        btn.disabled = true;
        try {
          const res = await fetch(`/api/hosts/${encodeURIComponent(btn.dataset.id)}`, { method: 'DELETE' });
          const data = await res.json();
          if (res.ok) {
            if (getActiveHost() === btn.dataset.id) setActiveHost('local');
            loadHosts();
          } else {
            showToast(data.error || 'Delete failed');
            btn.disabled = false;
          }
        } catch {
          showToast('Network error');
          btn.disabled = false;
        }
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">${escHtml(err.message)}</td></tr>`;
  }
}

document.getElementById('add-host-btn').addEventListener('click', async () => {
  const name = document.getElementById('host-name').value.trim();
  const url  = document.getElementById('host-url').value.trim();
  const errEl = document.getElementById('add-host-error');
  errEl.classList.add('d-none');

  if (!name || !url) {
    errEl.textContent = 'Name and URL are required.';
    errEl.classList.remove('d-none');
    return;
  }

  const btn = document.getElementById('add-host-btn');
  btn.disabled = true;
  try {
    const res = await fetch('/api/hosts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, url }),
    });
    const data = await res.json();
    if (!res.ok) {
      errEl.textContent = data.error || 'Failed to add host.';
      errEl.classList.remove('d-none');
    } else {
      document.getElementById('host-name').value = '';
      document.getElementById('host-url').value = '';
      loadHosts();
    }
  } catch {
    errEl.textContent = 'Network error.';
    errEl.classList.remove('d-none');
  } finally {
    btn.disabled = false;
  }
});

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

loadHosts();
