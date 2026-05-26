from __future__ import annotations

from llm_sdk import FireAndForgetTelemetryEmitter, HttpTelemetryEmitter, InferenceClient
from llm_sdk.providers import GeminiProvider, OpenAIProvider

from app.core.config import Settings


def build_inference_client(settings: Settings) -> InferenceClient:
    providers = {
        "gemini": GeminiProvider(
            api_key=settings.gemini_api_key,
            allow_mock=settings.allow_mock_provider,
        ),
        "openai": OpenAIProvider(
            api_key=settings.openai_api_key,
            allow_mock=settings.allow_mock_provider,
        ),
    }
    telemetry = FireAndForgetTelemetryEmitter(
        HttpTelemetryEmitter(endpoint=settings.ingestion_endpoint)
    )
    return InferenceClient(
        providers=providers,
        telemetry=telemetry,
        default_provider="gemini",
        default_model=settings.gemini_model,
        default_models={
            "gemini": settings.gemini_model,
            "openai": settings.openai_model,
        },
        max_retries=1,
    )
