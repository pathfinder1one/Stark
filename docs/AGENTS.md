# STARK — Agents Reference

> All agents available in STARK via MuktiVerse, their roles, when to use them, and how they wire into the cognitive loop.

---

## 🧠 Agent Overview

STARK uses **specialized agents** from MuktiVerse. Each agent has a focused role. The **Mode Router** decides which agents are activated based on task complexity.

```
User Query
    │
    ▼
Mode Router
    │
    ├── FAST ──────────► No agent (direct LLM)
    ├── REASONING ──────► ReasoningAgent
    ├── DEEP ───────────► [PlanningAgent → ResearchAgent/CodingAgent/MathAgent → VerificationAgent → JudgeAgent → ReflectionAgent]
    └── AUTONOMOUS ─────► Full agent swarm + self-revision loop
```

---

## 📋 Agent Catalog

### 🔍 ResearchAgent
- **File:** `muktiverse/agents/research.py`
- **Role:** Gathers information, searches knowledge base, synthesizes findings
- **Used in:** Deep mode, Autonomous mode
- **Triggers RAG:** Yes
- **Tool access:** web_search, document_tools
- **Output:** Structured research summary with sources

---

### 🤔 ReasoningAgent
- **File:** `muktiverse/agents/reasoning.py`
- **Role:** Step-by-step logical reasoning, chain-of-thought
- **Used in:** Reasoning mode, Deep mode
- **Triggers RAG:** Optional
- **Tool access:** None by default
- **Output:** Reasoned answer with explicit steps

---

### 💻 CodingAgent
- **File:** `muktiverse/agents/coding.py`
- **Role:** Writes, explains, debugs, and executes code
- **Used in:** Deep mode (coding tasks), Autonomous mode
- **Triggers RAG:** Optional
- **Tool access:** code_executor, file_processor, github_tools
- **Output:** Code + explanation + execution result

---

### 🔢 MathAgent
- **File:** `muktiverse/agents/math.py`
- **Role:** Mathematical computation, proofs, numerical analysis
- **Used in:** Deep mode (math tasks)
- **Triggers RAG:** No
- **Tool access:** code_executor (for computation)
- **Output:** Solution with steps + verification

---

### 📋 PlanningAgent
- **File:** `muktiverse/agents/planning.py`
- **Role:** Decomposes complex tasks into a DAG of sub-tasks
- **Used in:** Deep mode, Autonomous mode
- **Triggers RAG:** No
- **Tool access:** None
- **Output:** Task graph (DAG) for Executor

---

### ⚖️ JudgeAgent
- **File:** `muktiverse/agents/judge.py`
- **Role:** Scores agent output against a task-specific rubric
- **Used in:** All modes except Fast (configurable)
- **Triggers RAG:** No
- **Tool access:** None
- **Output:** `JudgeResult(score, passed, feedback, revision_hints)`

---

### 🔬 VerificationAgent
- **File:** `muktiverse/agents/verification.py`
- **Role:** Deterministic/evidence-based verification of answers
- **Used in:** Research, Coding, Math, Autonomous modes
- **Triggers RAG:** Yes (cross-checks against knowledge)
- **Tool access:** web_search, code_executor (for fact-checking)
- **Output:** `VerificationResult(verified, confidence, evidence)`

---

### 🪞 ReflectionAgent
- **File:** `muktiverse/agents/reflection.py`
- **Role:** Identifies WHY an answer failed and what to fix
- **Used in:** Triggered by JudgeAgent rejection
- **Triggers RAG:** No
- **Tool access:** None
- **Output:** `ReflectionResult(failure_reason, revision_strategy)`

---

### ✍️ SummarizationAgent
- **File:** `muktiverse/agents/summarization.py`
- **Role:** Condenses long content into concise summaries
- **Used in:** Research mode output compression
- **Triggers RAG:** No
- **Tool access:** document_tools
- **Output:** Structured summary

---

### 🛡️ SafetyAgent
- **File:** `muktiverse/agents/safety.py`
- **Role:** Checks output for harmful/unsafe content before delivery
- **Used in:** All modes (always-on gate)
- **Triggers RAG:** No
- **Tool access:** None
- **Output:** `SafetyResult(safe, issues)`

---

## 🔄 Cognitive Loop Agent Flow (Deep Mode)

```
Query
  │
  ▼
PlanningAgent ──► Task DAG
  │
  ▼
Executor runs DAG:
  ├── ResearchAgent (if research task)
  ├── CodingAgent   (if code task)
  ├── MathAgent     (if math task)
  └── ReasoningAgent (always)
  │
  ▼
VerificationAgent ──► Evidence check
  │
  ▼
JudgeAgent ──► Score (0-10)
  │
  ├── Score ≥ 7 ──► SafetyAgent ──► Final Response
  │
  └── Score < 7 ──► ReflectionAgent
                          │
                          ▼
                    Revisor (targeted re-run)
                          │
                          ▼
                    Back to VerificationAgent
```

---

## 📊 Agent Selection Matrix

| Task Type | Agents Activated |
|---|---|
| Greeting / Simple | None (direct LLM) |
| Explanation / Analysis | ReasoningAgent |
| Research / Facts | ResearchAgent + VerificationAgent |
| Code generation | CodingAgent + VerificationAgent |
| Math problems | MathAgent + VerificationAgent |
| Complex multi-step | PlanningAgent + relevant specialists |
| Any (quality gate) | JudgeAgent + ReflectionAgent (if failed) |
| Any (safety gate) | SafetyAgent (always) |

---

*Last Updated: 2026-09-12 | MuktiVerse 0.1.0*
