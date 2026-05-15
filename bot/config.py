"""Bot configuration, read from environment variables."""
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
BOT_SECRET = os.environ["BOT_SECRET"]

BACKEND_URL = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000").rstrip("/")
API_PREFIX = "/api/v1"

# URL opened by the "open app" buttons. A Telegram Mini App requires HTTPS;
# keyboards fall back to a callback notice when this is not an https:// URL.
MINIAPP_URL = os.getenv("MINIAPP_URL", "https://medhistory.ru")

# Where the legal markdown is fetched from to compute consent hashes and where
# the user-facing links point. Defaults to the public site so the bot records
# the canonical published version of each document.
LEGAL_BASE_URL = os.getenv("LEGAL_BASE_URL", "https://medhistory.ru").rstrip("/")

# Mirrors the backend's ALLOWED_EXTENSIONS / MAX_FILE_SIZE so the bot can
# reject bad files before uploading.
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# Consents collected during onboarding. Data-driven so the 152-ФЗ
# cross-border-transfer consent can be added later by appending one entry
# (a new key + its document) — no changes to the onboarding flow needed.
# document_version is pinned as sha256 of the joined documents, exactly like
# web registration.
CONSENT_JOIN = "\n---\n"
CONSENT_DEFS = [
    {
        "key": "terms_and_privacy",
        "docs": [
            {"path": "/legal/terms-of-service.md", "name": "Пользовательское соглашение"},
            {"path": "/legal/privacy-policy.md", "name": "Политика конфиденциальности"},
        ],
    },
    {
        "key": "special_category",
        "docs": [
            {"path": "/legal/consent.md", "name": "Согласие на обработку медицинских данных"},
        ],
    },
]
