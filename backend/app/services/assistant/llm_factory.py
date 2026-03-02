"""
LLM factory: create a LangChain chat model for the configured provider.

Supported providers:
  - "anthropic"  → Claude (claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5)
  - "openrouter" → OpenRouter-proxied models (google/gemini-2.5-flash, etc.)
"""
from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config import settings

# Available models shown in the frontend ModelSelector
AVAILABLE_MODELS: dict[str, list[dict]] = {
    "anthropic": [
        {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (recommended)"},
        {"id": "claude-opus-4-6",   "label": "Claude Opus 4.6 (most capable)"},
        {"id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5 (fastest)"},
    ],
    "openrouter": [
        {"id": "google/gemini-2.5-flash", "label": "Gemini 2.5 Flash"},
    ],
}


def get_llm(provider: str | None = None, model_id: str | None = None) -> BaseChatModel:
    """
    Return a streaming-enabled LangChain chat model.

    Args:
        provider: "anthropic" or "openrouter". Defaults to settings.ASSISTANT_PROVIDER.
        model_id: Model identifier within the provider.
                  Defaults to settings.ASSISTANT_MODEL.
    """
    provider = provider or settings.ASSISTANT_PROVIDER
    model_id = model_id or settings.ASSISTANT_MODEL

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_id,
            api_key=settings.ANTHROPIC_API_KEY,
            streaming=True,
            max_tokens=4096,
        )

    # OpenRouter — OpenAI-compatible endpoint
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model_id,
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
        streaming=True,
        max_tokens=4096,
    )
