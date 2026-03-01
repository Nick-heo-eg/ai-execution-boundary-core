# agent-execution-guard

Deterministic ALLOW / HOLD / DENY execution boundary for AI agent actions.

```bash
pip install agent-execution-guard
```

---

## The problem

AI agents execute actions without structural constraints.
Prompts can be bypassed. Guardrails can be reasoned around.

This library puts a deterministic gate between decision and execution.

---

## Quickstart

```python
from datetime import datetime, timezone
from agent_execution_guard import ExecutionGuard, Intent, ALLOW_ALL

guard = ExecutionGuard()

intent = Intent(
    actor="agent.finance",
    action="wire_transfer",
    payload="wire_transfer amount=50000 to=external",
    timestamp=datetime.now(timezone.utc),
)

# policy is required — no policy = no execution (fail-closed)
# use ALLOW_ALL to skip identity check and rely on risk scoring only
try:
    result = guard.evaluate(intent, policy=ALLOW_ALL)
    print(result.risk_score)  # 0–100

except Exception as e:
    print(e)  # DENY or HOLD
```

---

## Example 1 — DENY

```python
from agent_execution_guard import ExecutionGuard, Intent, GuardDeniedError, ALLOW_ALL
from datetime import datetime, timezone

# halt_threshold=39: wire_transfer scores 40 → DENY
guard = ExecutionGuard(halt_threshold=39)

intent = Intent(
    actor="agent.finance",
    action="wire_transfer",
    payload="wire_transfer amount=50000 to=external",
    timestamp=datetime.now(timezone.utc),
)

try:
    guard.evaluate(intent, policy=ALLOW_ALL)

except GuardDeniedError as e:
    print(f"Denied: {e.reason}")
    print(f"Proof:  {e.boundary_id}")
```

Output:
```
Denied: General command
Proof:  3f9a1c2d-...
```

Every denial issues a signed proof. The agent cannot retry past it.

---

## Example 2 — Severity-adaptive gate

```python
from agent_execution_guard import ExecutionGuard, Intent, SystemSeverity, GuardDeniedError
from datetime import datetime, timezone

guard = ExecutionGuard()

intent = Intent(
    actor="campaign_ai",
    action="aggressive_targeting",
    payload="launch targeted ad campaign segment=undecided_voters",
    timestamp=datetime.now(timezone.utc),
)

# score=0.60 → COOLDOWN state → threshold drops 80 → 30 → risk(40) > 30 → DENY
high = SystemSeverity(score=0.60, source="risk_model")
low  = SystemSeverity(score=0.10, source="baseline")

try:
    guard.evaluate(intent, severity=high, policy=ALLOW_ALL)
except GuardDeniedError:
    print("DENY  (COOLDOWN — threshold=30)")

result = guard.evaluate(intent, severity=low, policy=ALLOW_ALL)
print("ALLOW (ACTIVE  — threshold=80)")
```

Output:
```
DENY  (COOLDOWN — threshold=30)
ALLOW (ACTIVE  — threshold=80)
```

Same action. Different severity state. Different outcome.

---

## Policy guard

`policy` is required. No policy = no execution (fail-closed by default).

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
```

```python
import yaml
with open("policy.yaml") as f:
    policy = yaml.safe_load(f)

guard.evaluate(intent, policy=policy)
# unknown agent → immediate DENY, signed proof issued
```

To skip identity check and rely on risk scoring only:

```python
from agent_execution_guard import ALLOW_ALL

guard.evaluate(intent, policy=ALLOW_ALL)
```

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

### States

| State | Severity | Threshold |
|-------|----------|-----------|
| ACTIVE | < 0.20 | risk ≥ 80 → DENY |
| OBSERVE | ≥ 0.20 | risk ≥ 60 → DENY |
| COOLDOWN | ≥ 0.40 | risk ≥ 30 → DENY |

### Outcomes

| Outcome | Meaning |
|---------|---------|
| `ALLOW` | Proceed. Signed proof issued. |
| `DENY` | Blocked. Signed negative proof. Agent cannot retry. |
| `HOLD` | Awaiting human approval. Deadline enforced. |

---

## Cryptographic proof

Every decision — ALLOW and DENY — is signed and ledgered.

- ED25519 signatures
- Append-only NDJSON hash chain
- Offline verification, no external dependencies

---

## Requirements

- Python 3.10+
- `cryptography>=42.0.0`

Optional:
```bash
pip install pyyaml             # policy.yaml support
pip install opentelemetry-api  # OTel span export
```

---

## Roadmap

- [x] Risk scoring + ALLOW / DENY
- [x] ED25519 cryptographic proof + hash-chain ledger
- [x] Severity-driven state machine (ACTIVE / OBSERVE / COOLDOWN)
- [x] Policy guard (unknown agent/action → DENY)
- [x] HOLD state + human approval checkpoint
- [ ] LangChain adapter (`GuardedTool`)
- [ ] OTel-native decision trail export
- [ ] MCP integration

---

## License

Apache 2.0
