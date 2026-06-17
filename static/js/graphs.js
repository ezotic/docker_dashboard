const MAX_POINTS = 60;
const POLL_INTERVAL = 3000;

const history = {};  // { id: { labels, cpu, mem, net_rx, net_tx, blk_read, blk_write, prev } }
const charts = {};   // { id: { cpu, mem, net, blk } }

const grid = document.getElementById('graphs-grid');
const emptyState = document.getElementById('empty-state');

function currentHost() {
  return localStorage.getItem('selectedHost') || INITIAL_HOST;
}

function nowLabel() {
  const d = new Date();
  return d.getHours().toString().padStart(2, '0') + ':' +
         d.getMinutes().toString().padStart(2, '0') + ':' +
         d.getSeconds().toString().padStart(2, '0');
}

function fmtBps(v) {
  if (v < 1024) return v.toFixed(0) + ' B/s';
  if (v < 1048576) return (v / 1024).toFixed(1) + ' KB/s';
  return (v / 1048576).toFixed(1) + ' MB/s';
}

function rate(current, prev) {
  if (prev === null) return 0;
  return Math.max(0, (current - prev) / (POLL_INTERVAL / 1000));
}

function makePercentChartConfig(label, color) {
  return {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label,
        data: [],
        borderColor: color,
        backgroundColor: color.replace('rgb', 'rgba').replace(')', ', 0.15)'),
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.3,
        fill: true,
      }]
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y.toFixed(1)}%` } }
      },
      scales: {
        x: {
          ticks: { color: 'rgba(255,255,255,0.4)', maxTicksLimit: 6, maxRotation: 0 },
          grid: { color: 'rgba(255,255,255,0.05)' },
        },
        y: {
          min: 0,
          max: 100,
          ticks: { color: 'rgba(255,255,255,0.4)', callback: v => v + '%' },
          grid: { color: 'rgba(255,255,255,0.05)' },
        }
      }
    }
  };
}

function makeDualBytesChartConfig(label1, color1, label2, color2) {
  function mkDataset(label, color) {
    return {
      label,
      data: [],
      borderColor: color,
      backgroundColor: color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.3,
      fill: false,
    };
  }
  return {
    type: 'line',
    data: {
      labels: [],
      datasets: [mkDataset(label1, color1), mkDataset(label2, color2)]
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: {
          display: true,
          labels: { color: 'rgba(255,255,255,0.6)', boxWidth: 12, padding: 8, font: { size: 11 } }
        },
        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmtBps(ctx.parsed.y)}` } }
      },
      scales: {
        x: {
          ticks: { color: 'rgba(255,255,255,0.4)', maxTicksLimit: 6, maxRotation: 0 },
          grid: { color: 'rgba(255,255,255,0.05)' },
        },
        y: {
          beginAtZero: true,
          ticks: { color: 'rgba(255,255,255,0.4)', callback: v => fmtBps(v) },
          grid: { color: 'rgba(255,255,255,0.05)' },
        }
      }
    }
  };
}

function createCard(container) {
  const col = document.createElement('div');
  col.className = 'col-12 col-md-6';
  col.id = `card-${container.id}`;
  col.innerHTML = `
    <div class="card bg-dark border-secondary h-100">
      <div class="card-header border-secondary d-flex align-items-center gap-2 py-2">
        <span class="status-dot dot-green"></span>
        <span class="fw-semibold">${container.name}</span>
        <span class="text-muted small font-monospace ms-1">${container.short_id}</span>
      </div>
      <div class="card-body">
        <div class="row g-3">
          <div class="col-6">
            <div class="text-muted small mb-1">CPU %</div>
            <div style="height:130px;"><canvas id="cpu-chart-${container.id}"></canvas></div>
          </div>
          <div class="col-6">
            <div class="text-muted small mb-1">Memory %</div>
            <div style="height:130px;"><canvas id="mem-chart-${container.id}"></canvas></div>
          </div>
          <div class="col-6">
            <div class="text-muted small mb-1">Network I/O</div>
            <div style="height:130px;"><canvas id="net-chart-${container.id}"></canvas></div>
          </div>
          <div class="col-6">
            <div class="text-muted small mb-1">Block I/O</div>
            <div style="height:130px;"><canvas id="blk-chart-${container.id}"></canvas></div>
          </div>
        </div>
      </div>
    </div>`;
  grid.appendChild(col);

  history[container.id] = {
    labels: [], cpu: [], mem: [], net_rx: [], net_tx: [], blk_read: [], blk_write: [],
    prev: { net_rx: null, net_tx: null, blk_read: null, blk_write: null }
  };

  charts[container.id] = {
    cpu: new Chart(document.getElementById(`cpu-chart-${container.id}`),
                   makePercentChartConfig('CPU %', 'rgb(13, 202, 240)')),
    mem: new Chart(document.getElementById(`mem-chart-${container.id}`),
                   makePercentChartConfig('Memory %', 'rgb(255, 193, 7)')),
    net: new Chart(document.getElementById(`net-chart-${container.id}`),
                   makeDualBytesChartConfig('RX', 'rgb(25, 135, 84)', 'TX', 'rgb(111, 66, 193)')),
    blk: new Chart(document.getElementById(`blk-chart-${container.id}`),
                   makeDualBytesChartConfig('Read', 'rgb(253, 126, 20)', 'Write', 'rgb(220, 53, 69)')),
  };
}

function removeCard(id) {
  const el = document.getElementById(`card-${id}`);
  if (el) el.remove();
  if (charts[id]) {
    charts[id].cpu.destroy();
    charts[id].mem.destroy();
    charts[id].net.destroy();
    charts[id].blk.destroy();
    delete charts[id];
  }
  delete history[id];
}

function pushTrimmed(arr, val) {
  arr.push(val);
  if (arr.length > MAX_POINTS) arr.shift();
}

function updateCharts(container) {
  const h = history[container.id];
  const c = charts[container.id];
  if (!h || !c) return;

  const label = nowLabel();
  const netRxRate = rate(container.net_rx_bytes ?? 0, h.prev.net_rx);
  const netTxRate = rate(container.net_tx_bytes ?? 0, h.prev.net_tx);
  const blkReadRate = rate(container.blk_read_bytes ?? 0, h.prev.blk_read);
  const blkWriteRate = rate(container.blk_write_bytes ?? 0, h.prev.blk_write);

  h.prev = {
    net_rx: container.net_rx_bytes ?? 0,
    net_tx: container.net_tx_bytes ?? 0,
    blk_read: container.blk_read_bytes ?? 0,
    blk_write: container.blk_write_bytes ?? 0,
  };

  pushTrimmed(h.labels, label);
  pushTrimmed(h.cpu, container.cpu_percent ?? 0);
  pushTrimmed(h.mem, container.mem_percent ?? 0);
  pushTrimmed(h.net_rx, netRxRate);
  pushTrimmed(h.net_tx, netTxRate);
  pushTrimmed(h.blk_read, blkReadRate);
  pushTrimmed(h.blk_write, blkWriteRate);

  c.cpu.data.labels = h.labels;
  c.cpu.data.datasets[0].data = h.cpu;
  c.cpu.update('none');

  c.mem.data.labels = h.labels;
  c.mem.data.datasets[0].data = h.mem;
  c.mem.update('none');

  c.net.data.labels = h.labels;
  c.net.data.datasets[0].data = h.net_rx;
  c.net.data.datasets[1].data = h.net_tx;
  c.net.update('none');

  c.blk.data.labels = h.labels;
  c.blk.data.datasets[0].data = h.blk_read;
  c.blk.data.datasets[1].data = h.blk_write;
  c.blk.update('none');
}

async function pollGraphs() {
  try {
    const host = currentHost();
    const res = await fetch(`/api/graphs/stats?host=${encodeURIComponent(host)}`);
    if (!res.ok) return;
    const data = await res.json();
    if (!Array.isArray(data)) return;

    const activeIds = new Set(data.map(c => c.id));

    for (const id of Object.keys(charts)) {
      if (!activeIds.has(id)) removeCard(id);
    }

    for (const container of data) {
      if (!charts[container.id]) createCard(container);
      updateCharts(container);
    }

    if (emptyState) emptyState.classList.toggle('d-none', data.length > 0);
  } catch (_) {
    // network error — silently retry next interval
  }
}

pollGraphs();
setInterval(pollGraphs, POLL_INTERVAL);
