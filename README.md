# VaultScan

VaultScan, kodunu yapay zekâya gösterip "burada güvenlik açığı var mı?" diye sorduğun bir araç. Kod yapıştırabilir, bir dosya/zip yükleyebilir veya bir GitHub repo linki verebilirsin — VaultScan kodu okur, riskli noktaları (SQL injection, XSS, sızdırılmış şifreler, zayıf doğrulama gibi) bulur ve sana okunabilir bir rapor olarak gösterir.

## Bu ne işe yarar? (kısaca)

Diyelim bir proje yazdın ve "bunda güvenlik açığı var mı, kontrol ettirsem mi?" diye düşünüyorsun ama bir güvenlik uzmanı tutmak istemiyorsun. VaultScan tam bunun için: kodunu (veya tüm projeni) yapay zekâya gösterir, bulduğu sorunları "ne kadar ciddi" (kritik / yüksek / orta / düşük) etiketiyle birlikte sana listeler.

Asıl farkı: tek bir yapay zekâya değil, istersen aynı anda birden fazla yapay zekâya (Claude, ChatGPT, Gemini) sorabilirsin. Hepsi kodu ayrı ayrı inceler, sonra bulgular tek bir ortak rapor halinde birleştirilir — yani üç farklı "göz" aynı kodu kontrol etmiş olur.

## Özellikler

- **Kod yapıştır** — küçük bir kod parçasını direkt yapıştırıp analiz et.
- **Dosya / ZIP yükle** — tek dosya veya birden fazla dosya içeren bir ZIP yükle, VaultScan en kritik dosyaları öncelik sırasına koyup analiz eder.
- **GitHub repo analizi** — bir GitHub repo linki ver (public veya token ile private), VaultScan repoyu tarar ve dosya dosya ilerlerken anlık ilerleme gösterir.
- **Çoklu yapay zekâ desteği** — Claude (Anthropic), ChatGPT (OpenAI) ve Gemini (Google) arasından istediğini seç.
- **Birlikte analiz (collaborative mode)** — birden fazla AI'yı aynı anda seçtiğinde, hepsinin bulguları tek bir raporda birleştirilir ve hangi AI'nın neyi bulduğu belirtilir.
- **Google ile giriş** — uygulamayı kullanmak için Google hesabınla giriş yapman gerekir.
- **Kendi API key'in (BYOK)** — VaultScan'in kendi AI key'i yok; her kullanıcı `/settings` sayfasından kendi Claude/ChatGPT/Gemini key'ini ekler ve analizlerde kendi key'i kullanılır. Key'ler şifrelenmiş olarak saklanır.
- **Rapor dışa aktarma** — sonucu Markdown olarak indir veya PDF olarak yazdır.

## Nasıl çalışır?

1. Google hesabınla giriş yaparsın.
2. `/settings` sayfasından kullanacağın AI sağlayıcı(lar)ın için kendi API key'ini eklersin (Claude key'i ücretli; ChatGPT ve Gemini'nin ücretsiz katmanları var).
3. Kod yapıştırır, dosya yükler veya bir GitHub repo verirsin.
4. Hangi yapay zekâ(lar)ı kullanmak istediğini seçersin.
5. VaultScan kodu seçtiğin AI sağlayıcı(lar)ına — senin kendi key'inle — gönderir, gelen sonuçları okunabilir bir HTML rapora çevirir.
6. Birden fazla AI seçtiysen, sonuçlar otomatik olarak birleştirilip tek bir rapor haline getirilir.

## Kurulum

Projeyi kendi makinende çalıştırmak için:

```bash
git clone <repo-url>
cd VaultScan

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

`.env.example` dosyasını kopyalayıp kendi `.env` dosyanı oluştur:

```bash
cp .env.example .env
```

`.env` içine kendi değerlerini gir:

| Değişken | Ne işe yarar |
|---|---|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google ile giriş için (Google Cloud Console'dan OAuth Client ID oluştur) |
| `SESSION_SECRET` | Oturum çerezlerini imzalamak için rastgele bir metin (örn. `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ENCRYPTION_KEY` | Kullanıcıların kendi AI API key'lerini veritabanında şifreli saklamak için (örn. `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |

VaultScan'in kendi AI key'i yok — her kullanıcı kendi Claude/ChatGPT/Gemini key'ini uygulama içinden (`/settings`) girer, `.env`'e AI key'i eklemene gerek yok.

Sunucuyu başlat:

```bash
uvicorn main:app --reload
```

Tarayıcıda `http://localhost:8000` adresini aç.

## Testleri çalıştırma

```bash
pytest
```

Testler kendi izole veritabanı dosyasını kullanır, gerçek verine dokunmaz.

## Teknoloji yığını

- **Backend:** FastAPI (Python)
- **Veritabanı:** SQLite + SQLAlchemy
- **Kimlik doğrulama:** Google OAuth (Authlib) + imzalı oturum çerezleri
- **Yapay zekâ sağlayıcıları:** Anthropic (Claude), OpenAI (ChatGPT), Google (Gemini)
- **Frontend:** Düz HTML/CSS/JavaScript (framework yok, basit tutuldu)

## Proje yapısı

```
VaultScan/
├── main.py              # FastAPI route'ları (analyze, upload, github, auth, API key yönetimi vs.)
├── analyzer.py          # Tek/çoklu AI analiz akışı, sonuçları birleştirme mantığı
├── db.py                # SQLAlchemy modelleri (User) ve veritabanı yardımcıları
├── auth.py              # Google OAuth istemcisi
├── config.py            # Ortam değişkenlerini okuyan ayar dosyası
├── prompts.py           # AI'lara gönderilen sistem promptları
├── providers/           # Her AI sağlayıcı için ayrı modül (claude/chatgpt/gemini)
├── static/              # Frontend (HTML/CSS/JS, /settings sayfası dahil)
└── tests/               # pytest test paketi
```

## Yol haritası

VaultScan aktif geliştiriliyor. Şu an üzerinde çalışılan/planlanan konular:

- Arayüz iyileştirmeleri
- Ödeme/abonelik entegrasyonu (şu an beklemede — bkz. proje notları)

## Lisans

Bu proje şu an özel (private) geliştirme aşamasındadır.
