from functools import cache

from openai import OpenAI

from .config import settings


@cache
def chat_client() -> OpenAI:
    # Ollama ignores the key, but the SDK refuses an empty one.
    return OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key or "unused")


@cache
def judge_client() -> OpenAI:
    # A hung model fails fast instead of stalling a whole eval run.
    return OpenAI(
        base_url=settings.judge_base_url, api_key=settings.judge_api_key or "unused", timeout=60
    )


@cache
def embed_client() -> OpenAI:
    return OpenAI(base_url=settings.embed_base_url, api_key=settings.embed_api_key or "unused")


def embed(texts: list[str]) -> list[list[float]]:
    resp = embed_client().embeddings.create(model=settings.embed_model, input=texts)
    return [d.embedding for d in resp.data]
