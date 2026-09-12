# STARK — Execution Modes

> STARK automatically selects the best execution mode based on task complexity. You can also force a mode explicitly.

---

## 🎯 Overview

| Mode | Speed | Agents | Best For |
|---|---|---|---|
| **Fast** | < 2s | None (direct LLM) | Greetings, quick facts, simple Q&A |
| **Reasoning** | < 10s | ReasoningAgent | Math, logic, analysis, comparisons |
| **Deep** | < 60s | Multi-agent DAG | Research, coding, multi-step problems |
| **Autonomous** | Unlimited | Full swarm + self-revision | Complex goals, open-ended tasks |

---

## ⚡ Fast Mode

**When triggered:** Simple queries, conversational messages, quick factual lookups

**Pipeline:**
```
Query → Ollama (qwen3.5:4b) → Response
```

**No agents. No orchestration. No overhead.**

**Config:**
```yaml
execution:
  default_mode: fast
```

**Force it:**
```python
result = await stark.run("What is 2+2?", mode="fast")
```

---

## 🤔 Reasoning Mode

**When triggered:** Questions requiring step-by-step logic, mathematical analysis, comparisons

**Pipeline:**
```
Query
  │
  ▼
ReasoningAgent (Chain-of-Thought)
  │
  ▼
JudgeAgent (quality check)
  │
  ▼
Response
```

**Uses qwen3.5:4b's built-in thinking mode (`/think` token)**

**Force it:**
```python
result = await stark.run("Explain how quicksort works", mode="reasoning")
```

---

## 🔬 Deep Mode

**When triggered:** Research tasks, code generation, multi-step problems, anything requiring multiple specialists

**Pipeline:**
```
Query
  │
  ▼
IntentClassifier → task type detected
  │
  ▼
PlanningAgent → Task DAG created
  │
  ▼
Executor → runs DAG (parallel where possible):
  ├── ResearchAgent
  ├── CodingAgent
  └── MathAgent
  │
  ▼
VerificationAgent → evidence check
  │
  ▼
JudgeAgent → score ≥ 7?
  ├── YES → SafetyAgent → Response
  └── NO  → ReflectionAgent → Revisor → Re-verify
```

**Force it:**
```python
result = await stark.run("Build a Python web scraper", mode="deep")
```

---

## 🤖 Autonomous Mode

**When triggered:** Open-ended goals, tasks requiring self-direction, long-running objectives

**Pipeline:**
```
Goal
  │
  ▼
AutonomousOrchestrator (MuktiVerse)
  │
  ├── Spawns agents as needed
  ├── Uses tools dynamically
  ├── Self-monitors progress
  ├── Re-plans if blocked
  └── Runs until goal achieved (or max_iterations)
  │
  ▼
Full cognitive loop on final answer
  │
  ▼
Response
```

**Config:**
```yaml
execution:
  autonomous_mode: enabled
  autonomous_max_iterations: 10
```

**Force it:**
```python
result = await stark.run(
    "Research the latest advances in quantum computing and write a summary report",
    mode="autonomous"
)
```

---

## 🧭 Auto Mode Selection (Mode Router)

The Mode Router uses `muktiverse.orchestrator.intent.IntentClassifier` to detect task complexity:

```python
# stark/routing/mode_router.py

FAST_PATTERNS = [
    "hi", "hello", "what is", "who is", "when did",
    "define", "explain briefly", "translate"
]

REASONING_PATTERNS = [
    "analyze", "compare", "why", "how does", "calculate",
    "prove", "step by step", "evaluate"
]

DEEP_PATTERNS = [
    "research", "build", "create", "write code", "implement",
    "investigate", "find all", "summarize the document"
]

AUTONOMOUS_PATTERNS = [
    "achieve", "solve", "complete the task", "work on",
    "figure out how to", "do whatever it takes"
]
```

---

## 🎛️ Forcing a Mode via API

```bash
# Fast
curl -X POST http://localhost:8000/chat \
  -d '{"message": "Hello!", "mode": "fast"}'

# Deep
curl -X POST http://localhost:8000/chat \
  -d '{"message": "Research Rust vs Go", "mode": "deep"}'
```

---

*Last Updated: 2026-09-12 | MuktiVerse 0.1.0*
