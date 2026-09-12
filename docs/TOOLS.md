# STARK — Tools Reference

> All tools available in STARK via MuktiVerse, their permissions, and how agents use them.

---

## 🛠️ Available Tools

| Tool | File | Agents That Use It | Permission Level |
|---|---|---|---|
| `code_executor` | `tools/code_executor.py` | CodingAgent, MathAgent | Restricted (sandbox) |
| `web_search` | `tools/web_search.py` | ResearchAgent | Requires user policy |
| `file_processor` | `tools/file_processor.py` | CodingAgent, DocumentAgent | Local only |
| `sql_tools` | `tools/sql_tools.py` | DataAgent | Schema-approved only |
| `document_tools` | `tools/document_tools.py` | ResearchAgent, SummarizationAgent | Local only |
| `api_caller` | `tools/api_caller.py` | APIAgent | Explicit approval |
| `github_tools` | `tools/github_tools.py` | CodingAgent | Restricted |
| `web_scraper` | `tools/web_scraper.py` | ResearchAgent | Requires user policy |

---

## 🔐 Permission Levels

| Level | Meaning |
|---|---|
| `open` | Any agent can use freely |
| `restricted` | Sandboxed, resource-limited |
| `requires_approval` | User must explicitly allow |
| `disabled` | Blocked in current policy |

---

## 🔧 Tool Execution Flow

```
Agent identifies capability gap
        │
        ▼
ToolRegistry.lookup(tool_name)
        │
        ▼
tool_policy.validate(agent, tool, args)  ← Permission check
        │
        ▼
safe_execute(tool, args)                 ← Sandboxed execution
        │
        ▼
Tool result returned to agent
        │
        ▼
VerificationAgent observes result (if critical)
```

---

## 📋 Tool Details

### 🖥️ code_executor
```python
# Runs Python code in a sandbox
# Resource limits: CPU time, memory cap
# No network access by default

result = await tool_registry.execute("code_executor", {
    "code": "print(sum(range(100)))",
    "timeout": 10,
    "allow_network": False
})
```

---

### 🔍 web_search
```python
# Searches the web for information
# Requires: user policy to enable

result = await tool_registry.execute("web_search", {
    "query": "quantum computing 2025 advances",
    "max_results": 5
})
```

---

### 📁 file_processor
```python
# Reads/writes local files
# Restricted to project directory by default

result = await tool_registry.execute("file_processor", {
    "action": "read",
    "path": "./data/report.pdf"
})
```

---

### 🗄️ sql_tools
```python
# Executes SQL queries against approved schemas
# Read-only by default

result = await tool_registry.execute("sql_tools", {
    "query": "SELECT * FROM products LIMIT 10",
    "schema": "ecommerce"
})
```

---

## ⚙️ Tool Policy Config

```yaml
# config/policies.yaml
tools:
  code_executor:
    enabled: true
    permission: restricted
    max_cpu_seconds: 10
    max_memory_mb: 256
    allow_network: false

  web_search:
    enabled: true
    permission: requires_approval
    max_results: 10

  file_processor:
    enabled: true
    permission: restricted
    allowed_paths: ["./data", "./output"]
    allow_write: false

  sql_tools:
    enabled: false   # Enable when DB is configured
    permission: requires_approval

  api_caller:
    enabled: false   # Enable explicitly
    permission: requires_approval

  github_tools:
    enabled: false
    permission: requires_approval
```

---

## 🧪 Adding a Custom Tool

```python
# 1. Create tool class
from muktiverse.tools.base import BaseTool

class MyCustomTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"

    async def execute(self, args: dict) -> dict:
        # Your tool logic here
        return {"result": "done"}

# 2. Register it
from muktiverse.tools.registry import ToolRegistry
registry = ToolRegistry()
registry.register(MyCustomTool())

# 3. Add policy in policies.yaml
# tools:
#   my_tool:
#     enabled: true
#     permission: restricted
```

---

*Last Updated: 2026-09-12 | MuktiVerse 0.1.0*
