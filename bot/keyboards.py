"""Inline keyboards."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

import config
import formatting

DOCS_PAGE_SIZE = 6
ANALYTES_PAGE_SIZE = 8

_MENU = "⬅️ В меню"


def _app_button(text: str) -> InlineKeyboardButton:
    """Mini App button. Telegram only allows web_app buttons over HTTPS, so for
    a non-HTTPS MINIAPP_URL (e.g. local dev) a callback notice is used instead."""
    if config.MINIAPP_URL.startswith("https://"):
        return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=config.MINIAPP_URL))
    return InlineKeyboardButton(text=text, callback_data="menu:app_unavailable")


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_app_button("🩺 Открыть приложение")],
        [InlineKeyboardButton(text="📂 Мои документы", callback_data="docs:list:0")],
        [InlineKeyboardButton(text="💬 Спросить ассистента", callback_data="assist:start")],
        [InlineKeyboardButton(text="📊 Динамика показателя", callback_data="labs:analytes")],
        [InlineKeyboardButton(text="👨‍👩‍👧 Профили", callback_data="family:list")],
        [InlineKeyboardButton(text="⭐ Подписка", callback_data="sub:show")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="menu:help")],
    ])


def consent_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принимаю и продолжаю", callback_data="consent:accept")],
        [InlineKeyboardButton(text="🔗 У меня уже есть аккаунт", callback_data="consent:link")],
    ])


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_MENU, callback_data="menu:open")],
    ])


def upload_confirm_kb(seq: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📤 Отправить на обработку", callback_data=f"up:ok:{seq}"),
        InlineKeyboardButton(text="✖️ Отмена", callback_data=f"up:no:{seq}"),
    ]])


def documents_kb(docs: list, page: int) -> InlineKeyboardMarkup:
    start = page * DOCS_PAGE_SIZE
    chunk = docs[start:start + DOCS_PAGE_SIZE]
    rows = [
        [InlineKeyboardButton(
            text=formatting.document_label(d),
            callback_data=f"docs:view:{d['id']}",
        )]
        for d in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"docs:list:{page - 1}"))
    if start + DOCS_PAGE_SIZE < len(docs):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"docs:list:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=_MENU, callback_data="menu:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def document_actions_kb(document_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Скачать оригинал", callback_data=f"docs:file:{document_id}")],
        [InlineKeyboardButton(text="📂 К списку", callback_data="docs:list:0")],
    ])


def analytes_kb(analytes: list, page: int) -> InlineKeyboardMarkup:
    start = page * ANALYTES_PAGE_SIZE
    chunk = analytes[start:start + ANALYTES_PAGE_SIZE]
    rows = [
        [InlineKeyboardButton(text=a["name"], callback_data=f"labs:ts:{start + i}")]
        for i, a in enumerate(chunk)
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"labs:pg:{page - 1}"))
    if start + ANALYTES_PAGE_SIZE < len(analytes):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"labs:pg:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=_MENU, callback_data="menu:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def family_kb(profiles: list, active_id: str | None) -> InlineKeyboardMarkup:
    rows = []
    for i, p in enumerate(profiles):
        mark = "✓ " if str(p.get("id")) == str(active_id) else ""
        rows.append([InlineKeyboardButton(
            text=f"{mark}{p.get('full_name') or 'Профиль'}",
            callback_data=f"family:set:{i}",
        )])
    rows.append([InlineKeyboardButton(text=_MENU, callback_data="menu:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def assistant_exit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Завершить диалог", callback_data="menu:open")],
    ])


def subscription_kb(is_pro: bool) -> InlineKeyboardMarkup:
    rows = [[_app_button("⭐ Управление подпиской")]]
    if not is_pro:
        rows.append([InlineKeyboardButton(text="🎁 Ввести промокод", callback_data="sub:promo")])
    rows.append([InlineKeyboardButton(text=_MENU, callback_data="menu:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def promo_offer_kb(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎁 Активировать «{code}»", callback_data=f"sub:apply:{code}")],
    ])
