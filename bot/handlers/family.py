"""Family profile switching."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

import formatting
import keyboards
import texts
from api_client import ApiClient

router = Router()


@router.callback_query(F.data == "family:list")
async def family_list(cb: CallbackQuery, state: FSMContext, api: ApiClient) -> None:
    await cb.answer()
    profiles = await api.list_profiles(cb.from_user.id)
    if not profiles:
        await cb.message.answer(texts.FAMILY_EMPTY, reply_markup=keyboards.back_to_menu_kb())
        return
    await state.update_data(profiles=profiles)
    data = await state.get_data()
    active = data.get("active_profile_id") or api.user_id(cb.from_user.id)
    await cb.message.answer(
        texts.FAMILY_PICK, reply_markup=keyboards.family_kb(profiles, active))


@router.callback_query(F.data.startswith("family:set:"))
async def family_set(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    idx = int(cb.data.split(":")[2])
    data = await state.get_data()
    profiles = data.get("profiles", [])
    if idx >= len(profiles):
        await cb.message.answer(texts.SESSION_EXPIRED, reply_markup=keyboards.back_to_menu_kb())
        return
    chosen = profiles[idx]
    await state.update_data(
        active_profile_id=str(chosen["id"]),
        active_profile_name=chosen.get("full_name"),
    )
    await cb.message.edit_text(
        texts.FAMILY_SWITCHED.format(name=formatting.esc(chosen.get("full_name"))),
        reply_markup=keyboards.back_to_menu_kb(),
    )
