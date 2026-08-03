from collections.abc import Callable

from app.llm.audited_model import AuditedModelProvider, ModelAuditEvent
from app.llm.domain import ModelProvider
from app.llm.fallback_model import FallbackModelProvider
from app.llm.gemini_provider import GeminiModelProvider
from app.llm.internal_provider import InternalControlledModelProvider
from app.llm.model_registry import ModelRegistry, ModelSpec
from app.llm.openai_compatible_provider import (
    HttpClient,
    OpenAICompatibleChatModelProvider,
)
from app.llm.resilient_model import ResilientModelProvider

INTERNAL_PROVIDER = "internal"
CONTROLLED_RESPONSE_MODEL = "controlled-response"
OPENAI_COMPATIBLE_PROVIDER = "openai-compatible"
GEMINI_PROVIDER = "gemini"
GROQ_PROVIDER = "groq"
DEFAULT_OPENAI_COMPATIBLE_BASE_URL = "https://api.openai.com/v1"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def create_model_provider(
    provider_chain: str,
    audit_sink: Callable[[ModelAuditEvent], None] | None = None,
    openai_compatible_api_key: str | None = None,
    openai_compatible_base_url: str = DEFAULT_OPENAI_COMPATIBLE_BASE_URL,
    gemini_api_key: str | None = None,
    gemini_base_url: str = DEFAULT_GEMINI_BASE_URL,
    groq_api_key: str | None = None,
    groq_base_url: str = DEFAULT_GROQ_BASE_URL,
    http_client: HttpClient | None = None,
) -> ModelProvider:
    registry = ModelRegistry.from_chain(provider_chain)
    providers = tuple(
        ResilientModelProvider(
            provider=AuditedModelProvider(
                provider=_create_single_provider(
                    spec,
                    openai_compatible_api_key=openai_compatible_api_key,
                    openai_compatible_base_url=openai_compatible_base_url,
                    gemini_api_key=gemini_api_key,
                    gemini_base_url=gemini_base_url,
                    groq_api_key=groq_api_key,
                    groq_base_url=groq_base_url,
                    http_client=http_client,
                ),
                audit_sink=audit_sink,
            ),
        )
        for spec in (registry.primary, *registry.fallbacks)
    )
    if len(providers) == 1:
        return providers[0]
    return FallbackModelProvider(providers)


def _create_single_provider(
    spec: ModelSpec,
    openai_compatible_api_key: str | None,
    openai_compatible_base_url: str,
    gemini_api_key: str | None,
    gemini_base_url: str,
    groq_api_key: str | None,
    groq_base_url: str,
    http_client: HttpClient | None,
) -> ModelProvider:
    if (
        spec.provider_name == INTERNAL_PROVIDER
        and spec.model_name == CONTROLLED_RESPONSE_MODEL
    ):
        return InternalControlledModelProvider()
    if spec.provider_name == OPENAI_COMPATIBLE_PROVIDER:
        if not openai_compatible_api_key:
            raise ValueError("openai-compatible api key is required")
        return OpenAICompatibleChatModelProvider(
            provider_name=OPENAI_COMPATIBLE_PROVIDER,
            model_name=spec.model_name,
            api_key=openai_compatible_api_key,
            base_url=openai_compatible_base_url,
            http_client=http_client,
        )
    if spec.provider_name == GEMINI_PROVIDER:
        if not gemini_api_key:
            raise ValueError("gemini api key is required")
        return GeminiModelProvider(
            model_name=spec.model_name,
            api_key=gemini_api_key,
            base_url=gemini_base_url,
            http_client=http_client,
        )
    if spec.provider_name == GROQ_PROVIDER:
        if not groq_api_key:
            raise ValueError("groq api key is required")
        return OpenAICompatibleChatModelProvider(
            provider_name=GROQ_PROVIDER,
            model_name=spec.model_name,
            api_key=groq_api_key,
            base_url=groq_base_url,
            http_client=http_client,
        )
    raise ValueError(
        f"unsupported model provider until adapter exists: "
        f"{spec.provider_name}:{spec.model_name}",
    )
