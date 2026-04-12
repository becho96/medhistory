"""LangGraph state definition for the medical AI assistant."""
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MedicalAssistantState(TypedDict):
    # Conversation history — add_messages reducer handles appending
    messages: Annotated[list[BaseMessage], add_messages]

    # Authentication context
    user_id: str
    session_id: str

    # Model selection sent by the client
    model_config: dict  # {"provider": "openrouter", "model_id": "google/gemini-2.5-flash"}

    # Patient demographic info loaded once per request
    patient_profile: dict  # {full_name, gender, age}
