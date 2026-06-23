async function loadUserInfo() {
  try {
    const resp = await fetch('/api/me');
    const data = await resp.json();
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
    const resp = await fetch('/api/keys');
    const data = await resp.json();
    if (data.error) return;
    document.querySelectorAll('.key-card').forEach(card => {
      const provider = card.dataset.provider;
      const statusEl = card.querySelector('[data-status]');
      const removeBtn = card.querySelector('.key-remove-btn');
      const isSet = !!data[provider];
      statusEl.textContent = isSet ? 'Eklendi' : 'Eklenmedi';
      statusEl.className = 'key-status' + (isSet ? ' key-status-set' : '');
      removeBtn.style.display = isSet ? 'inline-block' : 'none';
    });
  } catch (e) { /* sessiz geç */ }
}

async function saveKey(card) {
  const provider = card.dataset.provider;
  const input = card.querySelector('.key-input');
  const value = input.value.trim();
  if (!value) { setStatus('API key boş olamaz.', true); return; }

  try {
    const resp = await fetch('/api/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, api_key: value })
    });
    const data = await resp.json();
    if (data.error) { setStatus(data.error, true); return; }
    input.value = '';
    setStatus('Kaydedildi.', false);
    loadKeyStatuses();
  } catch (e) {
    setStatus('Hata: ' + e.message, true);
  }
}

async function removeKey(card) {
  const provider = card.dataset.provider;
  try {
    const resp = await fetch(`/api/keys/${provider}`, { method: 'DELETE' });
    const data = await resp.json();
    if (data.error) { setStatus(data.error, true); return; }
    setStatus('Kaldırıldı.', false);
    loadKeyStatuses();
  } catch (e) {
    setStatus('Hata: ' + e.message, true);
  }
}

document.querySelectorAll('.key-card').forEach(card => {
  card.querySelector('.key-save-btn').addEventListener('click', () => saveKey(card));
  card.querySelector('.key-remove-btn').addEventListener('click', () => removeKey(card));
});

loadUserInfo();
loadKeyStatuses();
