# Integration Guide

How to integrate agent-execution-guard (v0.2.1) into AI agents and systems.

**Version:** 0.2.0
**Target:** AI Agent Developers

---

## 1. Core Principle

All external actions must pass through the execution boundary before running.

Use the direct path:

```
ExecutionIntent → enforce_boundary() → execute
```

Boundary is always pre-execution.

---

## 2. Custom Agent Integration

```python
from datetime import datetime, timezone
from agent_execution_guard import ExecutionGuard, Intent, GuardDeniedError

guard = ExecutionGuard()

intent = Intent(
    actor="agent.ops",
    action="shell_exec",
    payload="DELETE FROM users WHERE id=123",
    timestamp=datetime.now(timezone.utc),
)

try:
    record = guard.evaluate(intent)
    # ALLOW — proceed with execution
    result = perform_action(intent.payload)
    print(f"proof: {record.proof_signature}")

except GuardDeniedError as e:
    # DENY — blocked, signed proof issued
    print(f"blocked: {e.reason}")
```

---

## 3. Advanced: Direct enforce_boundary()

For full control over engine configuration:

```python
from datetime import datetime, timezone
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent
from execution_boundary.enforce import enforce_boundary
from execution_boundary.models import ExecutionDeniedError

engine = ExecutionBoundaryEngine(halt_threshold=80)

intent = ExecutionIntent(
    actor="api#service",
    action="db_write",
    payload="INSERT INTO audit_log VALUES (...)",
    timestamp=datetime.now(timezone.utc),
)

try:
    record = enforce_boundary(intent, engine=engine)
    # ALLOW
except ExecutionDeniedError as e:
    # DENY — signed negative proof in ledger
    pass
```

---

## 4. API Gateway (Advanced)

Use boundary in middleware before critical operations:

```python
record = enforce_boundary(intent, engine=engine)
# Attach proof to response for audit traceability
response.headers["X-Boundary-Id"] = record.boundary_id
response.headers["X-Proof-Signature"] = record.proof_signature
```

---

## 5. Best Practices

### Always enforce before execution

❌ Wrong
```
evaluate → execute → issue_proof
```

✅ Correct
```
enforce_boundary() → execute
```

---

### Use structured actor IDs

```
langchain#agent_001
api#192.168.1.100
user#alice@example.com
```

---

### Keep payload meaningful

Bad: `"delete"`

Good: `"DELETE FROM users WHERE id=123"`

---

### Verify ledger integrity periodically

```python
engine.ledger.verify_integrity()
```

---

## 6. Troubleshooting

**All actions blocked**

Lower your risk threshold:
```python
guard = ExecutionGuard(halt_threshold=90)
```

**Private key lost**

Back up `.private_key.pem`. Old proofs become unverifiable if key is lost.

**Ledger file large**

Implement rotation at application layer. Core appends only — no built-in rotation.

---

## 7. Design Constraints

agent-execution-guard is:

- Deterministic
- Offline-capable
- Minimal dependency (`cryptography` only)
- Pre-execution enforcement
- Cryptographic audit proof on every decision

It is an execution boundary engine — not a policy engine, not an LLM safety layer.

---

*Last Updated: 2026-03 / Version: 0.2.0*
