import json
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings


class AIProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
    ) -> dict:
        """Returns {"content": str | None, "tool_calls": [{"name": str, "arguments": dict}]}"""
        ...

    @abstractmethod
    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Ask the model for a single JSON object matching the schema described
        in system_prompt.
        """
        ...

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]] | None:
        """Returns one embedding vector per input text."""
        return None


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")

        if text.startswith("json"):
            text = text[4:]

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])

            except json.JSONDecodeError:
                pass

        return {}


class OpenAICompatibleProvider(AIProvider):
    """
    Works with OpenAI or any OpenAI-compatible API.

    Examples:
    - OpenAI
    - Groq
    - Ollama OpenAI-compatible endpoint
    - vLLM
    """

    def __init__(self):
        self.base_url = settings.OPENAI_BASE_URL.rstrip("/")
        self.model = settings.OPENAI_MODEL
        self.api_key = settings.OPENAI_API_KEY

    async def chat(
        self,
        system_prompt,
        messages,
        tools=None,
    ) -> dict:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages,
            ],
        }

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": tool,
                }
                for tool in tools
            ]

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            resp.raise_for_status()

            data = resp.json()

        message = data["choices"][0]["message"]

        content = message.get("content") or ""

        tool_calls = []

        for call in message.get("tool_calls") or []:
            fn = call.get("function", {})

            args = fn.get("arguments", "{}")

            if isinstance(args, str):
                args = _extract_json(args)

            tool_calls.append(
                {
                    "name": fn.get("name", ""),
                    "arguments": args,
                }
            )

        return {
            "content": content or None,
            "tool_calls": tool_calls,
        }

    async def complete_json(
        self,
        system_prompt,
        user_prompt,
    ) -> dict[str, Any]:

        result = await self.chat(
            system_prompt
            + "\nRespond with ONLY a raw JSON object, "
            "no prose, no markdown fences.",
            [
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
        )

        return _extract_json(
            result.get("content") or ""
        )

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]] | None:

        if not texts:
            return []

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "text-embedding-3-small",
                    "input": texts,
                },
            )

            if resp.status_code != 200:
                return None

            data = resp.json()

        return [
            row["embedding"]
            for row in sorted(
                data["data"],
                key=lambda r: r["index"],
            )
        ]


class AnthropicProvider(AIProvider):

    def __init__(self):
        self.model = settings.ANTHROPIC_MODEL
        self.api_key = settings.ANTHROPIC_API_KEY

    async def chat(
        self,
        system_prompt,
        messages,
        tools=None,
    ) -> dict:

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": messages,
        }

        if tools:
            payload["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool.get(
                        "description",
                        "",
                    ),
                    "input_schema": tool["parameters"],
                }
                for tool in tools
            ]

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key or "",
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )

            resp.raise_for_status()

            data = resp.json()

        content_text = ""
        tool_calls = []

        for block in data.get("content", []):

            if block["type"] == "text":
                content_text += block["text"]

            elif block["type"] == "tool_use":
                tool_calls.append(
                    {
                        "name": block["name"],
                        "arguments": block.get(
                            "input",
                            {},
                        ),
                    }
                )

        return {
            "content": content_text or None,
            "tool_calls": tool_calls,
        }

    async def complete_json(
        self,
        system_prompt,
        user_prompt,
    ) -> dict[str, Any]:

        result = await self.chat(
            system_prompt
            + "\nRespond with ONLY a raw JSON object, "
            "no prose, no markdown fences.",
            [
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
        )

        return _extract_json(
            result.get("content") or ""
        )


class OllamaProvider(AIProvider):

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL

    async def chat(
        self,
        system_prompt,
        messages,
        tools=None,
    ) -> dict:

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages,
            ],
            "stream": False,
        }

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": tool,
                }
                for tool in tools
            ]

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )

                resp.raise_for_status()

                data = resp.json()

            except (httpx.HTTPError, httpx.ConnectError):
                return {
                    "content": (
                        "Ollama is not running. "
                        "Start it with: ollama serve"
                    ),
                    "tool_calls": [],
                }

        message = (
            data.get("choices", [{}])[0]
            .get("message", {})
        )

        if not message.get("content") and tools:

            retry_payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    *messages,
                ],
                "stream": False,
            }

            async with httpx.AsyncClient(
                timeout=120
            ) as retry_client:

                retry_resp = await retry_client.post(
                    f"{self.base_url}/chat/completions",
                    json=retry_payload,
                )

                retry_resp.raise_for_status()

                retry_data = retry_resp.json()

            message = (
                retry_data.get(
                    "choices",
                    [{}],
                )[0].get(
                    "message",
                    {},
                )
            )

        tool_calls = []

        for call in message.get("tool_calls") or []:

            fn = call.get("function", {})

            args = fn.get(
                "arguments",
                "{}",
            )

            if isinstance(args, str):
                args = _extract_json(args)

            tool_calls.append(
                {
                    "name": fn.get("name", ""),
                    "arguments": args,
                }
            )

        return {
            "content": message.get("content"),
            "tool_calls": tool_calls,
        }

    async def complete_json(
        self,
        system_prompt,
        user_prompt,
    ) -> dict[str, Any]:

        result = await self.chat(
            system_prompt
            + "\nRespond with ONLY a raw JSON object, "
            "no prose, no markdown fences.",
            [
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
        )

        return _extract_json(
            result.get("content") or ""
        )


class HeuristicOnlyProvider(AIProvider):

    async def chat(
        self,
        system_prompt,
        messages,
        tools=None,
    ) -> dict:

        return {
            "content": (
                "AI provider is not configured. "
                "Set AI_PROVIDER and API key."
            ),
            "tool_calls": [],
        }

    async def complete_json(
        self,
        system_prompt,
        user_prompt,
    ) -> dict[str, Any]:

        return {}


def get_ai_provider() -> AIProvider:

    # OpenAI или Groq
    if (
        settings.AI_PROVIDER in ("openai", "groq")
        and settings.OPENAI_API_KEY
    ):
        return OpenAICompatibleProvider()

    # Anthropic / Claude
    if (
        settings.AI_PROVIDER == "anthropic"
        and settings.ANTHROPIC_API_KEY
    ):
        return AnthropicProvider()

    # Local Ollama
    if settings.AI_PROVIDER == "ollama":
        return OllamaProvider()

    # Если ничего не настроено
    return HeuristicOnlyProvider()
