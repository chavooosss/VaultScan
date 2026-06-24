let csrfToken = '';

async function loadUserInfo() {
  try {
    const resp = await fetch('/api/me');
    const data = await resp.json();
    csrfToken = data.csrf_token || '';
    if (!data.authenticated) return;
    document.getElementById('userName').textContent = data.name;
    if (data.picture) {
      const avatar = document.getElementById('userAvatar');
      avatar.src = data.picture;
      avatar.style.display = 'inline-block';
    }
  } catch (e) { /* sessiz geç */ }
}

const userInfoReady = loadUserInfo();

const PROVIDER_LABELS = { claude: 'Claude', chatgpt: 'ChatGPT', gemini: 'Gemini' };

function sourceLabel(sourceType) {
  if (sourceType === 'paste') return t('source_paste');
  if (sourceType === 'file') return t('source_file');
  return 'GitHub';
}

function formatDate(iso) {
  const d = new Date(iso);
  const locale = getLang() === 'tr' ? 'tr-TR' : 'en-US';
  return d.toLocaleString(locale, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function renderProviders(providers) {
  return providers.map(p => `<span class="line-chip">${escapeHtml(PROVIDER_LABELS[p] || p)}</span>`).join(' ');
}

async function loadHistory() {
  const list = document.getElementById('historyList');
  try {
    await userInfoReady;
    const resp = await fetch('/api/history', { headers: { 'X-Lang': getLang() } });
    const data = await resp.json();
    if (data.error) {
      list.innerHTML = `<p class="error-text">${escapeHtml(data.error)}</p>`;
      return;
    }
    if (data.items.length === 0) {
      list.innerHTML = `<p class="muted">${t('no_analyses_yet')}</p>`;
      return;
    }
    list.innerHTML = data.items.map(item => `
      <div class="history-item" data-id="${item.id}">
        <div class="history-item-main">
          <span class="history-item-label">${escapeHtml(item.source_label)}</span>
          <span class="hint">${sourceLabel(item.source_type)} · ${formatDate(item.created_at)}</span>
          <div class="history-item-providers">${renderProviders(item.providers)}</div>
          ${severityBarHtml(item.severity_counts)}
        </div>
        <div class="history-item-actions">
          <button class="btn-copy history-view-btn" data-id="${item.id}">${t('btn_view')}</button>
          <button class="btn-copy key-remove-btn history-delete-btn" data-id="${item.id}">${t('btn_delete')}</button>
        </div>
      </div>
    `).join('');

    list.querySelectorAll('.history-view-btn').forEach(btn => {
      btn.addEventListener('click', () => viewHistoryItem(btn.dataset.id));
    });
    list.querySelectorAll('.history-delete-btn').forEach(btn => {
      btn.addEventListener('click', () => deleteHistoryItem(btn.dataset.id));
    });
  } catch (e) {
    list.innerHTML = `<p class="error-text">${t('err_prefix')}${escapeHtml(e.message)}</p>`;
  }
}

async function viewHistoryItem(id) {
  try {
    const resp = await fetch(`/api/history/${id}`, { headers: { 'X-Lang': getLang() } });
    const data = await resp.json();
    if (data.error) { alert(data.error); return; }
    document.getElementById('mainBackLink').style.display = 'none';
    document.getElementById('historyList').style.display = 'none';
    document.getElementById('historyDetail').style.display = 'block';
    document.getElementById('historyDetailResult').innerHTML =
      summaryBarHtml(data.result) + injectLineChips(sanitizeAiHtml(data.result));
  } catch (e) {
    alert(t('err_prefix') + e.message);
  }
}

async function deleteHistoryItem(id) {
  if (!confirm(t('confirm_delete_record'))) return;
  try {
    await userInfoReady;
    const resp = await fetch(`/api/history/${id}`, { method: 'DELETE', headers: { 'X-CSRF-Token': csrfToken, 'X-Lang': getLang() } });
    const data = await resp.json();
    if (data.error) { alert(data.error); return; }
    loadHistory();
  } catch (e) {
    alert(t('err_prefix') + e.message);
  }
}

document.getElementById('historyDetailBack').addEventListener('click', () => {
  document.getElementById('historyDetail').style.display = 'none';
  document.getElementById('mainBackLink').style.display = '';
  document.getElementById('historyList').style.display = '';
});

document.addEventListener('langchange', () => {
  if (document.getElementById('historyDetail').style.display === 'none') loadHistory();
});

loadHistory();
