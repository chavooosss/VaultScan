import os
from dotenv import load_dotenv

load_dotenv()

MAX_TOKENS = 4096
PROVIDER_TIMEOUT_SECONDS = 90

MODEL = "claude-sonnet-4-6"
OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-2.5-flash"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET ortam değişkeni ayarlanmamış — oturumlar güvensiz olur.")
if not ENCRYPTION_KEY:
    raise RuntimeError("ENCRYPTION_KEY ortam değişkeni ayarlanmamış — API key şifrelemesi çalışamaz.")
