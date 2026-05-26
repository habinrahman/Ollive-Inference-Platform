from __future__ import annotations

from functools import lru_cache

from llm_sdk import InferenceClient

from app.core.config import get_settings
from app.services.inference_factory import build_inference_client


@lru_cache
def get_inference_client() -> InferenceClient:
    return build_inference_client(get_settings())
