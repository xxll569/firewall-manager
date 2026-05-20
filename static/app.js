'use strict';

// ── Bootstrap helpers ──────────────────────────────────────────
const toastEl    = document.getElementById('mainToast');
const bsToast    = new bootstrap.Toast(toastEl, { delay: 3500 });
const confirmMdl = new bootstrap.Modal(document.getElementById('confirmModal'));

function toast(msg, type = 'success') {
  toastEl.className = `toast align-items-center border-0 ${type}`;
  document.getElementById('toastBody').textContent = msg;
  bsToast.show();
}

function showAlert(msg) {
  const div = document.createElement('div');
  div.className = 'alert alert-dismissible fade show';
  div.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i>${msg}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  document.getElementById('alertArea').prepend(div);
  setTimeout(() => div.remove(), 7000);
}

function confirmDo(msg, onOk) {
  document.getElementById('confirmBody').textContent = msg;
  const btn = document.getElementById('confirmOkBtn');
  btn.onclick = () => { confirmMdl.hide(); onOk(); };
  confirmMdl.show();
}

// ── Preset ports data (mirrors Python COMMON_PORTS) ───────────
const PRESETS = [
  { port: 22,    protocol: 'tcp', label: 'SSH',        icon: 'bi-terminal-fill' },
  { port: 80,    protocol: 'tcp', label: 'HTTP',       icon: 'bi-globe' },
  { port: 443,   protocol: 'tcp', label: 'HTTPS',      icon: 'bi-shield-lock-fill' },
  { port: 3306,  protocol: 'tcp', label: 'MySQL',      icon: 'bi-database-fill' },
  { port: 5432,  protocol: 'tcp', label: 'PostgreSQL', icon: 'bi-database-fill' },
  { port: 6379,  protocol: 'tcp', label: 'Redis',      icon: 'bi-lightning-fill' },
  { port: 27017, protocol: 'tcp', label: 'MongoDB',    icon: 'bi-database-fill' },
  { port: 8080,  protocol: 'tcp', label: 'HTTP-ALT',   icon: 'bi-globe2' },
  { port: 8443,  protocol: 'tcp', label: 'HTTPS-ALT',  icon: 'bi-shield-fill' },
  { port: 53,    protocol: 'udp', label: 'DNS',        icon: 'bi-diagram-3-fill' },
];

// Track which ports are currently open
let openPorts = new Set();  // key: "port/protocol"

function portKey(port, protocol) { return `${port}/${protocol}`; }

// ── Build preset grid ──────────────────────────────────────────
function buildPresets() {
  const grid = document.getElementById('presetGrid');
  grid.innerHTML = PRESETS.map(p => `
    <div class="preset-btn" id="preset-${p.port}-${p.protocol}"
         onclick="togglePreset(${p.port},'${p.protocol}')">
      <i class="bi ${p.icon} preset-icon"></i>
      <span class="preset-label">${p.label}</span>
      <span class="preset-port">${p.port}</span>
      <i class="bi bi-check-circle-fill preset-check"></i>
    </div>
  `).join('');
}

function updatePresetStates() {
  PRESETS.forEach(p => {
    const el = document.getElementById(`preset-${p.port}-${p.protocol}`);
    if (!el) return;
    if (openPorts.has(portKey(p.port, p.protocol))) {
      el.classList.add('active');
    } else {
      el.classList.remove('active');
    }
  });
}

async function togglePreset(port, protocol) {
  if (openPorts.has(portKey(port, protocol))) {
    confirmDo(`关闭端口 ${port}/${protocol.toUpperCase()}？`, () => removeRule(port, protocol));
  } else {
    const res = await fetch('/api/rules/add', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ port, protocol, direction: 'in', source: 'any' }),
    });
    const data = await res.json();
    if (data.success) { toast(data.message, 'success'); loadRules(); }
    else showAlert(data.message || '操作失败');
  }
}

// ── pf status ─────────────────────────────────────────────────
async function loadStatus() {
  const res  = await fetch('/api/status');
  const data = await res.json();
  const badge   = document.getElementById('pfBadge');
  const dot     = document.getElementById('statusDot');
  const label   = document.getElementById('statusLabel');

  if (data.enabled) {
    badge.textContent = '● 已启用';
    badge.className   = 'status-badge enabled';
    dot.className     = 'status-dot enabled';
    label.textContent = '运行中';
  } else {
    badge.textContent = '● 已禁用';
    badge.className   = 'status-badge disabled';
    dot.className     = 'status-dot disabled';
    label.textContent = '未启用';
  }
}

async function togglePf(action) {
  const res  = await fetch(`/api/${action}`, { method: 'POST' });
  const data = await res.json();
  if (data.success) { toast(data.message, 'success'); loadStatus(); }
  else showAlert(data.message || '操作失败');
}

// ── Rules ─────────────────────────────────────────────────────
async function loadRules() {
  const res  = await fetch('/api/rules');
  const data = await res.json();

  // Sync pf status badge
  const badge = document.getElementById('pfBadge');
  const dot   = document.getElementById('statusDot');
  const label = document.getElementById('statusLabel');
  if (data.pf_enabled) {
    badge.textContent = '● 已启用'; badge.className = 'status-badge enabled';
    dot.className = 'status-dot enabled'; label.textContent = '运行中';
  } else {
    badge.textContent = '● 已禁用'; badge.className = 'status-badge disabled';
    dot.className = 'status-dot disabled'; label.textContent = '未启用';
  }

  // Track open ports
  openPorts = new Set(data.rules.map(r => portKey(r.port, r.protocol)));
  updatePresetStates();

  // Update count badge
  document.getElementById('ruleCount').textContent = data.count;

  // Render list
  const list = document.getElementById('rulesList');
  if (!data.rules.length) {
    list.innerHTML = `<div class="empty-state">
      <i class="bi bi-shield-slash"></i>
      <p>暂无规则 — 点击上方快速开放端口，或填写自定义规则</p>
    </div>`;
    return;
  }

  list.innerHTML = data.rules.map(r => `
    <div class="rule-item">
      <div class="rule-port-badge">${r.port}</div>
      <span class="rule-proto-badge ${r.protocol}">${r.protocol.toUpperCase()}</span>
      <span class="rule-dir">${r.direction === 'in' ? '↓ 入站' : '↑ 出站'}</span>
      <div class="rule-meta">
        <div class="rule-raw" title="${r.rule}">${r.rule}</div>
      </div>
      <button class="btn-remove" title="删除规则"
              onclick="confirmRemove(${r.port},'${r.protocol}')">
        <i class="bi bi-trash3"></i>
      </button>
    </div>
  `).join('');

  // Populate raw output if already expanded
  const rawDiv = document.getElementById('rawOutput');
  if (rawDiv.classList.contains('show')) {
    updateRaw(data.raw);
  }
}

function updateRaw(rawData) {
  const pre = document.getElementById('rawText');
  if (rawData && rawData.anchor_rules) {
    pre.textContent =
      '=== Anchor Rules ===\n' + rawData.anchor_rules +
      '\n\n=== PF Status ===\n' + (rawData.pf_info || '');
  } else {
    pre.textContent = '(无数据)';
  }
}

// load raw when user expands the section
document.getElementById('rawOutput').addEventListener('show.bs.collapse', async () => {
  const res  = await fetch('/api/rules');
  const data = await res.json();
  updateRaw(data.raw);
});

// ── Add rule ───────────────────────────────────────────────────
async function addRule() {
  const port      = document.getElementById('addPort').value.trim();
  const protocol  = document.getElementById('addProtocol').value;
  const direction = document.getElementById('addDirection').value;
  const source    = document.getElementById('addSource').value.trim() || 'any';

  if (!port) { showAlert('请填写端口号'); return; }

  const res  = await fetch('/api/rules/add', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ port: parseInt(port), protocol, direction, source }),
  });
  const data = await res.json();
  if (data.success) {
    toast(data.message, 'success');
    document.getElementById('addPort').value = '';
    loadRules();
  } else {
    showAlert(data.message || '添加失败');
  }
}

// ── Remove rule ────────────────────────────────────────────────
function confirmRemove(port, protocol) {
  confirmDo(`确定关闭端口 ${port}/${protocol.toUpperCase()}？此操作会立即生效。`,
            () => removeRule(port, protocol));
}

async function removeRule(port, protocol) {
  const res  = await fetch('/api/rules/remove', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ port, protocol }),
  });
  const data = await res.json();
  if (data.success) { toast(data.message, 'success'); loadRules(); }
  else showAlert(data.message || '删除失败');
}

// ── Enter key shortcut for port input ─────────────────────────
document.getElementById('addPort').addEventListener('keydown', e => {
  if (e.key === 'Enter') addRule();
});

// ── Refresh all ───────────────────────────────────────────────
async function refreshAll() {
  await Promise.all([loadStatus(), loadRules()]);
  toast('已刷新', 'info');
}

// ── Init ───────────────────────────────────────────────────────
buildPresets();
loadRules();   // also loads status
