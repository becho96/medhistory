"""AI assistant proxy — forwards questions to the LangGraph assistant."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import formatting
import keyboards
import texts
from api_client import ApiClient
from states import AssistantChat

router = Router()


@router.callback_query(F.data == "assist:start")
async def assist_start(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await state.set_state(AssistantChat.active)
    await cb.message.answer(texts.ASSIST_PROMPT, reply_markup=keyboards.assistant_exit_kb())


@router.message(AssistantChat.active, F.text)
async def assist_question(message: Message, state: FSMContext, api: ApiClient) -> None:
    question = message.text.strip()
    if not question:
        return

    await message.bot.send_chat_action(message.chat.id, "typing")
    data = await state.get_data()
    result = await api.ask_assistant(
        message.from_user.id, question, data.get("assist_session"))
    await state.update_data(assist_session=result.get("session_id"))

    answer = result.get("answer") or texts.ERROR_GENERIC
    if len(answer) > formatting.TG_MESSAGE_LIMIT:
        answer = answer[:formatting.TG_MESSAGE_LIMIT] + texts.ASSIST_TRUNCATED
    # parse_mode=None — the LLM answer is plain text, not HTML.
    await message.answer(
        answer, parse_mode=None, reply_markup=keyboards.assistant_exit_kb())
