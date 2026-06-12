const statMap = {
  running: 'stat-running',
  stopped: 'stat-stopped',
  total:   'stat-total',
  images:  'stat-images',
  volumes: 'stat-volumes',
};

const diskKeyMap = {
  images:       0,
  containers:   1,
  volumes:      2,
  build_cache:  3,
};

async function refreshDashboard() {
  try {
    const res = await fetch('/api/dashboard');
    if (!res.ok) return;
    const data = await res.json();
    for (const [key, id] of Object.entries(statMap)) {
      const el = document.getElementById(id);
      if (el && data[key] !== undefined) el.textContent = data[key];
    }
    if (data.disk) {
      const diskEls = document.querySelectorAll('.disk-val');
      diskEls.forEach(el => {
        const key = el.dataset.key;
        if (data.disk[key] !== undefined) el.textContent = data.disk[key];
      });
    }
  } catch (_) {}
}

setInterval(refreshDashboard, 10000);
