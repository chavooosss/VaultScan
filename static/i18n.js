const LANG_DICT = {
  tr: {
    title_index: 'VaultScan',
    title_login: 'VaultScan — Giriş',
    title_settings: 'VaultScan — Ayarlar',
    title_history: 'VaultScan — Geçmiş',
    title_privacy: 'VaultScan — Gizlilik',

    nav_history: 'Geçmiş',
    nav_settings: 'Ayarlar',
    nav_privacy: 'Gizlilik',
    nav_logout: 'Çıkış',

    eyebrow_tool: 'Güvenlik Analiz Aracı',
    eyebrow_settings: 'Ayarlar',
    eyebrow_history: 'Geçmiş',
    eyebrow_privacy: 'Gizlilik',

    tagline_index: 'Kodunu yapıştır, dosya yükle veya GitHub repo analiz et',

    tab_paste: 'Kod Yapıştır',
    tab_file: 'Dosya Yükle',
    provider_picker_title: 'Analiz için bir veya daha fazla AI seç',

    label_code: 'Kod',
    lang_auto: 'Otomatik Tespit',
    code_placeholder: 'Kodunu buraya yapıştır...',
    btn_analyze: 'Analiz Et',
    btn_cancel: 'İptal',

    upload_drag_or_click: 'Dosyayı buraya sürükle veya tıkla',
    upload_zip_hint: 'ZIP dosyası ile birden fazla dosya analiz edebilirsin',

    github_url_placeholder: 'https://github.com/kullanici/repo',
    github_token_placeholder: 'GitHub Token (opsiyonel, private repo için)',
    github_hint: 'Public repolar için token gerekmez. Max 20 dosya analiz edilir. · Ctrl+Enter ile analiz et',
    btn_analyze_repo: 'Repo Analiz Et',

    label_result: 'Sonuç',
    btn_copy: 'Kopyala',
    btn_stop: '⏹ Durdur',
    print_title: 'VaultScan — Güvenlik Analiz Raporu',
    result_placeholder: 'Analiz sonucu burada görünecek...',

    login_subtitle: 'Devam etmek için Google hesabınla giriş yap.',
    login_error: 'Giriş başarısız oldu, lütfen tekrar deneyin.',
    login_with_google: 'Google ile Giriş Yap',
    login_privacy_link: 'Verilerinle ne yapıyoruz?',

    settings_h1: "API Key'lerin",
    settings_subtitle: "VaultScan analiz yaparken senin kendi API key'ini kullanır — hiçbir AI sağlayıcısına biz ödeme yapmıyoruz, key'ler şifreli saklanır.",
    back_to_analysis: '← Analiz sayfasına dön',
    status_loading: 'Yükleniyor...',
    claude_key_note: 'Ücretli bir key gerekir. <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener">console.anthropic.com</a> üzerinden alabilirsin.',
    chatgpt_key_note: "Ücretli — hesabında ödeme yöntemi/kredi olması gerekir, ChatGPT Plus aboneliği API erişimi vermez. <a href=\"https://platform.openai.com/api-keys\" target=\"_blank\" rel=\"noopener\">platform.openai.com</a> üzerinden alabilirsin.",
    gemini_key_note: 'Ücretsiz API key alabilirsin. <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com</a> üzerinden alabilirsin.',
    btn_save: 'Kaydet',
    btn_remove: 'Kaldır',
    history_toggle_name: 'Analiz Geçmişi',
    history_toggle_note: 'Açıksa, her analizin AI raporu (kod/dosya/repo içeriği hariç) <a href="/history">geçmiş sayfasında</a> saklanır. İstediğin zaman kapatabilirsin.',

    history_h1: 'Analiz Geçmişin',
    history_subtitle: "Daha önce yaptığın analizlerin raporları — kod/dosya/repo içeriği saklanmaz, sadece AI'nin ürettiği rapor.",
    back_to_list: '← Listeye dön',

    back_to_home: '← Ana sayfaya dön',
    privacy_h1: 'Verilerinle ne yapıyoruz?',
    privacy_google_h2: 'Google ile girişte ne alıyoruz',
    privacy_google_p: 'Sadece Google hesabından gelen ad, e-posta adresi ve profil fotoğrafı bağlantısı. Şifreni hiçbir zaman görmüyoruz — giriş tamamen Google üzerinden yapılır.',
    privacy_keys_h2: "AI API key'lerin",
    privacy_keys_p: "VaultScan kendi AI key'ini kullanmaz — Claude/ChatGPT/Gemini için girdiğin key'ler senindir ve veritabanında <strong>şifrelenmiş</strong> olarak saklanır. Hiçbir ekranda veya API yanıtında düz metin olarak geri gösterilmez. İstediğin zaman Ayarlar sayfasından silebilirsin.",
    privacy_code_h2: 'Analiz ettiğin kod ne olur',
    privacy_code_p1: 'VaultScan, yapıştırdığın/yüklediğin kodu veya GitHub repo içeriğini <strong>kendi sunucusunda saklamaz</strong>. Kod, seçtiğin AI sağlayıcısına (Claude/ChatGPT/Gemini) senin kendi API key\'inle iletilir ve analiz orada yapılır.',
    privacy_code_p2: 'Bu nedenle gerçekten gizli/hassas kod paylaşıyorsan, seçtiğin AI sağlayıcının kendi gizlilik politikasını da göz önünde bulundur — o aşamada veri o sağlayıcının sunucularında işlenir.',
    privacy_history_h2: 'Analiz geçmişi',
    privacy_history_p1: "AI'nin ürettiği <strong>rapor/bulgular</strong> (hangi açıklar bulundu, hangi AI(ler) tespit etti, ne zaman yapıldı) hesabınla ilişkilendirilip <a href=\"/history\">Geçmiş</a> sayfasında saklanır — bu sayede eski analizlerine dönüp bakabilirsin. Analiz ettiğin <strong>kodun/dosyanın/repo içeriğinin kendisi bu kayda dahil değildir</strong>, yukarıdaki maddede anlatıldığı gibi hiçbir zaman sunucumuzda tutulmaz.",
    privacy_history_p2: 'Bu özelliği Ayarlar sayfasından istediğin zaman kapatabilirsin; kapattığında yeni analizler kaydedilmez. Geçmiş sayfasından tek tek kayıt da silebilirsin.',
    privacy_github_h2: "GitHub token'ı",
    privacy_github_p: "Private repo analizi için girdiğin GitHub token'ı sadece o anki isteği yapmak için kullanılır, hiçbir yere kaydedilmez.",
    privacy_cookies_h2: 'Çerezler',
    privacy_cookies_p: 'Sadece oturumunu açık tutmak için teknik amaçlı bir oturum çerezi kullanılır. Reklam/takip amaçlı çerez yok.',
    privacy_delete_h2: 'Hesabını silmek istersen',
    privacy_delete_p: "API key'lerini Ayarlar sayfasından, analiz geçmişi kayıtlarını Geçmiş sayfasından kendin kaldırabilirsin. Hesabının tamamen silinmesini istersen aşağıdaki adresten bize yazman yeterli.",
    privacy_contact_h2: 'Soruların için',
    privacy_note: 'Bu sayfa, verilerinle ne yaptığımızı açık ve sade bir dille anlatan bir bilgilendirme notudur — resmi bir KVKK Aydınlatma Metni değildir.',

    err_enter_code: 'Lütfen kod gir.',
    err_enter_github_url: 'GitHub URL gir.',
    err_prefix: 'Hata: ',
    status_analyzing: 'Analiz ediliyor...',
    status_analyzing_file: 'Dosya analiz ediliyor...',
    status_connecting: 'Bağlanıyor...',
    status_done: '✓ Tamamlandı',
    status_error: '✗ Hata',
    status_stopped: 'Durduruldu',
    status_stopped_msg: '⏹ Analiz durduruldu.',
    copied: '✓ Kopyalandı',
    files_analyzed: '{current} / {total} dosya analiz edildi',
    files_count_short: '{current}/{total} dosya',
    markdown_title: 'VaultScan Güvenlik Raporu',
    markdown_generated: 'Oluşturulma: {date}',
    label_summary: 'Özet',
    severity_critical: 'Kritik',
    severity_high: 'Yüksek',
    severity_medium: 'Orta',
    severity_low: 'Düşük',
    summary_clean: '✓ Kritik bulgu yok',
    summary_finding_label: 'Bulgu',

    key_added: 'Eklendi',
    key_not_added: 'Eklenmedi',
    invalid_key_format: "Geçersiz API key formatı. Claude için sk-ant-, OpenAI için sk- ile başlamalı.",
    saved: 'Kaydedildi.',
    removed: 'Kaldırıldı.',
    history_on: 'Analiz geçmişi açıldı.',
    history_off: 'Analiz geçmişi kapatıldı.',

    source_paste: 'Kod',
    source_file: 'Dosya',
    no_analyses_yet: 'Henüz hiç analiz yapmadın.',
    btn_view: 'Görüntüle',
    btn_delete: 'Sil',
    confirm_delete_record: 'Bu kaydı silmek istediğine emin misin?',
    api_key_empty: 'API key boş olamaz.',
  },
  en: {
    title_index: 'VaultScan',
    title_login: 'VaultScan — Sign in',
    title_settings: 'VaultScan — Settings',
    title_history: 'VaultScan — History',
    title_privacy: 'VaultScan — Privacy',

    nav_history: 'History',
    nav_settings: 'Settings',
    nav_privacy: 'Privacy',
    nav_logout: 'Log out',

    eyebrow_tool: 'Security Analysis Tool',
    eyebrow_settings: 'Settings',
    eyebrow_history: 'History',
    eyebrow_privacy: 'Privacy',

    tagline_index: 'Paste your code, upload a file, or analyze a GitHub repo',

    tab_paste: 'Paste Code',
    tab_file: 'Upload File',
    provider_picker_title: 'Select one or more AIs for analysis',

    label_code: 'Code',
    lang_auto: 'Auto-detect',
    code_placeholder: 'Paste your code here...',
    btn_analyze: 'Analyze',
    btn_cancel: 'Cancel',

    upload_drag_or_click: 'Drag a file here or click to upload',
    upload_zip_hint: 'Use a ZIP file to analyze multiple files at once',

    github_url_placeholder: 'https://github.com/username/repo',
    github_token_placeholder: 'GitHub token (optional, for private repos)',
    github_hint: 'No token needed for public repos. Max 20 files analyzed. · Ctrl+Enter to analyze',
    btn_analyze_repo: 'Analyze Repo',

    label_result: 'Result',
    btn_copy: 'Copy',
    btn_stop: '⏹ Stop',
    print_title: 'VaultScan — Security Analysis Report',
    result_placeholder: 'Analysis result will appear here...',

    login_subtitle: 'Sign in with your Google account to continue.',
    login_error: 'Login failed, please try again.',
    login_with_google: 'Sign in with Google',
    login_privacy_link: 'What do we do with your data?',

    settings_h1: 'Your API Keys',
    settings_subtitle: "VaultScan uses your own API key when running an analysis — we never pay any AI provider on your behalf, and your keys are stored encrypted.",
    back_to_analysis: '← Back to analysis page',
    status_loading: 'Loading...',
    claude_key_note: 'Requires a paid key. You can get one at <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener">console.anthropic.com</a>.',
    chatgpt_key_note: 'Paid — your account needs a payment method/credits; a ChatGPT Plus subscription does not grant API access. Get one at <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener">platform.openai.com</a>.',
    gemini_key_note: 'You can get a free API key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com</a>.',
    btn_save: 'Save',
    btn_remove: 'Remove',
    history_toggle_name: 'Analysis History',
    history_toggle_note: 'When enabled, each analysis\'s AI report (excluding the code/file/repo content itself) is stored on the <a href="/history">history page</a>. You can turn it off anytime.',

    history_h1: 'Your Analysis History',
    history_subtitle: "Reports from analyses you've run before — the code/file/repo content itself is never stored, only the report the AI produced.",
    back_to_list: '← Back to list',

    back_to_home: '← Back to home',
    privacy_h1: 'What do we do with your data?',
    privacy_google_h2: 'What we get when you sign in with Google',
    privacy_google_p: "Only the name, email address, and profile picture link from your Google account. We never see your password — sign-in happens entirely through Google.",
    privacy_keys_h2: 'Your AI API keys',
    privacy_keys_p: 'VaultScan never uses its own AI key — the keys you enter for Claude/ChatGPT/Gemini are yours and are stored <strong>encrypted</strong> in the database. They are never shown back in plain text on any screen or API response. You can delete them anytime from the Settings page.',
    privacy_code_h2: 'What happens to the code you analyze',
    privacy_code_p1: 'VaultScan does <strong>not store on its own server</strong> the code or GitHub repo content you paste or upload. The code is sent to the AI provider you chose (Claude/ChatGPT/Gemini) using your own API key, and the analysis happens there.',
    privacy_code_p2: "So if you're sharing genuinely confidential/sensitive code, also keep in mind the privacy policy of the AI provider you chose — at that point the data is processed on that provider's servers.",
    privacy_history_h2: 'Analysis history',
    privacy_history_p1: 'The <strong>report/findings</strong> the AI produces (which vulnerabilities were found, which AI(s) detected them, when it was run) are linked to your account and stored on the <a href="/history">History</a> page, so you can look back at past analyses. The <strong>code/file/repo content itself is not part of this record</strong> — as described above, it is never kept on our server.',
    privacy_history_p2: 'You can turn this feature off anytime from the Settings page; once off, new analyses won\'t be saved. You can also delete individual records from the History page.',
    privacy_github_h2: 'Your GitHub token',
    privacy_github_p: 'The GitHub token you enter for private repo analysis is only used to make that one request — it is never saved anywhere.',
    privacy_cookies_h2: 'Cookies',
    privacy_cookies_p: 'We only use a technical session cookie to keep you signed in. No advertising or tracking cookies.',
    privacy_delete_h2: 'If you want to delete your account',
    privacy_delete_p: 'You can remove your API keys from the Settings page and your analysis history from the History page yourself. If you want your account fully deleted, just email us at the address below.',
    privacy_contact_h2: 'Questions',
    privacy_note: "This page is a plain-language note about what we do with your data — it is not a formal legal privacy policy.",

    err_enter_code: 'Please enter some code.',
    err_enter_github_url: 'Enter a GitHub URL.',
    err_prefix: 'Error: ',
    status_analyzing: 'Analyzing...',
    status_analyzing_file: 'Analyzing file...',
    status_connecting: 'Connecting...',
    status_done: '✓ Done',
    status_error: '✗ Error',
    status_stopped: 'Stopped',
    status_stopped_msg: '⏹ Analysis stopped.',
    copied: '✓ Copied',
    files_analyzed: '{current} / {total} files analyzed',
    files_count_short: '{current}/{total} files',
    markdown_title: 'VaultScan Security Report',
    markdown_generated: 'Generated: {date}',
    label_summary: 'Summary',
    severity_critical: 'Critical',
    severity_high: 'High',
    severity_medium: 'Medium',
    severity_low: 'Low',
    summary_clean: '✓ No critical findings',
    summary_finding_label: 'Finding(s)',

    key_added: 'Added',
    key_not_added: 'Not added',
    invalid_key_format: 'Invalid API key format. Claude keys start with sk-ant-, OpenAI keys with sk-.',
    saved: 'Saved.',
    removed: 'Removed.',
    history_on: 'Analysis history turned on.',
    history_off: 'Analysis history turned off.',

    source_paste: 'Code',
    source_file: 'File',
    no_analyses_yet: "You haven't run any analyses yet.",
    btn_view: 'View',
    btn_delete: 'Delete',
    confirm_delete_record: 'Are you sure you want to delete this record?',
    api_key_empty: 'API key cannot be empty.',
  },
};

function detectLang() {
  const stored = localStorage.getItem('lang');
  if (stored === 'tr' || stored === 'en') return stored;
  return (navigator.language || '').toLowerCase().startsWith('tr') ? 'tr' : 'en';
}

let currentLang = detectLang();

function getLang() {
  return currentLang;
}

function t(key, params) {
  let str = (LANG_DICT[currentLang] && LANG_DICT[currentLang][key]) || LANG_DICT.tr[key] || key;
  if (params) {
    Object.keys(params).forEach((k) => {
      str = str.replace(`{${k}}`, params[k]);
    });
  }
  return str;
}

function applyI18n() {
  document.documentElement.lang = currentLang;

  document.querySelectorAll('[data-i18n]').forEach((el) => {
    el.textContent = t(el.getAttribute('data-i18n'));
  });
  document.querySelectorAll('[data-i18n-html]').forEach((el) => {
    el.innerHTML = t(el.getAttribute('data-i18n-html'));
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
  });
  document.querySelectorAll('[data-i18n-title]').forEach((el) => {
    el.title = t(el.getAttribute('data-i18n-title'));
  });

  const langBtn = document.getElementById('langToggle');
  if (langBtn) langBtn.textContent = currentLang === 'tr' ? 'EN' : 'TR';

  document.dispatchEvent(new CustomEvent('langchange', { detail: { lang: currentLang } }));
}

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem('lang', lang);
  applyI18n();
}

function toggleLang() {
  setLang(currentLang === 'tr' ? 'en' : 'tr');
}

document.addEventListener('DOMContentLoaded', applyI18n);
