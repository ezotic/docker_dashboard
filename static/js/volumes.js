const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
let pendingName = null;

document.querySelectorAll('.remove-vol-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    pendingName = btn.dataset.name;
    document.getElementById('confirm-name').textContent = pendingName;
    confirmModal.show();
  });
});

document.getElementById('confirm-btn').addEventListener('click', async () => {
  if (!pendingName) return;
  confirmModal.hide();
  try {
    const res = await csrfFetch(apiUrl(`/api/volumes/${encodeURIComponent(pendingName)}`), { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || 'Remove failed');
    } else {
      location.reload();
    }
  } catch {
    showToast('Network error');
  }
  pendingName = null;
});
