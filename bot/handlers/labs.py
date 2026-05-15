"""Lab analyte trends — динамика показателя."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

import formatting
import keyboards
import texts
from api_client import ApiClient

router = Router()


@router.callback_query(F.data == "labs:analytes")
async def labs_analytes(cb: CallbackQuery, state: FSMContext, api: ApiClient) -> None:
    await cb.answer()
    data = await state.get_data()
    payload = await api.list_analytes(cb.from_user.id, data.get("active_profile_id"))
    flat = [
        {"name": analyte["canonical_name"]}
        for category in payload.get("categories", [])
        for analyte in category.get("analytes", [])
    ]
    if not flat:
        await cb.message.answer(texts.LABS_EMPTY, reply_markup=keyboards.back_to_menu_kb())
        return
    await state.update_data(analytes=flat)
    await cb.message.answer(texts.LABS_PICK, reply_markup=keyboards.analytes_kb(flat, 0))


@router.callback_query(F.data.startswith("labs:pg:"))
async def labs_page(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    page = int(cb.data.split(":")[2])
    data = await state.get_data()
    await cb.message.edit_reply_markup(
        reply_markup=keyboards.analytes_kb(data.get("analytes", []), page))


@router.callback_query(F.data.startswith("labs:ts:"))
async def labs_timeseries(cb: CallbackQuery, state: FSMContext, api: ApiClient) -> None:
    await cb.answer()
    idx = int(cb.data.split(":")[2])
    data = await state.get_data()
    flat = data.get("analytes", [])
    if idx >= len(flat):
        await cb.message.answer(texts.SESSION_EXPIRED, reply_markup=keyboards.back_to_menu_kb())
        return
    series = await api.get_timeseries(
        cb.from_user.id, flat[idx]["name"], data.get("active_profile_id"))
    await cb.message.answer(
        formatting.timeseries_text(series),
        reply_markup=keyboards.back_to_menu_kb(),
    )
