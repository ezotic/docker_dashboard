const inspectModal = new bootstrap.Modal(document.getElementById('inspectModal'));
const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
let pendingId = null;

document.querySelectorAll('.inspect-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const { id, tag } = btn.dataset;
    document.getElementById('inspect-tag').textContent = tag;
    document.getElementById('inspect-body').textContent = 'Loading…';
    inspectModal.show();
    try {
      const res = await fetch(apiUrl(`/api/images/${encodeURIComponent(id)}/inspect`));
      const data = await res.json();
      document.getElementById('inspect-body').textContent = JSON.stringify(data, null, 2);
    } catch {
      document.getElementById('inspect-body').textContent = 'Failed to load.';
    }
  });
});

document.querySelectorAll('.remove-img-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    pendingId = btn.dataset.id;
    document.getElementById('confirm-tag').textContent = btn.dataset.tag;
    confirmModal.show();
  });
});

document.getElementById('confirm-btn').addEventListener('click', async () => {
  if (!pendingId) return;
  confirmModal.hide();
  try {
    const res = await fetch(apiUrl(`/api/images/${encodeURIComponent(pendingId)}`), { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Remove failed');
    } else {
      location.reload();
    }
  } catch {
    showToast('Network error');
  }
  pendingId = null;
});
