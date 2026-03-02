"""LangGraph state definition for the medical AI assistant."""
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MedicalAssistantState(TypedDict):
    # Conversation history — LangGraph's add_messages reducer handles appending
    messages: Annotated[list[BaseMessage], add_messages]

    # Authentication context
    user_id: str
    session_id: str

    # Model selection sent by the client (provider + model_id)
    model_config: dict  # {"provider": "anthropic", "model_id": "claude-sonnet-4-6"}

    # Patient demographic info loaded once at session start
    patient_profile: dict  # {full_name, gender, age}

    # Supervisor output
    intent: str     # one of: lab_analysis | health_trends | health_history |
                    #         doctor_recommendation | general_qa
    tool_params: dict  # date ranges, analyte names, etc. extracted by supervisor

    # Raw data retrieved from the database
    retrieved_data: dict  # {lab_results, doctor_visits, health_events, interpretations}
