# STARK — Local Cognitive AI
> *Don't make AI answer better. Make AI THINK better.*

Built on **MuktiVerse 0.1.0** + **Ollama (qwen3.5:4b)**

---

## 🚀 Quick Start

```bash
# 1. Make sure Ollama is running
ollama serve

# 2. Confirm model is available
ollama list   # should show qwen3.5:4b

# 3. Install dependencies
pip install muktiverse-0.1.0-py3-none-any.whl

# 4. Run STARK
python main.py
```

---

## 🧠 What is STARK?

STARK is a **cognitive AI system** that makes a local LLM smarter by wrapping it in:

- **Multi-agent orchestration** — specialized agents for research, coding, math, reasoning
- **Automatic mode selection** — decides how deeply to think based on task complexity
- **Judge + Verify + Reflect loop** — quality system that can reject and revise weak answers
- **Local-first privacy** — everything runs on your machine via Ollama

---

## 📁 Project Structure

```
stark/
├── stark/           ← STARK cognitive layer
│   ├── engine.py
│   ├── cognitive/   ← think → verify → judge → reflect → revise
│   ├── modes/       ← fast / reasoning / deep / autonomous
│   ├── adapters/    ← Ollama adapter
│   ├── routing/     ← mode selection
│   ├── policies/    ← tool permissions
│   └── api/         ← FastAPI server
├── config/          ← YAML configs
├── docs/            ← All documentation
├── tests/           ← Test suite
└── main.py          ← Entry point
```

---

## ⚡ Execution Modes

| Mode | Speed | When |
|---|---|---|
| Fast | < 2s | Simple Q&A, greetings |
| Reasoning | < 10s | Logic, math, analysis |
| Deep | < 60s | Research, code, multi-step |
| Autonomous | Unlimited | Complex goals |

---

## 📚 Documentation

- [Implementation Plan](docs/STARK_IMPLEMENTATION_PLAN.md)
- [Progress Tracker](docs/PROGRESS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Agents Reference](docs/AGENTS.md)
- [Execution Modes](docs/MODES.md)
- [Tools Reference](docs/TOOLS.md)
- [Memory & RAG](docs/MEMORY.md)
- [API Reference](docs/API.md)

---

## 🔧 Tech Stack

- **LLM:** qwen3.5:4b via Ollama
- **Framework:** MuktiVerse 0.1.0
- **Language:** Python 3.13
- **API:** FastAPI
- **Memory:** In-memory (V1) → Redis + PostgreSQL (later)
- **RAG:** ChromaDB + BM25 (later)

---

*STARK v0.1.0 | 2026-09-12*
