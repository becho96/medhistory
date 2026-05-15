"""Document upload and in-chat browsing."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

import config
import formatting
import keyboards
import texts
from api_client import ApiClient, ApiError

router = Router()
logger = logging.getLogger("medbot.documents")


def _ext(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot != -1 else ""


def _reason(detail) -> str:
    if isinstance(detail, dict):
        return detail.get("reason") or detail.get("code") or "неизвестная причина"
    return str(detail)


# ── Receiving files ──────────────────────────────────────────────────────────

@router.message(F.document)
async def on_document(message: Message, state: FSMContext) -> None:
    doc = message.document
    filename = doc.file_name or f"document_{doc.file_unique_id}.pdf"
    if _ext(filename) not in config.ALLOWED_EXTENSIONS:
        await message.answer(texts.FILE_BAD_TYPE)
        return
    if doc.file_size and doc.file_size > config.MAX_FILE_SIZE:
        await message.answer(texts.FILE_TOO_BIG)
        return
    await _offer_upload(message, state, doc.file_id, filename)


@router.message(F.photo)
async def on_photo(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    await _offer_upload(message, state, photo.file_id,
                        f"photo_{photo.file_unique_id}.jpg")


async def _offer_upload(message: Message, state: FSMContext,
                        file_id: str, filename: str) -> None:
    data = await state.get_data()
    pending = data.get("pending_files", {})
    seq = data.get("upload_seq", 0) + 1
    pending[str(seq)] = {"file_id": file_id, "filename": filename}
    await state.update_data(pending_files=pending, upload_seq=seq)
    await message.answer(
        texts.UPLOAD_OFFER.format(filename=formatting.esc(filename)),
        reply_markup=keyboards.upload_confirm_kb(seq),
    )


# ── Upload confirmation ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("up:no:"))
async def upload_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    seq = cb.data.split(":")[2]
    data = await state.get_data()
    pending = data.get("pending_files", {})
    pending.pop(seq, None)
    await state.update_data(pending_files=pending)
    await cb.message.edit_text(texts.UPLOAD_CANCELLED)


@router.callback_query(F.data.startswith("up:ok:"))
async def upload_confirm(cb: CallbackQuery, state: FSMContext, api: ApiClient) -> None:
    await cb.answer()
    seq = cb.data.split(":")[2]
    data = await state.get_data()
    pending = data.get("pending_files", {})
    entry = pending.pop(seq, None)
    await state.update_data(pending_files=pending)
    if not entry:
        await cb.message.edit_text(texts.UPLOAD_EXPIRED)
        return

    await cb.message.edit_text(texts.UPLOAD_PROCESSING)
    profile_id = data.get("active_profile_id")

    buffer = await cb.bot.download(entry["file_id"])
    content = buffer.read()

    try:
        result = await api.upload_document(
            cb.from_user.id, entry["filename"], content, profile_id)
    except ApiError as exc:
        await cb.message.edit_text(_upload_error(exc))
        return

    await _report_result(cb, api, str(result.get("document_id")), profile_id)


def _upload_error(exc: ApiError) -> str:
    if exc.status_code == 402:
        return texts.UPLOAD_QUOTA
    if exc.status_code == 400:
        return texts.UPLOAD_REJECTED.format(reason=formatting.esc(_reason(exc.detail)))
    logger.warning("Upload failed: %s %s", exc.status_code, exc.detail)
    return texts.ERROR_GENERIC


async def _report_result(cb: CallbackQuery, api: ApiClient,
                         document_id: str, profile_id) -> None:
    """Upload is synchronous, so the document is already analysed here."""
    try:
        doc = await api.get_document(cb.from_user.id, document_id, profile_id)
    except ApiError:
        await cb.message.edit_text(texts.UPLOAD_DONE_BASIC)
        return

    if doc.get("processing_status") == "failed":
        await cb.message.edit_text(texts.UPLOAD_DONE_FAILED)
        return

    text = texts.UPLOAD_DONE.format(dtype=formatting.esc(doc.get("document_type") or "—"))
    if doc.get("document_type") == "Результаты анализа":
        try:
            labs = await api.get_labs(cb.from_user.id, document_id, profile_id)
            section = formatting.abnormal_section(labs.get("lab_results", []))
            if section:
                text = formatting.clip(text + "\n" + section)
        except ApiError:
            pass
    await cb.message.edit_text(
        text, reply_markup=keyboards.document_actions_kb(document_id))


# ── Browsing ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("docs:list:"))
async def docs_list(cb: CallbackQuery, state: FSMContext, api: ApiClient) -> None:
    await cb.answer()
    page = int(cb.data.split(":")[2])
    data = await state.get_data()
    docs = await api.list_documents(cb.from_user.id, data.get("active_profile_id"))
    if not docs:
        await cb.message.answer(texts.DOCS_EMPTY, reply_markup=keyboards.back_to_menu_kb())
        return
    text = texts.DOCS_LIST_HEADER.format(total=len(docs))
    markup = keyboards.documents_kb(docs, page)
    try:
        await cb.message.edit_text(text, reply_markup=markup)
    except Exception:
        await cb.message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("docs:view:"))
async def docs_view(cb: CallbackQuery, state: FSMContext, api: ApiClient) -> None:
    await cb.answer()
    document_id = cb.data.split(":", 2)[2]
    data = await state.get_data()
    doc = await api.get_document(
        cb.from_user.id, document_id, data.get("active_profile_id"))
    await cb.message.answer(
        formatting.document_card(doc),
        reply_markup=keyboards.document_actions_kb(document_id),
    )


@router.callback_query(F.data.startswith("docs:file:"))
async def docs_file(cb: CallbackQuery, state: FSMContext, api: ApiClient) -> None:
    await cb.answer(texts.DOWNLOADING)
    document_id = cb.data.split(":", 2)[2]
    data = await state.get_data()
    profile_id = data.get("active_profile_id")
    doc = await api.get_document(cb.from_user.id, document_id, profile_id)
    content = await api.download_file(cb.from_user.id, document_id, profile_id)
    filename = doc.get("original_filename") or f"document.{doc.get('file_type', 'bin')}"
    await cb.message.answer_document(BufferedInputFile(content, filename=filename))
