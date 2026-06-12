const logBox = document.getElementById('log-box');
const containerId = logBox.dataset.containerId;
const statusBadge = document.getElementById('stream-status');
let autoScroll = true;

const source = new EventSource(`/api/containers/${containerId}/logs/stream`);

source.onmessage = e => {
  const line = document.createElement('span');
  line.className = 'log-line';
  line.textContent = e.data;
  logBox.appendChild(line);
  if (autoScroll) logBox.scrollTop = logBox.scrollHeight;
};

source.onerror = () => {
  statusBadge.textContent = 'Disconnected';
  statusBadge.className = 'badge bg-danger';
  source.close();
};

document.getElementById('btn-pause').addEventListener('click', e => {
  autoScroll = !autoScroll;
  e.currentTarget.innerHTML = autoScroll
    ? '<i class="bi bi-pause-fill"></i> Pause scroll'
    : '<i class="bi bi-play-fill"></i> Resume scroll';
  e.currentTarget.classList.toggle('btn-outline-secondary', autoScroll);
  e.currentTarget.classList.toggle('btn-outline-warning', !autoScroll);
});

document.getElementById('btn-clear').addEventListener('click', () => {
  logBox.innerHTML = '';
});

window.addEventListener('beforeunload', () => source.close());
