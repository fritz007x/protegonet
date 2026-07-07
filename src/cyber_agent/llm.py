from __future__ import annotations

from typing import Any

from .config import settings, gemini_credentials_present

_llm_cache: dict[tuple[str, float], _GeminiLLM] = {}  # (model_id, temperature) → instance


def _temperature(agent: str) -> float:
    return 0.0 if agent == "orchestrator" else 0.2


def make_llm(agent: str = "default", model_id: str | None = None):
    """Build a Gemini chat LLM. Falls back to a deterministic stub when credentials are absent.

    The stub lets us run unit tests and local smoke flows without hitting the API.
    """
    if not gemini_credentials_present():
        return _StubLLM(agent=agent)

    from langchain_google_genai import ChatGoogleGenerativeAI  # lazy import

    resolved = model_id or settings.gemini_model_id
    temp = _temperature(agent)
    key = (resolved, temp)
    if key not in _llm_cache:
        chat = ChatGoogleGenerativeAI(
            model=resolved,
            google_api_key=settings.gemini_api_key,
            temperature=temp,
        )
        _llm_cache[key] = _GeminiLLM(chat)
    return _llm_cache[key]


def make_embeddings():
    if not gemini_credentials_present():
        return _StubEmbeddings()

    from langchain_google_genai import GoogleGenerativeAIEmbeddings  # lazy import

    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model_id,
        google_api_key=settings.gemini_api_key,
    )


class _GeminiLLM:
    """Thin wrapper so callers receive a plain string from .invoke(), matching _StubLLM."""

    def __init__(self, chat_model: Any):
        self._m = chat_model

    @property
    def temperature(self) -> float:
        return self._m.temperature

    def invoke(self, prompt: str, **_: Any) -> str:
        return self._m.invoke(prompt).content

    def __call__(self, prompt: str, **kw: Any) -> str:
        return self.invoke(prompt, **kw)


class _StubLLM:
    def __init__(self, agent: str):
        self.agent = agent

    def invoke(self, prompt: str, **_: Any) -> str:
        return f"[stub-{self.agent}] {prompt[:120]}"

    def __call__(self, prompt: str, **kw: Any) -> str:
        return self.invoke(prompt, **kw)


class _StubEmbeddings:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 7)] * 8 for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text) % 7)] * 8
