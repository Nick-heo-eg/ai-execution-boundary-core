# Integration Guide

How to integrate AI Execution Boundary Core into common AI frameworks.

**Version:** 0.1.0
**Target:** AI Agent Developers

---

## Table of Contents

- [LangChain Integration](#langchain-integration)
- [AutoGPT Integration](#autogpt-integration)
- [Custom AI Agent Integration](#custom-ai-agent-integration)
- [API Gateway Integration](#api-gateway-integration)
- [Database Access Integration](#database-access-integration)

---

## LangChain Integration

### Basic Shell Tool with Boundary

```python
from datetime import datetime, timezone
from langchain.agents import Tool
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent
import subprocess

# Initialize boundary engine
boundary = ExecutionBoundaryEngine(halt_threshold=80)

def safe_shell_tool(command: str) -> str:
    """Shell tool with execution boundary."""
    intent = ExecutionIntent(
        actor="langchain#agent",
        action="shell.exec",
        payload=command,
        timestamp=datetime.now(timezone.utc)
    )

    decision = boundary.evaluate(intent)
    proof = boundary.issue_proof(decision)

    if decision.decision == "ALLOW":
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return f"✅ Executed (risk: {decision.risk_score}/100)\n{result.stdout}"
    else:
        return f"🚫 Blocked (risk: {decision.risk_score}/100)\nReason: {decision.reason}\nProof: {proof.signature[:16]}..."

# Create LangChain tool
shell_tool = Tool(
    name="SafeShell",
    func=safe_shell_tool,
    description="Execute shell commands with safety boundary. Use for file operations, system info, etc."
)

# Use with agent
from langchain.agents import initialize_agent, AgentType
from langchain_openai import OpenAI

agent = initialize_agent(
    tools=[shell_tool],
    llm=OpenAI(temperature=0),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

# Agent will use shell tool with boundary protection
response = agent.run("List files in current directory")
```

---

### Custom LangChain BaseTool

```python
from langchain.tools import BaseTool
from pydantic import Field
from typing import Optional
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent

class BoundaryShellTool(BaseTool):
    name: str = "boundary_shell"
    description: str = "Execute shell commands with cryptographic proof"
    boundary: ExecutionBoundaryEngine = Field(default_factory=ExecutionBoundaryEngine)

    def _run(self, command: str) -> str:
        """Execute command with boundary check."""
        intent = ExecutionIntent(
            actor="langchain#boundary_tool",
            action="shell.exec",
            payload=command,
            timestamp=datetime.now(timezone.utc)
        )

        decision = self.boundary.evaluate(intent)
        proof = self.boundary.issue_proof(decision)

        if decision.decision == "ALLOW":
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout
        else:
            raise ValueError(f"Command blocked: {decision.reason}")

    async def _arun(self, command: str) -> str:
        """Async version."""
        raise NotImplementedError("Async not implemented")

# Use it
tool = BoundaryShellTool()
result = tool.run("ls -la")
```

---

## AutoGPT Integration

### Custom Command with Boundary

```python
from autogpt.command_decorator import command
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent
from datetime import datetime, timezone
import subprocess

boundary = ExecutionBoundaryEngine()

@command(
    "safe_execute_shell",
    "Execute shell command with boundary check",
    {"command": "<shell-command>"}
)
def safe_execute_shell(command: str, agent) -> str:
    """Execute shell command with boundary protection."""
    intent = ExecutionIntent(
        actor=f"autogpt#{agent.ai_name}",
        action="shell.exec",
        payload=command,
        timestamp=datetime.now(timezone.utc)
    )

    decision = boundary.evaluate(intent)
    proof = boundary.issue_proof(decision)

    if decision.decision == "ALLOW":
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return f"Executed: {result.stdout}\nProof: {proof.signature[:16]}..."
    else:
        return f"BLOCKED: {decision.reason} (Risk: {decision.risk_score}/100)"
```

---

## Custom AI Agent Integration

### Minimal Integration Pattern

```python
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent
from datetime import datetime, timezone

class SafeAIAgent:
    """AI Agent with built-in execution boundary."""

    def __init__(self, agent_id: str, halt_threshold: int = 80):
        self.agent_id = agent_id
        self.boundary = ExecutionBoundaryEngine(halt_threshold=halt_threshold)

    def execute_action(self, action_type: str, payload: str) -> dict:
        """Execute action with boundary check."""
        intent = ExecutionIntent(
            actor=f"agent#{self.agent_id}",
            action=action_type,
            payload=payload,
            timestamp=datetime.now(timezone.utc)
        )

        decision = self.boundary.evaluate(intent)
        proof = self.boundary.issue_proof(decision)

        if decision.decision == "ALLOW":
            # Actually execute the action
            result = self._execute(action_type, payload)
            return {
                "success": True,
                "result": result,
                "proof": proof,
                "risk_score": decision.risk_score
            }
        else:
            # Blocked
            return {
                "success": False,
                "reason": decision.reason,
                "proof": proof,
                "risk_score": decision.risk_score
            }

    def _execute(self, action_type: str, payload: str):
        """Actual execution logic (implement based on action type)."""
        if action_type == "shell.exec":
            import subprocess
            return subprocess.run(payload, shell=True, capture_output=True, text=True).stdout
        elif action_type == "api.call":
            # Implement API call logic
            pass
        elif action_type == "db.query":
            # Implement DB query logic
            pass
        else:
            raise ValueError(f"Unknown action type: {action_type}")

# Usage
agent = SafeAIAgent(agent_id="my_agent_001")

# Safe execution
result = agent.execute_action("shell.exec", "ls -la")
print(result["success"])  # True
print(result["proof"].signature[:16])  # Cryptographic proof

# Blocked execution
result = agent.execute_action("shell.exec", "rm -rf /")
print(result["success"])  # False
print(result["reason"])  # "Critical: root deletion"
```

---

## API Gateway Integration

### FastAPI Middleware

```python
from fastapi import FastAPI, Request, HTTPException
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent
from datetime import datetime, timezone

app = FastAPI()
boundary = ExecutionBoundaryEngine()

@app.middleware("http")
async def boundary_middleware(request: Request, call_next):
    """Check execution boundary before processing API requests."""
    # Extract request details
    method = request.method
    path = request.url.path
    body = await request.body()

    # Create intent
    intent = ExecutionIntent(
        actor=f"api#{request.client.host}",
        action=f"api.{method.lower()}",
        payload=f"{method} {path} {body.decode()[:100]}",
        timestamp=datetime.now(timezone.utc)
    )

    # Evaluate
    decision = boundary.evaluate(intent)
    proof = boundary.issue_proof(decision)

    if decision.decision == "HALT":
        raise HTTPException(
            status_code=403,
            detail={
                "blocked": True,
                "reason": decision.reason,
                "risk_score": decision.risk_score,
                "proof": proof.signature[:32]
            }
        )

    # Proceed
    response = await call_next(request)

    # Add proof header
    response.headers["X-Boundary-Proof"] = proof.signature[:32]
    response.headers["X-Risk-Score"] = str(decision.risk_score)

    return response

@app.post("/payments")
async def create_payment(amount: float):
    """Payment endpoint protected by boundary."""
    # This endpoint is protected by middleware
    return {"status": "processed", "amount": amount}
```

---

## Database Access Integration

### SQL Query Boundary

```python
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent
from datetime import datetime, timezone
import sqlite3

class SafeDBConnection:
    """Database connection with execution boundary."""

    def __init__(self, db_path: str, user_id: str):
        self.conn = sqlite3.connect(db_path)
        self.user_id = user_id
        self.boundary = ExecutionBoundaryEngine(halt_threshold=80)

    def execute(self, query: str, params: tuple = ()):
        """Execute SQL with boundary check."""
        intent = ExecutionIntent(
            actor=f"db#{self.user_id}",
            action="db.query",
            payload=query,
            timestamp=datetime.now(timezone.utc)
        )

        decision = self.boundary.evaluate(intent)
        proof = self.boundary.issue_proof(decision)

        if decision.decision == "ALLOW":
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return {
                "success": True,
                "rows": cursor.fetchall(),
                "proof": proof
            }
        else:
            return {
                "success": False,
                "reason": decision.reason,
                "risk_score": decision.risk_score,
                "proof": proof
            }

# Usage
db = SafeDBConnection("app.db", user_id="ai_assistant")

# Safe query
result = db.execute("SELECT * FROM users WHERE id = ?", (123,))
print(result["success"])  # True

# Blocked query
result = db.execute("DROP TABLE users")
print(result["success"])  # False
print(result["reason"])  # "High risk: DROP TABLE"
```

---

## Best Practices

### 1. Always Issue Proof

```python
# ❌ Bad: Evaluate but don't issue proof
decision = engine.evaluate(intent)
if decision.decision == "ALLOW":
    execute()

# ✅ Good: Always issue proof for audit trail
decision = engine.evaluate(intent)
proof = engine.issue_proof(decision)  # Creates signed ledger entry
if decision.decision == "ALLOW":
    execute()
```

### 2. Use Structured Actor IDs

```python
# ✅ Good: Structured actor IDs
actor = "langchain#agent_001"
actor = "autogpt#my_assistant"
actor = "api#192.168.1.100"
actor = "user#alice@example.com"

# ❌ Bad: Unstructured IDs
actor = "user"
actor = "agent"
```

### 3. Include Context in Payload

```python
# ✅ Good: Rich payload with context
payload = "POST /payments amount=50000 currency=USD destination=external"

# ❌ Bad: Minimal payload
payload = "payment"
```

### 4. Handle Blocked Actions Gracefully

```python
# ✅ Good: Informative error messages
if decision.decision == "HALT":
    raise ValueError(
        f"Action blocked by boundary: {decision.reason}\n"
        f"Risk score: {decision.risk_score}/100\n"
        f"Proof: {proof.signature[:16]}..."
    )

# ❌ Bad: Generic error
if decision.decision == "HALT":
    raise ValueError("Blocked")
```

### 5. Verify Ledger Integrity Periodically

```python
# ✅ Good: Periodic verification
import schedule

def verify_ledger():
    result = engine.ledger.verify_integrity()
    if not result["valid"]:
        alert_team(f"Ledger integrity violated: {result['error']}")

schedule.every().day.at("00:00").do(verify_ledger)
```

---

## Troubleshooting

### Command Always Blocked

**Issue:** All commands get HALT decision

**Solution:** Check halt threshold
```python
# Lower threshold for less strict blocking
engine = ExecutionBoundaryEngine(halt_threshold=90)  # Only block 90+ risk
```

### Ledger File Growing Too Large

**Issue:** `judgment_ledger.ndjson` file size growing rapidly

**Solution:** Implement log rotation
```python
import os
from datetime import datetime

def rotate_ledger_if_needed(max_size_mb=100):
    ledger_path = "judgment_ledger.ndjson"
    if os.path.exists(ledger_path):
        size_mb = os.path.getsize(ledger_path) / (1024 * 1024)
        if size_mb > max_size_mb:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.rename(ledger_path, f"judgment_ledger_{timestamp}.ndjson")
```

### Private Key Lost

**Issue:** `.private_key.pem` deleted, can't verify old proofs

**Solution:** Key is auto-generated if missing, but old proofs become unverifiable
```python
# ✅ Good: Backup private key
import shutil
shutil.copy(".private_key.pem", "/secure/backup/location/.private_key.pem")

# For production: Use key management service (KMS)
```

---

## Next Steps

- See [API_STABILITY.md](API_STABILITY.md) for versioning guarantees
- See [PRODUCT_IDENTITY.md](PRODUCT_IDENTITY.md) for design constraints
- See [Telegram Demo](https://github.com/Nick-heo-eg/ai-execution-boundary-telegram-demo) for complete example

---

**Last Updated:** 2026-02-22
**Version:** 0.1.0
