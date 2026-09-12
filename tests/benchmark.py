"""
STARK — A/B Evaluation Benchmark Suite
Compares raw local LLM baseline vs STARK cognitive pipeline on identical tasks.
"""
from __future__ import annotations

import asyncio
import time
import sys
import io

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stark.engine import STARKEngine

GOLDEN_TASKS = [
    {
        "id": "T1_MATH",
        "category": "Math / Finance",
        "prompt": "A store offers a 20% discount on a $150 jacket, then adds 8% sales tax to the discounted price. What is the final total?",
        "expected_answer": "$129.60",
    },
    {
        "id": "T2_LOGIC",
        "category": "Systems / Analysis",
        "prompt": "Explain the fundamental difference between a process and a thread in an operating system in 2 clear bullet points.",
        "expected_answer": "Memory space isolation vs shared memory within a process",
    },
    {
        "id": "T3_CODE",
        "category": "Coding / Algorithm",
        "prompt": "Write a Python function `is_palindrome(s: str) -> bool` that ignores case, spaces, and punctuation.",
        "expected_answer": "clean string comparison with [::-1]",
    },
]


async def run_baseline(prompt: str, model: str = "qwen3.5:4b") -> dict:
    """Single local LLM direct completion without cognitive loop."""
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        data = resp.json()
        latency = (time.perf_counter() - start) * 1000
        msg = data.get("message", {})
        content = msg.get("content") or msg.get("thinking", "")
        tokens = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)

        return {
            "answer": content.strip(),
            "latency_ms": round(latency, 1),
            "tokens": tokens,
        }


async def run_stark(engine: STARKEngine, prompt: str) -> dict:
    """STARK cognitive pipeline execution."""
    resp = await engine.run(prompt, mode="auto")
    return {
        "answer": resp.answer.strip(),
        "mode": resp.mode_used,
        "agents": resp.agents_used,
        "judge_score": resp.judge_score,
        "verified": resp.verified,
        "latency_ms": resp.total_latency_ms,
        "tokens": resp.total_tokens,
    }


async def main():
    print("=" * 70)
    print("  STARK vs Raw Ollama Baseline — Evaluation Benchmark")
    print("  Model: qwen3.5:4b | Tasks: 3 Golden Tasks")
    print("=" * 70)

    engine = STARKEngine(model="qwen3.5:4b", enable_judge=True)
    await engine.startup()

    results = []

    for task in GOLDEN_TASKS:
        print(f"\nEvaluating [{task['id']}] {task['category']}...")
        print(f"Prompt: {task['prompt'][:70]}...")

        # Run Baseline
        print("  Running Baseline (raw Ollama)...", end="", flush=True)
        base = await run_baseline(task["prompt"])
        print(f" Done ({base['latency_ms']:.0f}ms)")

        # Run STARK
        print("  Running STARK Cognitive Loop...", end="", flush=True)
        stark = await run_stark(engine, task["prompt"])
        print(f" Done ({stark['latency_ms']:.0f}ms, Mode: {stark['mode']}, Score: {stark['judge_score']})")

        results.append({
            "task": task,
            "baseline": base,
            "stark": stark,
        })

    # Print Summary Table
    print("\n" + "=" * 70)
    print("  BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Task ID':<10} | {'Mode':<10} | {'Agents':<20} | {'Score':<8} | {'STARK Latency':<14} | {'Base Latency'}")
    print("-" * 70)
    for r in results:
        t = r["task"]
        b = r["baseline"]
        s = r["stark"]
        agents_str = ",".join(s["agents"])[:18]
        score_str = f"{s['judge_score']:.0f}/100" if s["judge_score"] else "N/A"
        print(f"{t['id']:<10} | {s['mode']:<10} | {agents_str:<20} | {score_str:<8} | {s['latency_ms']:.0f}ms{'':<8} | {b['latency_ms']:.0f}ms")

    print("\n" + "=" * 70)
    print("  DETAILED OUTPUT COMPARISON")
    print("=" * 70)
    for r in results:
        t = r["task"]
        b = r["baseline"]
        s = r["stark"]
        print(f"\n--- [{t['id']}] {t['category']} ---")
        print(f"PROMPT: {t['prompt']}")
        print(f"EXPECTED: {t['expected_answer']}")
        print(f"\n[BASELINE ANSWER]:\n{b['answer'][:300]}...")
        print(f"\n[STARK ANSWER (Mode: {s['mode']}, Score: {s['judge_score']})]:\n{s['answer'][:300]}...")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
