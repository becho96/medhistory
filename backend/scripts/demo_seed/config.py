"""Shared constants for the demo-seed scripts (seed + teardown)."""
from __future__ import annotations

from datetime import date

# --- demo owner (the shareable login) ---------------------------------------
OWNER_EMAIL = "demo@medhistory.ru"
OWNER_PASSWORD = "MedHistory2026"
OWNER_NAME = "Соколова Ольга Николаевна"
OWNER_PATIENT = "Соколова О.Н."
OWNER_BIRTH = date(1983, 4, 12)

# --- family member (daughter) -----------------------------------------------
CHILD_NAME = "Соколова София Александровна"
CHILD_PATIENT = "Соколова С.А."
CHILD_BIRTH = date(2019, 6, 20)

# --- 152-ФЗ consent versions (sha256 of the legal markdown, matching the
# frontend Register flow). Recorded so the demo account is a complete record.
CONSENT_HASHES = {
    "terms_and_privacy": "6cb2ebadda5d6293bff0b165d41710dfed504c23e88823ec1b9cbad012816d50",
    "special_category": "8e20afd8d0c8ca6f26954d31df2c4d051db4b995de89ffabe2c405498cc3db1d",
}

# --- the three intentionally-unclosed referrals (for verification) ----------
# (source doc code, title fragment, target specialty/area)
UNCLOSED_REFERRALS = [
    ("A01", "эндокринолог", "Эндокринология"),
    ("A03", "УЗИ органов брюшной полости", "Брюшная полость"),
    ("B01", "сосудист", "Хирургия"),
]
