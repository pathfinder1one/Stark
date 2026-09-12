# STARK — Architecture Deep Dive

> Detailed technical architecture of STARK, its layers, data flow, and integration points with MuktiVerse and Ollama.

---

## 🏗️ Three-Layer Architecture

```
╔══════════════════════════════════════════════════════════════╗
║                        STARK LAYER                          ║
║                                                              ║
║   ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐  ║
║   │ STARKEngine │   │ ModeRouter  │   │  CognitiveLoop  │  ║
║   │  (engine.py)│   │(mode_router)│   │   (loop.py)     │  ║
║   └─────────────┘   └─────────────┘   └─────────────────┘  ║
║   ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐  ║
║   │   Modes     │   │  Policies   │   │   API Server    │  ║
║   │ fast/deep/  │   │ tool_policy │   │  (FastAPI)      │  ║
║   │ reasoning/  │   │             │   │                 │  ║
║   │ autonomous  │   │             │   │                 │  ║
║   └─────────────┘   └─────────────┘   └─────────────────┘  ║
╠══════════════════════════════════════════════════════════════╣
║                     MUKTIVERSE LAYER                        ║
║                                                             ║
║  agents/          orchestrator/        llm/                 ║
║  ├── base         ├── core             ├── ollama           ║
║  ├── reasoning    ├── planner          ├── smart_router      ║
║  ├── research     ├── executor         ├── selector         ║
║  ├── coding       ├── graph            └── catalog          ║
║  ├── math         ├── intent                                ║
║  ├── judge        ├── synthesizer      memory/              ║
║  ├── verification └── autonomous       ├── short_term       ║
║  ├── reflection                        ├── long_term        ║
║  └── planning     rag/                 └── manager          ║
║                   ├── pipeline                              ║
║  tools/           ├── retriever        core/                ║
║  ├── registry     ├── hybrid_ranker    ├── prompt_guard      ║
║  ├── code_executor├── bm25             ├── rate_limiter      ║
║  ├── web_search   ├── vector_store     └── security         ║
║  ├── sql_tools    └── chunker                               ║
║  └── file_processor                                         ║
╠══════════════════════════════════════════════════════════════╣
║                      OLLAMA LAYER                           ║
║                                                             ║
║           qwen3.5:4b @ http://localhost:11434               ║
║           Thinking Mode: /think | /no_think                 ║
║           Context: 128K tokens                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 🔄 Request Lifecycle (Deep Mode Example)

```
1. HTTP POST /chat  {"message": "Research quantum computing"}
         │
         ▼
2. STARKEngine.run()
         │
         ▼
3. core.prompt_guard  ← Injection check
         │
         ▼
4. ModeRouter.route()
         │
         ▼
5. IntentClassifier → "research" → DEEP MODE selected
         │
         ▼
6. PlanningAgent → DAG:
         [task_1: web_search QC basics]
         [task_2: web_search QC advances]  (parallel)
         [task_3: synthesize findings]      (after 1+2)
         │
         ▼
7. Executor runs DAG
         ├── ResearchAgent (task_1) → Ollama → result_1
         └── ResearchAgent (task_2) → Ollama → result_2
                    │
                    ▼
              ResearchAgent (task_3) → Ollama → synthesis
         │
         ▼
8. VerificationAgent → cross-checks synthesis
         │
         ▼
9. JudgeAgent → score: 8.2/10 → PASS
         │
         ▼
10. SafetyAgent → SAFE
         │
         ▼
11. Final Response → HTTP 200
```

---

## 🧠 Cognitive Loop Detail

```python
# stark/cognitive/loop.py (simplified)

async def cognitive_loop(query, mode, config):
    MAX_REVISIONS = 3

    # Step 1: Think
    candidate = await thinker.think(query, mode)

    for attempt in range(MAX_REVISIONS):
        # Step 2: Verify
        verification = await verification_agent.verify(candidate, query)

        # Step 3: Judge
        judgment = await judge_agent.score(candidate, query, verification)

        if judgment.score >= config.quality.pass_threshold:
            break  # Accept

        # Step 4: Reflect
        reflection = await reflection_agent.reflect(
            candidate, judgment.feedback
        )

        # Step 5: Revise
        candidate = await revisor.revise(query, candidate, reflection)

    # Step 6: Safety
    safety = await safety_agent.check(candidate)
    return candidate if safety.safe else safety.fallback
```

---

## 🗃️ Data Models

```python
# Core data flow types

@dataclass
class STARKRequest:
    message: str
    mode: Optional[str] = None   # auto, fast, reasoning, deep, autonomous
    session_id: Optional[str] = None
    context: Optional[dict] = None

@dataclass
class AgentRun:
    agent_name: str
    model_used: str
    tool_calls: List[ToolCall]
    evidence: List[Evidence]
    output: str
    latency_ms: int

@dataclass
class STARKResponse:
    answer: str
    mode_used: str
    agents_used: List[str]
    judge_score: Optional[float]
    verified: bool
    revision_count: int
    total_latency_ms: int
    session_id: str
```

---

## 🔌 Ollama Adapter

```python
# stark/adapters/ollama_adapter.py

from muktiverse import configure

def configure_stark_ollama(model: str = "qwen3.5:4b"):
    configure(
        default_provider="ollama",
        ollama_base_url="http://localhost:11434",
        ollama_model=model,
        ollama_timeout=120,
    )
```

---

## 🔐 Security Flow

```
Every query passes through:

prompt_guard (injection detection)
        ↓
tool_policy (permission validation per agent)
        ↓
rate_limiter (prevents abuse)
        ↓
[agent execution]
        ↓
safety_agent (output safety check)
        ↓
PII scrubbing before persistence
```

---

## 🗄️ Persistence (Future Phases)

| Data | Store | MuktiVerse Module |
|---|---|---|
| Conversation state | PostgreSQL | `muktiverse.database` |
| Short-term context | Redis | `muktiverse.cache` |
| Vector embeddings | ChromaDB/Weaviate | `muktiverse.rag.vector_store` |
| Knowledge graph | Neo4j | `muktiverse.knowledge` |
| Execution traces | PostgreSQL | `muktiverse.observability` |

---

*Last Updated: 2026-09-12 | MuktiVerse 0.1.0*
