"""Onboarding: /start, consent capture, account linking."""
import logging

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

import config
import keyboards
import texts
from api_client import ApiClient, ApiError
from legal import compute_consents
from states import LinkAccount

router = Router()
logger = logging.getLogger("medbot.start")


def _full_name(user) -> str:
    parts = [user.first_name, user.last_name]
    return " ".join(p for p in parts if p) or (user.username or "Пользователь")


def _consent_docs_block() -> str:
    lines = []
    for definition in config.CONSENT_DEFS:
        for doc in definition["docs"]:
            url = config.LEGAL_BASE_URL + doc["path"]
            lines.append(f'• <a href="{url}">{doc["name"]}</a>')
    return "\n".join(lines)


async def _maybe_offer_promo(message: Message, state: FSMContext) -> None:
    """If /start carried a deep-link promo code, offer to activate it."""
    data = await state.get_data()
    payload = data.get("deep_link")
    if not payload or payload.startswith("ref_"):
        return
    await message.answer(
        texts.PROMO_OFFER.format(code=payload),
        reply_markup=keyboards.promo_offer_kb(payload),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject,
                    state: FSMContext, api: ApiClient) -> None:
    await state.clear()
    payload = (command.args or "").strip()
    if payload:
        await state.update_data(deep_link=payload)

    auth = await api.resolve(message.from_user.id)
    if auth:
        await message.answer(
            texts.WELCOME_BACK.format(
                name=auth.get("full_name") or _full_name(message.from_user)),
            reply_markup=keyboards.main_menu_kb(),
        )
        await _maybe_offer_promo(message, state)
        return

    await message.answer(
        texts.CONSENT_SCREEN.format(docs=_consent_docs_block()),
        reply_markup=keyboards.consent_kb(),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(F.data == "consent:accept")
async def consent_accept(cb: CallbackQuery, state: FSMContext, api: ApiClient) -> None:
    await cb.answer()
    await cb.message.edit_text(texts.CREATING_ACCOUNT)

    try:
        consents = await compute_consents()
    except Exception as exc:
        logger.error("Could not fetch legal documents: %s", exc)
        await cb.message.edit_text(texts.ERROR_LEGAL)
        return

    auth = await api.register(cb.from_user.id, _full_name(cb.from_user), consents)
    logger.info("Registered Telegram user via bot | user_id=%s", auth.get("user_id"))

    await cb.message.edit_text(texts.REGISTERED)
    await cb.message.answer(texts.MENU, reply_markup=keyboards.main_menu_kb())
    await _maybe_offer_promo(cb.message, state)


@router.callback_query(F.data == "consent:link")
async def consent_link(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await state.set_state(LinkAccount.awaiting_email)
    await cb.message.answer(texts.LINK_ASK_EMAIL)


@router.message(LinkAccount.awaiting_email, F.text)
async def link_email(message: Message, state: FSMContext) -> None:
    await state.update_data(link_email=message.text.strip())
    await state.set_state(LinkAccount.awaiting_password)
    await message.answer(texts.LINK_ASK_PASSWORD)


@router.message(LinkAccount.awaiting_password, F.text)
async def link_password(message: Message, state: FSMContext, api: ApiClient) -> None:
    data = await state.get_data()
    email = data.get("link_email", "")
    password = message.text.strip()

    # Best-effort: drop the message that contained the password.
    try:
        await message.delete()
    except Exception:
        pass

    try:
        auth = await api.link(message.from_user.id, email, password)
    except ApiError:
        await state.set_state(LinkAccount.awaiting_email)
        await message.answer(texts.LINK_FAILED)
        await message.answer(texts.LINK_ASK_EMAIL)
        return

    await state.set_state(None)
    await message.answer(
        texts.LINK_SUCCESS.format(name=auth.get("full_name") or ""),
        reply_markup=keyboards.main_menu_kb(),
    )
