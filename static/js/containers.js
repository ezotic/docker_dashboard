const table = document.getElementById('containers-table');
const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
let pendingRemoveId = null;

// Action delegation
table && table.addEventListener('click', async e => {
  const btn = e.target.closest('[data-action]');
  if (!btn || btn.disabled) return;

  const { action, id, name } = btn.dataset;

  if (action === 'remove') {
    pendingRemoveId = id;
    document.getElementById('confirm-name').textContent = name || id.slice(0, 12);
    confirmModal.show();
    return;
  }

  btn.disabled = true;
  try {
    const res = await fetch(apiUrl(`/api/containers/${id}/${action}`), { method: 'POST' });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Action failed');
    } else {
      setTimeout(() => location.reload(), 800);
    }
  } catch (err) {
    showToast('Network error');
  } finally {
    btn.disabled = false;
  }
});

document.getElementById('confirm-btn').addEventListener('click', async () => {
  if (!pendingRemoveId) return;
  confirmModal.hide();
  try {
    const res = await fetch(apiUrl(`/api/containers/${pendingRemoveId}`), { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Remove failed');
    } else {
      const row = table.querySelector(`tr[data-id="${pendingRemoveId}"]`);
      if (row) row.remove();
    }
  } catch {
    showToast('Network error');
  }
  pendingRemoveId = null;
});

// Stats polling for running containers
async function pollStats() {
  const rows = table ? table.querySelectorAll('tr[data-status="running"]') : [];
  for (const row of rows) {
    const id = row.dataset.id;
    const shortId = id.slice(0, 12);
    try {
      const res = await fetch(apiUrl(`/api/containers/${id}/stats`));
      if (!res.ok) continue;
      const s = await res.json();
      const cpuEl = document.getElementById(`cpu-${shortId}`);
      const memEl = document.getElementById(`mem-${shortId}`);
      if (cpuEl) cpuEl.textContent = `${s.cpu_percent}%`;
      if (memEl) memEl.textContent = `${s.mem_usage} / ${s.mem_limit}`;
    } catch (_) {}
  }
}

pollStats();
const statsInterval = setInterval(pollStats, 3000);
window.addEventListener('beforeunload', () => clearInterval(statsInterval));
