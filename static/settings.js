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

function setStatus(msg, isError) {
  const el = document.getElementById('settingsStatus');
  el.textContent = msg;
  el.className = 'settings-status' + (isError ? ' settings-status-error' : ' settings-status-ok');
}

async function loadKeyStatuses() {
  try {
    const resp = await fetch('/api/keys', { headers: { 'X-Lang': getLang() } });
    const data = await resp.json();
    if (data.error) return;
    document.querySelectorAll('.key-list .key-card').forEach(card => {
      const provider = card.dataset.provider;
      const statusEl = card.querySelector('[data-status]');
      const removeBtn = card.querySelector('.key-remove-btn');
      const isSet = !!data[provider];
      statusEl.textContent = isSet ? t('key_added') : t('key_not_added');
      statusEl.className = 'key-status' + (isSet ? ' key-status-set' : '');
      removeBtn.style.display = isSet ? 'inline-block' : 'none';
    });
  } catch (e) { /* sessiz geç */ }
}

const KEY_PREFIXES = { claude: 'sk-ant-', chatgpt: 'sk-' };

function isValidKeyFormat(provider, value) {
  const prefix = KEY_PREFIXES[provider];
  if (!prefix) return true;
  if (!value.startsWith(prefix)) return false;
  // chatgpt'nin 'sk-' kontrolü, claude'un 'sk-ant-' key'ini de yanlışlıkla
  // kabul eder (sk-ant- de sk- ile başlar) — bunu açıkça reddet.
  if (provider === 'chatgpt' && value.startsWith(KEY_PREFIXES.claude)) return false;
  return true;
}

async function saveKey(card) {
  const provider = card.dataset.provider;
  const input = card.querySelector('.key-input');
  const value = input.value.trim();
  if (!value) { setStatus(t('api_key_empty'), true); return; }

  if (!isValidKeyFormat(provider, value)) {
    setStatus(t('invalid_key_format'), true);
    return;
  }

  try {
    await userInfoReady;
    const resp = await fetch('/api/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken, 'X-Lang': getLang() },
      body: JSON.stringify({ provider, api_key: value })
    });
    const data = await resp.json();
    if (data.error) { setStatus(data.error, true); return; }
    input.value = '';
    setStatus(t('saved'), false);
    loadKeyStatuses();
  } catch (e) {
    setStatus(t('err_prefix') + e.message, true);
  }
}

async function removeKey(card) {
  const provider = card.dataset.provider;
  try {
    await userInfoReady;
    const resp = await fetch(`/api/keys/${provider}`, { method: 'DELETE', headers: { 'X-CSRF-Token': csrfToken, 'X-Lang': getLang() } });
    const data = await resp.json();
    if (data.error) { setStatus(data.error, true); return; }
    setStatus(t('removed'), false);
    loadKeyStatuses();
  } catch (e) {
    setStatus(t('err_prefix') + e.message, true);
  }
}

document.querySelectorAll('.key-list .key-card').forEach(card => {
  card.querySelector('.key-save-btn').addEventListener('click', () => saveKey(card));
  card.querySelector('.key-remove-btn').addEventListener('click', () => removeKey(card));
});

async function loadHistoryToggle() {
  try {
    const resp = await fetch('/api/history', { headers: { 'X-Lang': getLang() } });
    const data = await resp.json();
    if (data.error) return;
    document.getElementById('historyToggleInput').checked = !!data.history_enabled;
  } catch (e) { /* sessiz geç */ }
}

document.getElementById('historyToggleInput').addEventListener('change', async (e) => {
  const enabled = e.target.checked;
  try {
    await userInfoReady;
    const resp = await fetch('/api/history/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken, 'X-Lang': getLang() },
      body: JSON.stringify({ enabled })
    });
    const data = await resp.json();
    if (data.error) { setStatus(data.error, true); e.target.checked = !enabled; return; }
    setStatus(enabled ? t('history_on') : t('history_off'), false);
  } catch (err) {
    setStatus(t('err_prefix') + err.message, true);
    e.target.checked = !enabled;
  }
});

const userInfoReady = loadUserInfo();
loadKeyStatuses();
loadHistoryToggle();

document.addEventListener('langchange', loadKeyStatuses);
