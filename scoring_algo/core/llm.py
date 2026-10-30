from __future__ import annotations

import json
import os

import tiktoken
from openai import AsyncOpenAI

from ..settings import Settings
from .telemetry import observe, update_generation
from .types import Finding


class LLMClient:
    def __init__(self, model: str):
        self.model = model

        settings = Settings()
        if not any(model in models for models in settings.SUPPORTED_MODELS.values()):
            raise ValueError(f"Unsupported model {model}")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        base_url = os.getenv("OPENAI_BASE_URL") or None
        self._use_base_url = base_url is not None

        # Remove empty OPENAI_BASE_URL from env so the OpenAI SDK doesn't
        # pick it up internally (dotenv loaders set it to "" which the SDK
        # treats as a real value instead of falling back to the default URL).
        if not self._use_base_url and "OPENAI_BASE_URL" in os.environ:
            del os.environ["OPENAI_BASE_URL"]

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @observe(name="[LLM] Send prompt to LLM (async)", as_type="generation")
    async def generate_async(self, prompt: str) -> Finding | None:
        try:
            messages = _responses_input_from_text(prompt)
            parsed_response: Finding | None
            if self._use_base_url:
                completion = await self._client.chat.completions.parse(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=Finding,
                )
                parsed_response = getattr(completion.choices[0].message, "parsed", None)
            else:
                response = await self._client.responses.parse(
                    model=self.model,
                    input=[{"role": "user", "content": prompt}],
                    text_format=Finding,
                )
                parsed_response = getattr(response, "output_parsed", None)
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
            print(f"[LLMPrompt] OpenAI API error (async) for {self.model}: {e}")
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

    enc = tiktoken.get_encoding("o200k_base")
    tokens = enc.encode(text)
    return len(tokens)


def _openai_messages_langfuse(messages: list[dict]) -> str:
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
