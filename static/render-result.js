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

function severityBarSegments(counts) {
  const total = counts.critical + counts.high + counts.medium + counts.low;
  if (total === 0) return '';
  return ['critical', 'high', 'medium', 'low']
    .filter(key => counts[key] > 0)
    .map(key => `<div class="severity-bar-seg severity-bar-${key}" style="width:${(counts[key] / total * 100).toFixed(2)}%"></div>`)
    .join('');
}

function severityBarHtml(counts) {
  const segments = severityBarSegments(counts);
  return segments ? `<div class="severity-bar">${segments}</div>` : '';
}

function summaryBarHtml(html) {
  const counts = countSeverities(html);
  return `${severityBarHtml(counts)}<div class="summary-bar">${summaryPillsHtml(counts)}</div>`;
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
