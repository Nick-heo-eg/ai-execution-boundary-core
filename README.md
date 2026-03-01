# agent-execution-guard

**A lightweight execution guard for AI agents.**

Decide `ALLOW` / `HOLD` / `DENY` before your agent performs real actions.

```bash
pip install agent-execution-guard
```

---

## The problem

Your AI agent will execute anything.

```python
agent.run("wire_transfer amount=50000 to=external")   # proceeds
agent.run("delete all user records")                   # also proceeds
agent.run("send mass email to customer list")          # also proceeds
```

There is no structural layer that stops it.
Prompts can be bypassed. Guardrails can be talked around.

**This is that layer.**

---

## Quickstart

```python
from datetime import datetime, timezone
from agent_execution_guard import ExecutionGuard, Intent

guard = ExecutionGuard()

intent = Intent(
    actor="agent.finance",
    action="wire_transfer",
    payload="wire_transfer amount=50000 to=external",
    timestamp=datetime.now(timezone.utc),
)

result = guard.evaluate(intent)
print(result.decision)    # ALLOW / DENY / HOLD
print(result.risk_score)  # 0–100
print(result.reason)
```

---

## Example 1 — Finance: DENY

```python
from agent_execution_guard import ExecutionGuard, Intent, GuardDeniedError
from datetime import datetime, timezone

guard = ExecutionGuard()

intent = Intent(
    actor="agent.finance",
    action="wire_transfer",
    payload="wire_transfer amount=50000 to=external",
    timestamp=datetime.now(timezone.utc),
)

try:
    result = guard.evaluate(intent)
    print(f"Allowed: {result.boundary_id}")

except GuardDeniedError as e:
    print(f"Denied: {e.reason}")
    print(f"Proof:  {e.boundary_id}")
    # Signed negative proof issued — execution structurally blocked
```

**Output:**
```
Denied: risk_score=85 exceeds threshold=80
Proof:  3f9a1c2d-...
```

Every denial issues a **signed proof**. The agent cannot retry past it.

---

## Example 2 — Campaign AI: HOLD

```python
from agent_execution_guard import ExecutionGuard, Intent, SystemSeverity, GuardHeldError
from datetime import datetime, timezone

guard = ExecutionGuard()

intent = Intent(
    actor="campaign_ai",
    action="aggressive_targeting",
    payload="launch targeted ad campaign segment=undecided_voters",
    timestamp=datetime.now(timezone.utc),
)

# Elevated system severity (e.g. election period, market stress)
severity = SystemSeverity(score=0.60, source="geopolitical_risk_model")

try:
    result = guard.evaluate(intent, severity=severity)

except GuardHeldError as e:
    print(f"Held — requires human approval")
    print(f"Deadline: {e.deadline_ts}")
    print(f"Proof:    {e.boundary_id}")
```

**Output:**
```
Held — requires human approval
Deadline: 2026-03-01T10:28:00+00:00
Proof:    7d2f9e1a-...
```

`HOLD` is not a failure. It is a **decision checkpoint**.
Execution waits for a human token before proceeding.

---

## How it works

```
Intent → Risk Score → Severity State → Guard Decision → Signed Proof
```

| Component | What it does |
|-----------|-------------|
| Risk scoring | Rule-based 0–100 score per action |
| Severity gate | ACTIVE / OBSERVE / COOLDOWN — tightens threshold as risk rises |
| Policy guard | Unknown agent or action → immediate DENY |
| Decision trail | Every decision signed (ED25519) + ledgered (SHA-256 chain) |

### Three states

| State | Trigger | Threshold |
|-------|---------|-----------|
| ACTIVE | severity < 0.20 | risk ≥ 80 → DENY |
| OBSERVE | severity ≥ 0.20 | risk ≥ 60 → DENY |
| COOLDOWN | severity ≥ 0.40 | risk ≥ 30 → DENY |

Hysteresis prevents oscillation between states.

### Four outcomes

| Outcome | Meaning |
|---------|---------|
| `ALLOW` | Proceed. Signed proof issued. |
| `DENY` | Blocked. Signed negative proof issued. Agent cannot retry. |
| `HOLD` | Awaiting human approval. Deadline enforced. |
| `EXPIRED` | HOLD deadline passed without approval. Blocked. |

---

## Policy guard

Unknown agents and actions are denied by default.

```yaml
# policy.yaml
defaults:
  unknown_agent:  DENY
  unknown_action: DENY

identity:
  agents:
    - agent_id: "agent.finance"
      allowed_actions:
        - action: "wire_transfer"
        - action: "read_ledger"
```

```python
import yaml
with open("policy.yaml") as f:
    policy = yaml.safe_load(f)

result = guard.evaluate(intent, policy=policy)
# unknown agent → immediate DENY, signed proof, no risk scoring needed
```

---

## Cryptographic proof

Every decision — `ALLOW` and `DENY` — is signed and ledgered.

```python
# Verify any past decision
verification = guard.verify(proof)
print(verification.valid)    # True
print(verification.message)  # "Proof verified at ledger index 7"
```

- Algorithm: ED25519
- Ledger: append-only NDJSON with SHA-256 hash chain
- Verification: offline, no external dependencies

---

## Install

```bash
pip install agent-execution-guard
```

Requires Python 3.10+. No external services. Runs offline.

Optional:
```bash
pip install pyyaml          # for policy.yaml loading
pip install opentelemetry-api  # for OTel span export
```

---

## Roadmap

- [x] Rule-based risk scoring (ALLOW / DENY)
- [x] ED25519 cryptographic proof
- [x] Append-only hash-chain ledger
- [x] Severity-driven state machine (ACTIVE / OBSERVE / COOLDOWN)
- [x] Policy guard (unknown agent/action → DENY)
- [x] HOLD state + human approval checkpoint
- [ ] `pip install agent-execution-guard` (TestPyPI → PyPI)
- [ ] OTel-native decision trail export
- [ ] MCP integration for agent frameworks
- [ ] Human-in-the-loop authority token protocol

---

## License

Apache 2.0

---

*Your AI agent will execute anything. This makes it stop.*
