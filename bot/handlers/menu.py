"""Main menu, help, and the unknown-input fallback."""
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards
import texts

router = Router()


async def _open_menu(message: Message, state: FSMContext) -> None:
    # Clear only the FSM state — keep data (active profile, sessions).
    await state.set_state(None)
    await message.answer(texts.MENU, reply_markup=keyboards.main_menu_kb())


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await _open_menu(message, state)


@router.callback_query(F.data == "menu:open")
async def cb_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await _open_menu(cb.message, state)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP, reply_markup=keyboards.back_to_menu_kb())


@router.callback_query(F.data == "menu:help")
async def cb_help(cb: CallbackQuery) -> None:
    await cb.answer()
    await cb.message.answer(texts.HELP, reply_markup=keyboards.back_to_menu_kb())


@router.callback_query(F.data == "menu:app_unavailable")
async def cb_app_unavailable(cb: CallbackQuery) -> None:
    await cb.answer(texts.MINIAPP_UNAVAILABLE, show_alert=True)


@router.message(StateFilter(None), F.text)
async def fallback_text(message: Message) -> None:
    """Any plain text outside a dialogue — nudge the user to the menu."""
    await message.answer(texts.UNKNOWN_INPUT, reply_markup=keyboards.main_menu_kb())
