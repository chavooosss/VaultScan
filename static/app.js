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

function applyTheme(theme) {
  if (theme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    const btn = document.getElementById('themeToggle');
    if (btn) btn.textContent = '☾';
  } else {
    document.documentElement.removeAttribute('data-theme');
    const btn = document.getElementById('themeToggle');
    if (btn) btn.textContent = '☀︎';
  }
}

function toggleTheme() {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  const next = isLight ? 'dark' : 'light';
  localStorage.setItem('theme', next);
  applyTheme(next);
}

applyTheme(localStorage.getItem('theme'));

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener');
  }
});

function sanitizeAiHtml(html) {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['div', 'span', 'p', 'strong', 'code', 'pre', 'ul', 'ol', 'li', 'a'],
    ALLOWED_ATTR: ['class', 'href']
  });
}

function countSeverities(html) {
  const counts = { critical: 0, high: 0, medium: 0, low: 0 };
  const regex = /badge-(critical|high|medium|low)\b/g;
  let m;
  while ((m = regex.exec(html))) counts[m[1]]++;
  return counts;
}

function summaryPillsHtml(counts) {
  const labels = { critical: 'Kritik', high: 'Yüksek', medium: 'Orta', low: 'Düşük' };
  const total = counts.critical + counts.high + counts.medium + counts.low;

  if (total === 0) {
    return '<span class="summary-clean">✓ Kritik bulgu yok</span>';
  }

  const pills = Object.keys(labels)
    .filter(key => counts[key] > 0)
    .map(key => `<span class="summary-pill summary-${key}"><strong>${counts[key]}</strong> ${labels[key]}</span>`)
    .join('');

  return `<span class="summary-pill summary-total"><strong>${total}</strong> Bulgu</span>${pills}`;
}

function summaryBarHtml(html) {
  return `<div class="summary-bar">${summaryPillsHtml(countSeverities(html))}</div>`;
}

function injectLineChips(html) {
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html;
  wrapper.querySelectorAll('.finding').forEach(finding => {
    const body = finding.querySelector('.finding-body');
    const titleEl = finding.querySelector('.finding-title');
    if (!body || !titleEl) return;
    const lineP = Array.from(body.querySelectorAll('p')).find(p => p.textContent.includes('Satır:'));
    if (!lineP) return;
    const match = lineP.textContent.match(/Satır:\s*(.+)/);
    const value = match ? match[1].trim() : '';
    if (!value || /^n\/?a$/i.test(value)) return;
    const chip = document.createElement('span');
    chip.className = 'line-chip';
    chip.textContent = `L:${value}`;
    titleEl.appendChild(chip);
  });
  return wrapper.innerHTML;
}

let currentTab = 'paste';

function switchTab(tab, el) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('pastePanel').style.display = tab === 'paste' ? 'flex' : 'none';
  document.getElementById('filePanel').style.display = tab === 'file' ? 'flex' : 'none';
  document.getElementById('githubPanel').style.display = tab === 'github' ? 'flex' : 'none';

  const shown = document.getElementById(tab + 'Panel');
  if (shown) {
    shown.classList.remove('panel-fade');
    void shown.offsetWidth;
    shown.classList.add('panel-fade');
  }
}

document.addEventListener('keydown', (e) => {
  if (!(e.ctrlKey || e.metaKey) || e.key !== 'Enter') return;
  e.preventDefault();
  if (currentTab === 'paste') analyze();
  else if (currentTab === 'file') document.getElementById('fileInput').click();
  else if (currentTab === 'github') analyzeGithub();
});

function showExportButtons() {
  document.getElementById('copyBtn').style.display = 'inline-block';
  document.getElementById('mdBtn').style.display = 'inline-block';
  document.getElementById('pdfBtn').style.display = 'inline-block';
}

function hideExportButtons() {
  document.getElementById('copyBtn').style.display = 'none';
  document.getElementById('mdBtn').style.display = 'none';
  document.getElementById('pdfBtn').style.display = 'none';
}

function setLoading(msg) {
  hideExportButtons();
  document.getElementById('status').className = 'status-loading';
  document.getElementById('status').textContent = msg;
  document.getElementById('result').innerHTML = `<p class="muted">⏳ ${msg}</p>`;
}

function setResult(html) {
  document.getElementById('result').innerHTML = summaryBarHtml(html) + injectLineChips(sanitizeAiHtml(html));
  showExportButtons();
  document.getElementById('status').className = 'status-done';
  document.getElementById('status').textContent = '✓ Tamamlandı';
}

function setError(msg) {
  document.getElementById('result').innerHTML = `<p class="error-text">${escapeHtml(msg)}</p>`;
  document.getElementById('status').className = 'status-error';
  document.getElementById('status').textContent = '✗ Hata';
}

function buildZipHtml(results) {
  return results.map(r =>
    `<div class="file-section"><div class="file-name">📄 ${escapeHtml(r.file)}</div>${injectLineChips(sanitizeAiHtml(r.result))}</div>`
  ).join('');
}

function toggleProvider(el) {
  const active = document.querySelectorAll('.provider-chip.active');
  if (el.classList.contains('active')) {
    if (active.length === 1) return;
    el.classList.remove('active');
  } else {
    el.classList.add('active');
  }
}

function getSelectedProviders() {
  return Array.from(document.querySelectorAll('.provider-chip.active')).map(el => el.dataset.provider);
}

async function analyze() {
  const code = document.getElementById('code').value.trim();
  const language = document.getElementById('language').value;
  const btn = document.getElementById('analyzeBtn');

  if (!code) { setError('Lütfen kod gir.'); return; }

  btn.disabled = true;
  setLoading('Analiz ediliyor...');

  try {
    await userInfoReady;
    const response = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      body: JSON.stringify({ code, language, providers: getSelectedProviders() })
    });
    const data = await response.json();
    if (data.error) { setError(data.error); return; }
    setResult(data.result);
  } catch (err) {
    setError('Hata: ' + err.message);
  } finally {
    btn.disabled = false;
  }
}

async function uploadFile(input) {
  const file = input.files[0];
  if (!file) return;
  await handleFile(file);
}

async function handleFile(file) {
  if (!file) return;

  const uploadArea = document.getElementById('uploadArea');
  uploadArea.innerHTML = `<div class="upload-icon">📄</div><p>${escapeHtml(file.name)}</p><p class="hint" style="margin-top:4px">${(file.size/1024).toFixed(1)} KB</p>`;
  document.getElementById('uploadBtn').style.display = 'block';

  setLoading('Dosya analiz ediliyor...');

  const formData = new FormData();
  formData.append('file', file);
  formData.append('providers', getSelectedProviders().join(','));

  try {
    await userInfoReady;
    const response = await fetch('/upload', { method: 'POST', headers: { 'X-CSRF-Token': csrfToken }, body: formData });
    const data = await response.json();
    if (data.error) { setError(data.error); return; }
    setResult(data.type === 'zip' ? buildZipHtml(data.results) : data.result);
  } catch (err) {
    setError('Hata: ' + err.message);
  }
}

async function analyzeGithub() {
  const url = document.getElementById('githubUrl').value.trim();
  const token = document.getElementById('githubToken').value.trim();
  const btn = document.getElementById('githubBtn');

  if (!url) { setError('GitHub URL gir.'); return; }

  btn.disabled = true;
  hideExportButtons();
  document.getElementById('status').className = 'status-loading';
  document.getElementById('status').textContent = 'Bağlanıyor...';
  document.getElementById('result').innerHTML = '<p class="muted">⏳ Repo analiz ediliyor...</p>';

  const results = [];
  let total = 0;
  let repo = '';

  try {
    await userInfoReady;
    const response = await fetch('/github', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      body: JSON.stringify({ url, token, providers: getSelectedProviders() })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const msg = JSON.parse(line);

          if (msg.error) {
            setError(msg.error);
            btn.disabled = false;
            return;
          }

          if (msg.type === 'error') {
            setError(msg.message);
            btn.disabled = false;
            return;
          }

          if (msg.type === 'start') {
            total = msg.total;
            repo = msg.repo;
            document.getElementById('resultTitle').textContent = `Sonuç — ${repo}`;
            document.getElementById('result').innerHTML = `
              <div class="progress-wrap">
                <div class="progress-info">
                  <span id="progressText">0 / ${total} dosya analiz edildi</span>
                </div>
                <div class="progress-bar-bg">
                  <div class="progress-bar" id="progressBar" style="width:0%"></div>
                </div>
                <div id="progressFile" class="progress-file"></div>
              </div>
              <div class="summary-bar" id="summaryBar"></div>
              <div id="resultsContainer"></div>
            `;
          }

          if (msg.type === 'progress') {
            const pct = Math.round((msg.current / total) * 100);
            const bar = document.getElementById('progressBar');
            const text = document.getElementById('progressText');
            const file = document.getElementById('progressFile');
            if (bar) bar.style.width = pct + '%';
            if (text) text.textContent = `${msg.current} / ${total} dosya analiz edildi`;
            if (file) file.textContent = `⏳ ${msg.file}`;
            document.getElementById('status').textContent = `${msg.current}/${total} dosya`;
          }

          if (msg.type === 'result') {
            results.push(msg);
            const container = document.getElementById('resultsContainer');
            if (container) {
              container.innerHTML += `<div class="file-section"><div class="file-name">📄 ${escapeHtml(msg.file)}</div>${injectLineChips(sanitizeAiHtml(msg.result))}</div>`;
            }
            const summaryBar = document.getElementById('summaryBar');
            if (summaryBar) summaryBar.innerHTML = summaryPillsHtml(countSeverities(container.innerHTML));
          }

          if (msg.type === 'done') {
            const progressWrap = document.querySelector('.progress-wrap');
            if (progressWrap) progressWrap.style.display = 'none';
            showExportButtons();
            document.getElementById('status').className = 'status-done';
            document.getElementById('status').textContent = '✓ Tamamlandı';
          }

        } catch (e) { /* json parse hatası */ }
      }
    }

    // Stream hiç başlamadan tek seferlik bir {"error": ...} ile bitmiş olabilir
    // (örn. geçersiz URL, CSRF, rate limit) — sonda \n olmadığı için yukarıdaki
    // döngü bunu hiç işlemez, son kalan parçayı burada kontrol ediyoruz.
    if (buffer.trim()) {
      try {
        const msg = JSON.parse(buffer);
        if (msg.error) setError(msg.error);
      } catch (e) { /* yoksay */ }
    }
  } catch (err) {
    setError('Hata: ' + err.message);
  } finally {
    btn.disabled = false;
  }
}

function copyResult() {
  const copyBtn = document.getElementById('copyBtn');
  navigator.clipboard.writeText(document.getElementById('result').innerText).then(() => {
    copyBtn.textContent = '✓ Kopyalandı';
    setTimeout(() => { copyBtn.textContent = 'Kopyala'; }, 2000);
  });
}

function resultToMarkdown() {
  const root = document.getElementById('result');
  const title = document.getElementById('resultTitle').textContent.trim();
  const lines = [`# VaultScan Güvenlik Raporu`, ``, `**${title}**  `, `_Oluşturulma: ${new Date().toLocaleString('tr-TR')}_`, ``];

  const summary = root.querySelector('.summary-bar');
  if (summary) {
    lines.push('## Özet', '');
    summary.querySelectorAll('.summary-pill, .summary-clean').forEach(p => {
      lines.push(`- ${p.textContent.trim()}`);
    });
    lines.push('');
  }

  const fileSections = root.querySelectorAll('.file-section');
  const groups = fileSections.length ? fileSections : [root];

  groups.forEach(group => {
    const fileName = group.querySelector('.file-name');
    if (fileName) lines.push(`## ${fileName.textContent.trim()}`, '');

    group.querySelectorAll('.finding').forEach(f => {
      const findingTitle = f.querySelector('.finding-title')?.textContent.trim() || '';
      const badge = f.querySelector('.badge')?.textContent.trim() || '';
      lines.push(`### ${findingTitle} [${badge}]`, '');
      f.querySelectorAll('.finding-body p').forEach(p => {
        lines.push(`- ${p.textContent.trim()}`);
      });
      lines.push('');
    });
  });

  return lines.join('\n');
}

function downloadMarkdown() {
  const blob = new Blob([resultToMarkdown()], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `vaultscan-rapor-${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

(() => {
  const uploadArea = document.getElementById('uploadArea');
  if (!uploadArea) return;

  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
  });

  uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
  });

  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });
})();