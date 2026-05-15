"""MedHistory Telegram bot — entrypoint (long-polling)."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand,
    ErrorEvent,
    MenuButtonCommands,
    MenuButtonWebApp,
    WebAppInfo,
)

import config
import texts
from api_client import ApiClient, ApiError, NotLinkedError
from handlers import assistant, documents, family, labs, menu, start, subscription

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("medbot")


async def _setup_bot(bot: Bot) -> None:
    """Register slash commands and the persistent Mini App menu button."""
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск / главное меню"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="help", description="Помощь"),
    ])
    if config.MINIAPP_URL.startswith("https://"):
        try:
            await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(
                text="Открыть MedHistory",
                web_app=WebAppInfo(url=config.MINIAPP_URL),
            ))
        except Exception as exc:  # non-fatal — bot still works without it
            logger.warning("Could not set Mini App menu button: %s", exc)
    else:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


def _register_error_handler(dp: Dispatcher) -> None:
    @dp.error()
    async def on_error(event: ErrorEvent, bot: Bot) -> None:
        """Central safety net: turn known errors into friendly messages."""
        exc = event.exception
        update = event.update

        chat_id = None
        if update.message:
            chat_id = update.message.chat.id
        elif update.callback_query and update.callback_query.message:
            chat_id = update.callback_query.message.chat.id
            try:
                await update.callback_query.answer()
            except Exception:
                pass

        if isinstance(exc, NotLinkedError):
            message = texts.NOT_LINKED
        elif isinstance(exc, ApiError):
            logger.warning("API error %s: %s", exc.status_code, exc.detail)
            message = texts.ERROR_GENERIC
        else:
            logger.exception("Unhandled error", exc_info=exc)
            message = texts.ERROR_GENERIC

        if chat_id is not None:
            try:
                await bot.send_message(chat_id, message)
            except Exception:
                pass


async def main() -> None:
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    api = ApiClient()

    dp = Dispatcher()
    dp["api"] = api  # injected into handlers by parameter name

    for module in (start, menu, documents, labs, assistant, family, subscription):
        dp.include_router(module.router)
    _register_error_handler(dp)

    await _setup_bot(bot)
    logger.info("MedHistory bot started (long-polling)")
    try:
        await dp.start_polling(bot)
    finally:
        await api.aclose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
