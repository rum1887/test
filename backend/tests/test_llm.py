"""
Tests for LLM Client, Record/Replay Cache, MockLLM, Cost Tracking, and Structured Output Validation.
"""

from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from backend.app.agent.llm import (
    LLMClient,
    LLMResponse,
    RecordReplayCache,
    ToolCallItem,
    calculate_cost,
)


class DummyVerdict(BaseModel):
    verdict: str = Field(description="Verdict (benign or malicious)")
    confidence: float = Field(description="Confidence score")
    summary: str = Field(description="Brief summary")


def test_cost_calculation():
    """Verify Sonnet token pricing calculation."""
    cost = calculate_cost(input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == 18.0  # $3 + $15

    cost_small = calculate_cost(input_tokens=1000, output_tokens=500)
    expected = (1000 / 1e6 * 3.0) + (500 / 1e6 * 15.0)
    assert abs(cost_small - round(expected, 6)) < 1e-6


def test_cache_key_computation_and_persistence(tmp_path: Path):
    """Verify deterministic cache key computation and JSONL persistence."""
    cache = RecordReplayCache(cache_dir=tmp_path)

    key1 = cache.compute_key(
        model="claude-3-5-sonnet",
        system="System prompt 1",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.0,
    )
    key2 = cache.compute_key(
        model="claude-3-5-sonnet",
        system="System prompt 1",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.0,
    )
    assert key1 == key2

    # Put response
    resp = LLMResponse(
        content="Cached reply",
        input_tokens=100,
        output_tokens=20,
        cost_usd=0.0006,
    )
    cache.put(key1, resp)

    # Reload cache from disk
    cache2 = RecordReplayCache(cache_dir=tmp_path)
    loaded = cache2.get(key1)
    assert loaded is not None
    assert loaded.content == "Cached reply"
    assert loaded.from_cache is True


def test_mock_llm_queue_and_structured_output():
    """Verify MockLLM queues responses and call_structured validates Pydantic model."""
    client = LLMClient(mode="mock")

    # Queue structured tool call for DummyVerdict
    client.mock.queue_response(
        LLMResponse(
            content="",
            tool_calls=[
                ToolCallItem(
                    id="call-verdict-1",
                    name="DummyVerdict",
                    input={"verdict": "benign", "confidence": 0.95, "summary": "Authorized debugging"},
                )
            ],
            input_tokens=200,
            output_tokens=50,
            cost_usd=0.00135,
        )
    )

    verdict, resp = client.call_structured(
        schema=DummyVerdict,
        system="You are a security verifier.",
        messages=[{"role": "user", "content": "Analyze evidence."}],
    )

    assert isinstance(verdict, DummyVerdict)
    assert verdict.verdict == "benign"
    assert verdict.confidence == 0.95
    assert verdict.summary == "Authorized debugging"


def test_replay_mode_serves_cached_investigation(tmp_path: Path):
    """Verify that replay mode serves from cache and raises KeyError on cache miss."""
    # 1. Pre-record a dummy investigation step into cache
    cache = RecordReplayCache(cache_dir=tmp_path)
    key = cache.compute_key(
        model="claude-3-5-sonnet-20241022",
        system="Investigate alert",
        messages=[{"role": "user", "content": "Alert: shell in checkout pod"}],
        temperature=0.0,
    )
    cached_resp = LLMResponse(
        content="Investigating process tree...",
        tool_calls=[
            ToolCallItem(
                id="call-proc-tree",
                name="process_tree",
                input={"pod_id": "pod-checkout-1", "pid": 1002},
            )
        ],
        input_tokens=300,
        output_tokens=60,
        cost_usd=0.0018,
    )
    cache.put(key, cached_resp)

    # 2. Run client in replay mode
    replay_client = LLMClient(
        model="claude-3-5-sonnet-20241022",
        mode="replay",
        cache_dir=tmp_path,
    )

    # Should succeed from cache
    res = replay_client.complete(
        system="Investigate alert",
        messages=[{"role": "user", "content": "Alert: shell in checkout pod"}],
        temperature=0.0,
    )
    assert res.from_cache is True
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "process_tree"

    # Cache miss should fail loudly in replay mode
    with pytest.raises(KeyError) as exc_info:
        replay_client.complete(
            system="Investigate alert",
            messages=[{"role": "user", "content": "Unseen prompt that has no cache"}],
            temperature=0.0,
        )
    assert "Replay cache miss" in str(exc_info.value)
