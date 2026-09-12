# STARK — Memory & RAG Reference

> How STARK remembers conversations and retrieves relevant knowledge using MuktiVerse's memory and RAG modules.

---

## 🧠 Memory System

STARK uses a two-tier memory system via `muktiverse.memory`:

```
┌─────────────────────────────────────────┐
│              Memory Manager             │
│                                         │
│  ┌──────────────┐  ┌────────────────┐  │
│  │  Short-Term  │  │   Long-Term    │  │
│  │  (session)   │  │  (persistent)  │  │
│  │  In-memory   │  │  Vector store  │  │
│  │  Redis cache │  │  + PostgreSQL  │  │
│  └──────────────┘  └────────────────┘  │
└─────────────────────────────────────────┘
```

---

## 📋 Short-Term Memory

- **Scope:** Current conversation session
- **Storage:** In-memory / Redis
- **TTL:** Session lifetime (default: 2 hours)
- **Content:** Recent messages, agent outputs, tool results

```python
from muktiverse.memory.short_term import ShortTermMemory

stm = ShortTermMemory(session_id="user_123")
await stm.add("user", "What is quantum computing?")
await stm.add("assistant", "Quantum computing is...")

context = await stm.get_recent(n=10)  # Last 10 turns
```

---

## 🗄️ Long-Term Memory

- **Scope:** Across sessions, persistent
- **Storage:** Vector store (embeddings) + PostgreSQL (metadata)
- **Content:** Important facts, user preferences, learned patterns

```python
from muktiverse.memory.long_term import LongTermMemory

ltm = LongTermMemory()
await ltm.store("User prefers concise answers", user_id="user_123")

# Semantic search
relevant = await ltm.recall("user communication preferences", user_id="user_123")
```

---

## 📚 RAG Pipeline

The **Retrieval-Augmented Generation** pipeline injects relevant knowledge into agent prompts.

```
Agent needs context
        │
        ▼
RAGPipeline.retrieve(query)
        │
        ├── Vector search (semantic similarity)
        ├── BM25 search (keyword match)
        └── Hybrid Ranker (RRF fusion)
                │
                ▼
        Top-K documents ranked by relevance
                │
                ▼
        Injected into agent system prompt
```

---

## ⚙️ RAG Components

### Vector Store
```python
from muktiverse.rag.vector_store import VectorStore

vs = VectorStore()
await vs.index(documents)           # Add documents
results = await vs.search(query, k=5)  # Semantic search
```

### BM25 (Keyword Search)
```python
from muktiverse.rag.bm25 import BM25Retriever

bm25 = BM25Retriever()
results = bm25.search(query, k=5)   # Keyword-based
```

### Hybrid Ranker
```python
from muktiverse.rag.hybrid_ranker import HybridRanker

ranker = HybridRanker()
# Fuses vector + BM25 results using Reciprocal Rank Fusion
fused = ranker.rank(vector_results, bm25_results)
```

---

## 🔄 How Memory Flows into Agents

```python
# In cognitive/loop.py (simplified)

async def build_agent_context(query, session_id):
    # 1. Recent conversation history
    history = await short_term_memory.get_recent(n=10)

    # 2. Relevant long-term memories
    long_term = await long_term_memory.recall(query)

    # 3. Relevant documents via RAG
    rag_docs = await rag_pipeline.retrieve(query, k=5)

    return {
        "history": history,
        "memories": long_term,
        "knowledge": rag_docs
    }
```

---

## 📊 Memory Config

```yaml
# config/local.yaml
memory:
  short_term:
    backend: inmemory   # or redis
    ttl_minutes: 120
    max_turns: 50

  long_term:
    enabled: false      # Enable with vector store
    backend: chromadb
    collection: stark_memory

rag:
  enabled: false        # Enable with document corpus
  chunk_size: 512
  chunk_overlap: 64
  top_k: 5
  hybrid_alpha: 0.7     # 0=BM25 only, 1=vector only
```

---

## 🚀 V1 Setup (Minimal)

For V1, we start with **in-memory only** (no persistence needed):

```python
from muktiverse.memory.manager import MemoryManager

# Simple in-memory setup
memory = MemoryManager(
    short_term_backend="inmemory",
    long_term_enabled=False,
    rag_enabled=False
)
```

Persistence (Redis, PostgreSQL, ChromaDB, Neo4j) comes in later phases.

---

*Last Updated: 2026-09-12 | MuktiVerse 0.1.0*
