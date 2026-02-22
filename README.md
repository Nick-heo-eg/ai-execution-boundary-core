# AI Execution Boundary Core

**A deterministic execution boundary engine for AI agents with cryptographic proof.**

**Version:** 0.1.0 | **Status:** Interface Frozen | **License:** Private (Future-openable)

---

## What This Is

Developer infrastructure for AI agent safety. Drop-in SDK that provides:

1. **Pre-execution evaluation** of AI agent actions (shell commands, API calls, DB operations)
2. **Deterministic decisions** (ALLOW or HALT) based on rule-based risk scoring
3. **Cryptographic proof** (ED25519 signatures) for every decision
4. **Immutable audit trail** (hash-chain ledger) with offline verification
5. **Zero cloud dependencies** — runs entirely offline

**Use this when:** Your AI agent can execute dangerous operations and you need verifiable proof of what was allowed or blocked.

---

## Why Use This

### For AI Agent Developers

- **Pre-execution blocking** instead of post-execution cleanup
- **Deterministic decisions** (same input → same output, no LLM randomness)
- **Signed proof** of every decision for audit trails
- **Minimal dependencies** (only `cryptography` library)
- **Works offline** (no API calls, no cloud services)

### Common Use Cases

1. **AI agents with shell access** (LangChain, AutoGPT, CrewAI)
2. **LLM apps making API calls** (payment APIs, external services)
3. **AI assistants with database access** (SQL execution, schema changes)
4. **Autonomous systems** requiring verifiable decision logs

---

## Scope

**In Scope:**
- Pre-execution risk evaluation
- Cryptographic proof issuance (ED25519)
- Immutable ledger (hash chain)
- Offline verification

**Out of Scope:**
- UI/UX layers
- Transport adapters (Telegram, HTTP, etc.)
- Multi-tenant SaaS
- LLM-based risk scoring (v0.2+)
- Compliance certification

---

## Architecture

```
┌─────────────────────────────────┐
│  Product Layer (SaaS)           │  ← Multi-tenant, Policy UI, Audit
├─────────────────────────────────┤
│  Adapter Layer (Integrations)   │  ← Telegram, CLI, API Gateway
├─────────────────────────────────┤
│  Core Layer (This Repo)         │  ← Decision Engine, Proof, Ledger
└─────────────────────────────────┘
```

**This repository contains the Core only.**

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Nick-heo-eg/ai-execution-boundary-core.git
cd ai-execution-boundary-core

# Install dependencies
pip install cryptography

# Run tests
PYTHONPATH=src pytest tests/ -v
# → 39 passed in 0.22s
```

### Basic Usage

```python
from datetime import datetime, timezone
from execution_boundary import (
    ExecutionBoundaryEngine,
    ExecutionIntent
)

# Initialize engine
engine = ExecutionBoundaryEngine(
    halt_threshold=80  # Block commands with risk >= 80
)

# AI agent wants to execute a shell command
agent_command = "rm -rf /"

# Create execution intent
intent = ExecutionIntent(
    actor="agent#123",
    action="shell.exec",
    payload=agent_command,
    timestamp=datetime.now(timezone.utc)
)

# Evaluate risk
decision = engine.evaluate(intent)
print(f"Decision: {decision.decision}")  # → "HALT"
print(f"Risk: {decision.risk_score}/100")  # → "95/100"
print(f"Reason: {decision.reason}")  # → "Critical: root deletion"

# Issue cryptographic proof
proof = engine.issue_proof(decision)
print(f"Signature: {proof.signature[:32]}...")  # → Hex signature
print(f"Ledger index: {proof.ledger_index}")  # → 0

# Later: Verify proof integrity
result = engine.verify(proof)
print(f"Valid: {result.valid}")  # → True
```

### Integration Example

```python
import subprocess
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent

engine = ExecutionBoundaryEngine()

def safe_shell_exec(command: str, actor: str):
    """Execute shell command with boundary check."""
    intent = ExecutionIntent(
        actor=actor,
        action="shell.exec",
        payload=command,
        timestamp=datetime.now(timezone.utc)
    )

    decision = engine.evaluate(intent)
    proof = engine.issue_proof(decision)

    if decision.decision == "ALLOW":
        # Execute and return result
        result = subprocess.run(command, shell=True, capture_output=True)
        return {"executed": True, "proof": proof, "output": result.stdout}
    else:
        # Blocked with signed proof
        return {"executed": False, "proof": proof, "reason": decision.reason}

# Use with AI agent
result = safe_shell_exec("ls -la", actor="agent#123")
# → {"executed": True, "proof": <Proof>, "output": <bytes>}

result = safe_shell_exec("rm -rf /", actor="agent#123")
# → {"executed": False, "proof": <Proof>, "reason": "Critical: root deletion"}
```

---

## Design Principles

1. **No External Dependencies** (except `cryptography`)
2. **Deterministic** (same input → same output)
3. **Offline-capable** (no network required)
4. **Stateless** (except ledger append)

---

## Components

| Module | Responsibility | Lines |
|--------|---------------|-------|
| `interface.py` | Base contract | 99 |
| `models.py` | Data models | 71 |
| `risk.py` | Rule-based risk scoring | 59 |
| `engine.py` | Complete implementation | 149 |
| `crypto.py` | ED25519 signing | 161 |
| `ledger.py` | Hash-chain ledger | 186 |

**Total:** 7 source files, 6 test files, 39 tests

---


---

## Risk Scoring

Rule-based evaluation (0-100 scale):

- **0-20**: Low risk (read-only: `ls`, `cat`, `grep`)
- **21-60**: Medium risk (modifications: `rm file`)
- **61-80**: High risk (database: `drop table`)
- **81-100**: Critical risk (system destruction: `rm -rf /`)

Threshold (default): 80 (HALT if >= 80)

---

## Cryptographic Proof

**Signing:**
- Algorithm: ED25519
- Key: Auto-generated or loaded from `.private_key.pem`
- Signature: Hex-encoded

**Ledger:**
- Format: NDJSON (newline-delimited JSON)
- Hash chain: Each entry → previous hash
- Genesis: `"0" * 64` for first entry

**Verification:**
- Signature validity
- Hash chain continuity
- Entry integrity

---

## File Artifacts

Generated during operation:

```
.private_key.pem          # ED25519 private key (auto-generated)
judgment_ledger.ndjson    # Append-only ledger
```

**Both are in `.gitignore`** — not committed to repo.

---

## Documentation

- **[API_STABILITY.md](API_STABILITY.md)** — Public API guarantees and versioning policy
- **[CHANGELOG.md](CHANGELOG.md)** — Version history and release notes
- **[PRODUCT_IDENTITY.md](PRODUCT_IDENTITY.md)** — Product positioning and strategy

---

## Examples

- **[Telegram Integration](https://github.com/Nick-heo-eg/ai-execution-boundary-telegram-demo)** — Reference implementation with Telegram bot
- **LangChain Integration** — Coming soon
- **AutoGPT Integration** — Coming soon

---

## Version 0.1 Status

✅ **Interface Sealed**
✅ **Risk Engine Complete**
✅ **Decision Logic Complete**
✅ **Cryptographic Proof Complete**
✅ **Ledger Complete**
✅ **Tests Passing** (39/39)

---

## Future Versions

- v0.2: Risk fusion (Rule + LLM hybrid)
- v0.3: HOLD state + human approval flow
- v0.4: Enforcement gate integration
