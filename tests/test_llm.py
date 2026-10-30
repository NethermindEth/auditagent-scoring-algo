"""Tests for LLM client helpers, guard rails, and both OpenAI SDK call paths (offline)."""

from __future__ import annotations

import json

import httpx2
import pytest
from openai import AsyncOpenAI

from scoring_algo.core import llm
from scoring_algo.core.types import Finding

FINDING = {
    "is_match": True,
    "is_partial_match": False,
    "explanation": "same root cause",
    "severity_from_junior_auditor": "High",
    "severity_from_truth": "High",
    "index_of_finding_from_junior_auditor": 3,
}


def _fake_openai(request: httpx2.Request) -> httpx2.Response:
    """Canned OpenAI replies carrying a serialized ``Finding`` for both endpoints."""
    body = json.loads(request.content)
    text = json.dumps(FINDING)
    if request.url.path.endswith("/chat/completions"):
        assert body["messages"] == [{"role": "user", "content": "prompt"}]
        payload = {
            "id": "c1",
            "object": "chat.completion",
            "created": 0,
            "model": body["model"],
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": text},
                }
            ],
        }
    else:
        assert request.url.path.endswith("/responses")
        assert body["input"] == [{"role": "user", "content": "prompt"}]
        payload = {
            "id": "r1",
            "object": "response",
            "created_at": 0,
            "model": body["model"],
            "status": "completed",
            "parallel_tool_calls": True,
            "tool_choice": "auto",
            "tools": [],
            "output": [
                {
                    "type": "message",
                    "id": "m1",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": text, "annotations": []}],
                }
            ],
        }
    return httpx2.Response(200, json=payload)


def test_count_tokens():
    assert llm.count_tokens("") == 0
    assert llm.count_tokens("hello world") > 0


def test_unsupported_model_raises_value_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(ValueError):
        llm.LLMClient("definitely-not-a-supported-model")


def test_missing_api_key_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        llm.LLMClient("o4-mini")  # supported model, so it reaches the key check


@pytest.mark.parametrize("base_url", [None, "http://fake-openai.test/v1"])
async def test_generate_async_parses_through_sdk(monkeypatch, base_url):
    # Runs the real SDK request/parse path offline, so a breaking openai bump
    # fails here instead of silently turning every judgement into "no result".
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    if base_url:
        monkeypatch.setenv("OPENAI_BASE_URL", base_url)  # chat.completions path
    else:
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)  # responses path
    client = llm.LLMClient("o4-mini")
    client._client = AsyncOpenAI(
        api_key="test-key",
        base_url=base_url or "http://fake-openai.test/v1",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(_fake_openai)),
    )

    result = await client.generate_async("prompt")

    assert result == Finding(**FINDING)
