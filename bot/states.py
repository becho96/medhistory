"""Aiogram FSM states (in-memory storage)."""
from aiogram.fsm.state import State, StatesGroup


class LinkAccount(StatesGroup):
    """Linking a Telegram user to an existing email/password account."""
    awaiting_email = State()
    awaiting_password = State()


class AssistantChat(StatesGroup):
    """User is in a free-form dialogue with the AI assistant."""
    active = State()


class PromoEntry(StatesGroup):
    """User is typing a promo code."""
    awaiting_code = State()
