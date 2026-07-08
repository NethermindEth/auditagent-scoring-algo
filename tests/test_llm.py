"""Tests for LLM client helpers and guard rails (unsupported model, missing key)."""

from __future__ import annotations

import pytest

from scoring_algo.core import llm


def test_count_tokens():
    assert llm.count_tokens("") == 0
    assert llm.count_tokens("hello world") > 0


def test_responses_input_from_text():
    assert llm._responses_input_from_text("hi") == [{"role": "user", "content": "hi"}]


def test_unsupported_model_raises_value_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(ValueError):
        llm.LLMClient("definitely-not-a-supported-model")


def test_missing_api_key_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        llm.LLMClient("o4-mini")  # supported model, so it reaches the key check
