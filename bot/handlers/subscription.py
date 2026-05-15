"""Subscription status, Pro upsell, and promo codes."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import formatting
import keyboards
import texts
from api_client import ApiClient, ApiError
from states import PromoEntry

router = Router()


@router.callback_query(F.data == "sub:show")
async def sub_show(cb: CallbackQuery, api: ApiClient) -> None:
    await cb.answer()
    sub = await api.get_subscription(cb.from_user.id)
    await cb.message.answer(
        formatting.subscription_text(sub),
        reply_markup=keyboards.subscription_kb(sub.get("tier") == "pro"),
    )


@router.callback_query(F.data == "sub:promo")
async def sub_promo(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await state.set_state(PromoEntry.awaiting_code)
    await cb.message.answer(texts.PROMO_ASK)


@router.message(PromoEntry.awaiting_code, F.text)
async def sub_promo_code(message: Message, state: FSMContext, api: ApiClient) -> None:
    code = message.text.strip()
    await state.set_state(None)
    await _apply_promo(message, api, message.from_user.id, code)


@router.callback_query(F.data.startswith("sub:apply:"))
async def sub_apply(cb: CallbackQuery, api: ApiClient) -> None:
    await cb.answer()
    code = cb.data.split(":", 2)[2]
    await _apply_promo(cb.message, api, cb.from_user.id, code)


async def _apply_promo(message: Message, api: ApiClient,
                       telegram_id: int, code: str) -> None:
    try:
        result = await api.activate_promo(telegram_id, code)
    except ApiError:
        await message.answer(texts.PROMO_FAILED, reply_markup=keyboards.back_to_menu_kb())
        return
    until = str(result.get("activated_until") or "")[:10]
    await message.answer(
        texts.PROMO_SUCCESS.format(until=until),
        reply_markup=keyboards.back_to_menu_kb(),
    )
