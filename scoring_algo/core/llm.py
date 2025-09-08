from __future__ import annotations

import json
import os
from typing import Optional

import tiktoken
from langfuse.openai import OpenAI
from langfuse.types import List

from ..settings import Settings
from .telemetry import observe, update_generation
from .types import Finding


class LLMClient:
    def __init__(self, model: str):
        self.model = model
        self._openai: Optional[OpenAI] = None

        if not self.is_model_supported(model):
            raise ValueError(f"Unsupported model {model}")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._openai = OpenAI(api_key=api_key)

    @observe(name="[LLM] Send prompt to LLM", as_type="generation")
    def generate(self, prompt: str) -> Optional[Finding]:
        return self._generate_openai(prompt)

    @classmethod
    def is_model_supported(cls, model: str) -> bool:
        """Check if a model is supported by any provider."""
        cfg = Settings()
        for models in cfg.SUPPORTED_MODELS.values():
            if model in models:
                return True
        return False

    def _generate_openai(self, prompt: str) -> Optional[Finding]:
        try:
            messages = _responses_input_from_text(prompt)
            response = self._openai.responses.parse(
                model=self.model,
                input=messages,
                text_format=Finding,
            )

            parsed_response: Optional[Finding] = getattr(response, "output_parsed", None)
            input_text = _openai_messages_langfuse(messages)
            output_text = str(parsed_response)
            update_generation(
                model=self.model,
                usage_details={
                    "input": count_tokens(input_text),
                    "output": count_tokens(output_text),
                },
                input=input_text,
                output=output_text,
            )
            return parsed_response
        except Exception as e:
            print(f"[LLMPrompt] OpenAI API error for {self.model}: {e}")
            return None


def _responses_input_from_text(text: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": text,
        }
    ]


def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a text using the configured encoding.

    Args:
        text: The text to count tokens for.

    Returns:
        int: The number of tokens in the text.

    Raises:
        ValidationError: If the text is not a string or if there's an encoding error.
    """

    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    return len(tokens)


def _openai_messages_langfuse(messages: List[dict]) -> str:
    parts: list[str] = []
    for message in messages:
        if isinstance(message, dict):
            role = message.get("role", "user")
            content = message.get("content", "")
        else:
            role = getattr(message, "role", "user")
            content = getattr(message, "content", "")
        if role == "assistant":
            try:
                if isinstance(content, (dict, list)):
                    content_compact = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
                else:
                    content_compact = json.dumps(
                        json.loads(content), ensure_ascii=False, separators=(",", ":")
                    )
            except Exception:
                content_compact = str(content).replace("\n", " ")

            content = f"```json\n{content_compact}\n```"
        parts.append(str(content))
    return "\n\n".join(parts)
