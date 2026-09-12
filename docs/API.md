# STARK — API Reference

> STARK exposes a simple FastAPI server for interacting with the cognitive engine.

---

## 🚀 Base URL

```
http://localhost:8000
```

---

## 📡 Endpoints

### POST `/chat`
Send a message to STARK and get a cognitive response.

**Request:**
```json
{
  "message": "Explain how transformers work",
  "mode": "auto",
  "session_id": "user_123",
  "stream": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | ✅ | The user query |
| `mode` | string | ❌ | `auto`, `fast`, `reasoning`, `deep`, `autonomous` |
| `session_id` | string | ❌ | For conversation continuity |
| `stream` | boolean | ❌ | Stream response via SSE (default: false) |

**Response:**
```json
{
  "answer": "Transformers are a neural network architecture...",
  "mode_used": "reasoning",
  "agents_used": ["ReasoningAgent", "JudgeAgent"],
  "judge_score": 8.5,
  "verified": true,
  "revision_count": 0,
  "total_latency_ms": 4230,
  "session_id": "user_123"
}
```

---

### GET `/health`
Check if STARK and Ollama are running.

**Response:**
```json
{
  "status": "ok",
  "stark_version": "0.1.0",
  "muktiverse_version": "0.1.0",
  "ollama_connected": true,
  "model": "qwen3.5:4b",
  "uptime_seconds": 3600
}
```

---

### GET `/status`
Get current system status and active sessions.

**Response:**
```json
{
  "active_sessions": 2,
  "requests_processed": 145,
  "avg_latency_ms": 3200,
  "mode_distribution": {
    "fast": 80,
    "reasoning": 45,
    "deep": 18,
    "autonomous": 2
  }
}
```

---

### POST `/chat/stream`
Stream STARK's response as Server-Sent Events.

**Request:** Same as `/chat`

**Response:** SSE stream
```
data: {"chunk": "Transform", "done": false}
data: {"chunk": "ers are", "done": false}
data: {"chunk": " a neural...", "done": false}
data: {"answer": "...", "mode_used": "reasoning", "done": true}
```

---

## 🧪 Usage Examples

### curl
```bash
# Simple query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is STARK?"}'

# Force deep mode
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Research LLM scaling laws", "mode": "deep"}'

# Health check
curl http://localhost:8000/health
```

### Python
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/chat",
        json={
            "message": "Write a Python function to sort a list",
            "mode": "auto",
            "session_id": "dev_session"
        }
    )
    result = response.json()
    print(result["answer"])
    print(f"Mode: {result['mode_used']}, Score: {result['judge_score']}")
```

---

## 🚀 Starting the Server

```bash
# From the Stark project root
python main.py

# Or with uvicorn directly
uvicorn stark.api.server:app --host 0.0.0.0 --port 8000 --reload
```

---

## ⚙️ API Config

```yaml
# config/local.yaml
api:
  host: 0.0.0.0
  port: 8000
  reload: true
  cors_origins: ["*"]
  max_request_size_mb: 10
  request_timeout_seconds: 300
```

---

*Last Updated: 2026-09-12 | STARK v0.1.0 | MuktiVerse 0.1.0*
