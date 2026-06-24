const DEMO_EXAMPLES = {
  sql_injection: {
    code: `def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return db.execute(query)

def delete_user(user_id):
    db.execute("DELETE FROM users WHERE id = " + user_id)`,
    result: {
      en: `
        <div class="finding"><div class="finding-header"><span class="finding-title">SQL Injection via string concatenation</span><span class="badge badge-critical">CRITICAL</span></div><div class="finding-body">
        <p><strong>Line:</strong> 2, 6</p>
        <p><strong>Description:</strong> user_id is concatenated directly into the SQL query in both get_user and delete_user, letting an attacker inject arbitrary SQL (e.g. pass "1 OR 1=1" to delete every row).</p>
        <p><strong>Recommendation:</strong> Use parameterized queries everywhere, e.g. db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).</p>
        <p><strong>Detected by:</strong> Claude, ChatGPT, Gemini</p></div></div>
        <div class="finding"><div class="finding-header"><span class="finding-title">No authorization check before delete_user</span><span class="badge badge-high">HIGH</span></div><div class="finding-body">
        <p><strong>Line:</strong> 5</p>
        <p><strong>Description:</strong> delete_user performs a destructive operation with no check that the caller is allowed to delete that user.</p>
        <p><strong>Recommendation:</strong> Verify the current user's permissions before executing the delete.</p>
        <p><strong>Detected by:</strong> ChatGPT, Gemini</p></div></div>
      `,
      tr: `
        <div class="finding"><div class="finding-header"><span class="finding-title">String birleştirme ile SQL Injection</span><span class="badge badge-critical">CRITICAL</span></div><div class="finding-body">
        <p><strong>Satır:</strong> 2, 6</p>
        <p><strong>Açıklama:</strong> user_id, hem get_user hem delete_user içinde doğrudan SQL sorgusuna birleştiriliyor — bir saldırgan "1 OR 1=1" gibi bir değer göndererek tüm satırları silebilir.</p>
        <p><strong>Öneri:</strong> Her yerde parametreli sorgu kullan, örn. db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).</p>
        <p><strong>Tespit eden:</strong> Claude, ChatGPT, Gemini</p></div></div>
        <div class="finding"><div class="finding-header"><span class="finding-title">delete_user öncesi yetki kontrolü yok</span><span class="badge badge-high">HIGH</span></div><div class="finding-body">
        <p><strong>Satır:</strong> 5</p>
        <p><strong>Açıklama:</strong> delete_user, çağıranın bu kullanıcıyı silmeye yetkili olup olmadığını kontrol etmeden yıkıcı bir işlem gerçekleştiriyor.</p>
        <p><strong>Öneri:</strong> Silme işleminden önce mevcut kullanıcının yetkisini doğrula.</p>
        <p><strong>Tespit eden:</strong> ChatGPT, Gemini</p></div></div>
      `,
    },
  },
  hardcoded_secret: {
    code: `const stripe = require('stripe')('sk_live_EXAMPLE_DO_NOT_USE_xxxxxxxxxx');

function chargeCustomer(amount, token) {
  return stripe.charges.create({ amount, currency: 'usd', source: token });
}`,
    result: {
      en: `
        <div class="finding"><div class="finding-header"><span class="finding-title">Hardcoded live Stripe secret key</span><span class="badge badge-critical">CRITICAL</span></div><div class="finding-body">
        <p><strong>Line:</strong> 1</p>
        <p><strong>Description:</strong> A live (sk_live_...) Stripe secret key is committed directly in source. Anyone with read access to this code — or this repo's history — can use it to move real money.</p>
        <p><strong>Recommendation:</strong> Revoke this key immediately, move it to an environment variable / secret manager, and scan git history for other exposures.</p>
        <p><strong>Detected by:</strong> Claude, ChatGPT, Gemini</p></div></div>
        <div class="finding"><div class="finding-header"><span class="finding-title">No input validation on amount</span><span class="badge badge-medium">MEDIUM</span></div><div class="finding-body">
        <p><strong>Line:</strong> 4</p>
        <p><strong>Description:</strong> amount is passed straight to Stripe with no type/range check — a negative or absurdly large value could cause unexpected charges or errors.</p>
        <p><strong>Recommendation:</strong> Validate amount is a positive integer within an expected range before charging.</p>
        <p><strong>Detected by:</strong> Claude</p></div></div>
      `,
      tr: `
        <div class="finding"><div class="finding-header"><span class="finding-title">Sabit kodlanmış canlı Stripe key'i</span><span class="badge badge-critical">CRITICAL</span></div><div class="finding-body">
        <p><strong>Satır:</strong> 1</p>
        <p><strong>Açıklama:</strong> Canlı (sk_live_...) bir Stripe secret key doğrudan kaynak koda gömülmüş. Bu koda — veya repo geçmişine — erişimi olan herkes bunu gerçek para hareketi için kullanabilir.</p>
        <p><strong>Öneri:</strong> Bu key'i hemen iptal et, bir ortam değişkenine/secret manager'a taşı ve git geçmişinde başka sızıntı olup olmadığını tara.</p>
        <p><strong>Tespit eden:</strong> Claude, ChatGPT, Gemini</p></div></div>
        <div class="finding"><div class="finding-header"><span class="finding-title">amount için girdi doğrulaması yok</span><span class="badge badge-medium">MEDIUM</span></div><div class="finding-body">
        <p><strong>Satır:</strong> 4</p>
        <p><strong>Açıklama:</strong> amount, hiçbir tip/aralık kontrolü yapılmadan doğrudan Stripe'a gönderiliyor — negatif veya aşırı büyük bir değer beklenmeyen tahsilat veya hatalara yol açabilir.</p>
        <p><strong>Öneri:</strong> Tahsilattan önce amount'un beklenen aralıkta pozitif bir sayı olduğunu doğrula.</p>
        <p><strong>Tespit eden:</strong> Claude</p></div></div>
      `,
    },
  },
};

function loadExample(key) {
  const example = DEMO_EXAMPLES[key];
  if (!example) return;

  document.getElementById('code').value = example.code;
  document.getElementById('copyBtn').style.display = 'none';
  document.getElementById('result').innerHTML = skeletonHtml();
  document.getElementById('status').className = 'status-loading';
  document.getElementById('status').textContent = t('status_analyzing');

  setTimeout(() => {
    const html = example.result[getLang()] || example.result.en;
    document.getElementById('result').innerHTML = summaryBarHtml(html) + injectLineChips(sanitizeAiHtml(html));
    document.getElementById('copyBtn').style.display = 'inline-block';
    document.getElementById('status').className = 'status-done';
    document.getElementById('status').textContent = t('status_done');
  }, 1600);
}

function copyResult() {
  const copyBtn = document.getElementById('copyBtn');
  navigator.clipboard.writeText(document.getElementById('result').innerText).then(() => {
    copyBtn.textContent = t('copied');
    setTimeout(() => { copyBtn.textContent = t('btn_copy'); }, 2000);
  });
}
