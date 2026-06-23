import os
from dotenv import load_dotenv

load_dotenv()

MAX_TOKENS = 4096

MODEL = "claude-sonnet-4-6"
OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-2.5-flash"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
