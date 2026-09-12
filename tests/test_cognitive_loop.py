"""
STARK — Phase 3 Cognitive Loop Tests
Tests the Think -> Judge -> Revise cycle end-to-end.
"""
import asyncio
import sys
import io

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from stark import STARKEngine


async def test_fast_mode():
    """Fast mode: direct LLM, no judge."""
    print("\n=== TEST 1: Fast Mode (no judge) ===")
    engine = STARKEngine(enable_judge=False)
    await engine.startup()
    response = await engine.run("Hello! How are you?", mode="fast")
    print(f"Answer:     {response.answer[:100]}...")
    print(f"Mode:       {response.mode_used}")
    print(f"Agents:     {response.agents_used}")
    print(f"Score:      {response.judge_score}")
    print(f"Latency:    {response.total_latency_ms}ms")
    assert response.answer, "No answer returned"
    assert "direct_llm" in response.agents_used
    assert response.judge_score is None, "Judge should not run in fast mode"
    print("PASS")
    return engine


async def test_reasoning_with_judge(engine: STARKEngine):
    """Reasoning mode: should run judge, potentially revise."""
    print("\n=== TEST 2: Reasoning + Judge ===")
    response = await engine.run("What is 15 percent of 840?", mode="reasoning")
    print(f"Answer:     {response.answer[:200]}...")
    print(f"Mode:       {response.mode_used}")
    print(f"Agents:     {response.agents_used}")
    print(f"Score:      {response.judge_score}")
    print(f"Verified:   {response.verified}")
    print(f"Revisions:  {response.revision_count}")
    print(f"Latency:    {response.total_latency_ms}ms")
    assert response.answer, "No answer returned"
    assert "reasoning" in response.agents_used or "reflection" in response.agents_used
    print("PASS")


async def test_cognitive_loop_direct():
    """Direct CognitiveLoop test."""
    print("\n=== TEST 3: CognitiveLoop Direct ===")
    from stark.cognitive.loop import CognitiveLoop
    from stark.adapters.ollama_adapter import configure_ollama
    configure_ollama()

    loop = CognitiveLoop(model="qwen3.5:4b", max_revisions=1, enable_judge=True)
    result = await loop.run(
        message="Explain what a neural network is in 2 sentences.",
        mode="reasoning",
    )
    print(f"Answer:     {result.answer[:200]}")
    print(f"Agents:     {result.agents_used}")
    print(f"Score:      {result.judge_score}")
    print(f"Verdict:    {result.judge_verdict}")
    print(f"Revisions:  {result.revision_count}")
    print(f"Latency:    {result.total_latency_ms}ms")
    assert result.answer, "No answer"
    print("PASS")


async def main():
    print("=" * 60)
    print("STARK Phase 3 — Cognitive Loop Tests")
    print("=" * 60)

    engine = await test_fast_mode()

    # Re-enable judge for remaining tests
    engine._enable_judge = True
    engine._cognitive_loop._enable_judge = True

    await test_reasoning_with_judge(engine)
    await test_cognitive_loop_direct()

    print("\n" + "=" * 60)
    print("All Phase 3 tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
