"""
Anthropic LLM Client Wrapper with Deterministic Record/Replay Caching,
MockLLM Test Runner, Cost Tracking, and Pydantic-Validated Structured Output.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Literal, Type, TypeVar

from pydantic import BaseModel, Field

from backend.app.config import settings

logger = logging.getLogger("trust_analyst.llm")

T = TypeVar("T", bound=BaseModel)

# Sonnet 3.5 Pricing per 1M tokens ($3.00 input, $15.00 output)
PRICE_INPUT_PER_M = 3.00
PRICE_OUTPUT_PER_M = 15.00


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculates approximate USD cost for token usage."""
    return round((input_tokens / 1_000_000 * PRICE_INPUT_PER_M) + (output_tokens / 1_000_000 * PRICE_OUTPUT_PER_M), 6)


class ToolCallItem(BaseModel):
    """Normalized tool call representation."""

    id: str
    name: str
    input: dict[str, Any]


class LLMResponse(BaseModel):
    """Normalized LLM completion result."""

    content: str = ""
    tool_calls: list[ToolCallItem] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    from_cache: bool = False
    stop_reason: str | None = None


class RecordReplayCache:
    """
    Disk-backed deterministic record/replay cache.
    Stores cached responses keyed by SHA256 of (model, system, messages, tools, temperature).
    """

    def __init__(self, cache_dir: str | Path | None = None):
        self.cache_dir = Path(cache_dir or settings.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "cache.jsonl"
        self._memory_cache: dict[str, dict[str, Any]] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Loads cached entries from the JSONL index into memory."""
        if not self.index_file.exists():
            return
        with open(self.index_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    k = entry.get("key")
                    if k:
                        self._memory_cache[k] = entry.get("response", {})
                except Exception as e:
                    logger.debug(f"Failed to read cache line: {e}")

    @staticmethod
    def compute_key(
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
    ) -> str:
        """Computes deterministic SHA256 key for LLM invocation."""
        canonical_payload = {
            "model": model,
            "system": system,
            "messages": messages,
            "tools": tools or [],
            "temperature": round(temperature, 2),
        }
        serialized = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, key: str) -> LLMResponse | None:
        """Retrieves cached response if present."""
        if key in self._memory_cache:
            data = self._memory_cache[key]
            resp = LLMResponse.model_validate(data)
            resp.from_cache = True
            return resp
        return None

    def put(self, key: str, response: LLMResponse) -> None:
        """Persists LLM response to in-memory and disk cache."""
        data = response.model_dump()
        self._memory_cache[key] = data
        with open(self.index_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "response": data}) + "\n")


class MockLLM:
    """Scriptable mock LLM for deterministic offline testing and replay emulation."""

    def __init__(self):
        self._queue: list[LLMResponse] = []
        self.recorded_calls: list[dict[str, Any]] = []

    def queue_response(self, response: LLMResponse) -> None:
        """Enqueues a canned response."""
        self._queue.append(response)

    def queue_tool_call(self, tool_name: str, arguments: dict[str, Any], text: str = "") -> None:
        """Convenience helper to enqueue a tool call."""
        resp = LLMResponse(
            content=text,
            tool_calls=[ToolCallItem(id=f"call-{tool_name}", name=tool_name, input=arguments)],
            input_tokens=150,
            output_tokens=50,
            cost_usd=calculate_cost(150, 50),
            stop_reason="tool_use",
        )
        self._queue.append(resp)

    def queue_text(self, text: str) -> None:
        """Convenience helper to enqueue a text completion."""
        resp = LLMResponse(
            content=text,
            input_tokens=100,
            output_tokens=30,
            cost_usd=calculate_cost(100, 30),
            stop_reason="end_turn",
        )
        self._queue.append(resp)

    def generate(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Returns next queued response or a predictable fallback."""
        self.recorded_calls.append({"system": system, "messages": messages, "tools": tools})
        if self._queue:
            return self._queue.pop(0)

        # Predictable fallback if queue is empty
        return LLMResponse(
            content="Mock investigation response: Analysis complete.",
            tool_calls=[],
            input_tokens=50,
            output_tokens=20,
            cost_usd=calculate_cost(50, 20),
            stop_reason="end_turn",
        )


class LLMClient:
    """Unified LLM interface supporting live Anthropic calls, record/replay cache, and mock execution."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        mode: Literal["live", "replay", "mock"] | None = None,
        cache_dir: str | Path | None = None,
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.mode = mode or settings.LLM_MODE
        self.cache = RecordReplayCache(cache_dir=cache_dir)
        self.mock = MockLLM()
        self._anthropic_client = None

    def _get_anthropic_client(self):
        if self._anthropic_client is None:
            import anthropic

            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY is required for live LLM mode.")
            self._anthropic_client = anthropic.Anthropic(api_key=self.api_key)
        return self._anthropic_client

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Executes an LLM completion according to current LLM_MODE:
        - 'mock': delegates to MockLLM
        - 'replay': serves strictly from disk cache (fails loudly on miss)
        - 'live': serves from cache on hit, otherwise calls Anthropic API and records to cache
        """
        if self.mode == "mock":
            return self.mock.generate(system=system, messages=messages, tools=tools)

        cache_key = RecordReplayCache.compute_key(
            model=self.model,
            system=system,
            messages=messages,
            tools=tools,
            temperature=temperature,
        )

        cached_resp = self.cache.get(cache_key)
        if cached_resp is not None:
            return cached_resp

        if self.mode == "replay":
            raise KeyError(
                f"Replay cache miss for key {cache_key}. "
                f"In replay mode, all completions must be pre-recorded in {self.cache.index_file}."
            )

        # Live Anthropic API Call
        client = self._get_anthropic_client()

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        api_res = client.messages.create(**kwargs)

        # Parse Anthropic completion
        content_text = ""
        tool_calls: list[ToolCallItem] = []

        for block in api_res.content:
            if getattr(block, "type", None) == "text":
                content_text += getattr(block, "text", "")
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append(
                    ToolCallItem(
                        id=getattr(block, "id", f"call-{len(tool_calls)}"),
                        name=getattr(block, "name", ""),
                        input=getattr(block, "input", {}),
                    )
                )

        input_toks = getattr(api_res.usage, "input_tokens", 0)
        output_toks = getattr(api_res.usage, "output_tokens", 0)
        cost = calculate_cost(input_toks, output_toks)

        response = LLMResponse(
            content=content_text,
            tool_calls=tool_calls,
            input_tokens=input_toks,
            output_tokens=output_toks,
            cost_usd=cost,
            from_cache=False,
            stop_reason=getattr(api_res, "stop_reason", None),
        )

        # Record to cache
        self.cache.put(cache_key, response)
        return response

    def call_structured(
        self,
        schema: Type[T],
        system: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
    ) -> tuple[T, LLMResponse]:
        """
        Forces structured Pydantic output via tool use constraint.
        Retries once with validation feedback on schema parsing error.
        """
        tool_name = schema.__name__
        tool_def = {
            "name": tool_name,
            "description": f"Outputs structured {tool_name} schema.",
            "input_schema": schema.model_json_schema(),
        }
        tool_choice = {"type": "tool", "name": tool_name}

        # First attempt
        resp = self.complete(
            system=system,
            messages=messages,
            tools=[tool_def],
            tool_choice=tool_choice,
            temperature=temperature,
        )

        for tc in resp.tool_calls:
            if tc.name == tool_name:
                try:
                    parsed = schema.model_validate(tc.input)
                    return parsed, resp
                except Exception as e:
                    logger.warning(f"Schema validation error on first attempt: {e}. Retrying once...")
                    # Retry once with error feedback
                    retry_msgs = list(messages)
                    retry_msgs.append(
                        {
                            "role": "assistant",
                            "content": [{"type": "tool_use", "id": tc.id, "name": tool_name, "input": tc.input}],
                        }
                    )
                    retry_msgs.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tc.id,
                                    "content": f"Schema validation error: {e}. Please fix the fields.",
                                }
                            ],
                        }
                    )

                    retry_resp = self.complete(
                        system=system,
                        messages=retry_msgs,
                        tools=[tool_def],
                        tool_choice=tool_choice,
                        temperature=temperature,
                    )
                    for r_tc in retry_resp.tool_calls:
                        if r_tc.name == tool_name:
                            parsed_retry = schema.model_validate(r_tc.input)
                            return parsed_retry, retry_resp

        # If model returned text instead of tool call or in mock mode
        if resp.content:
            try:
                data = json.loads(resp.content)
                return schema.model_validate(data), resp
            except Exception:
                pass

        raise ValueError(f"Failed to extract structured {tool_name} from model response: {resp}")


# Global default client
llm_client = LLMClient()
