# execution-boundary

**A risk-adaptive execution control layer.**

This is not an agent framework. This is not a guardrail.
This is a deterministic boundary between decision and execution.

> Execution is not default.

---

## What this does

When an AI agent — or any automated system — attempts an action,
`execution-boundary` answers one question:

**Should this execute?**

Not by asking the LLM. Not by checking a prompt.
By evaluating policy, identity, severity, and irreversibility
through a deterministic state machine.

```
Agent Request → Severity Score → State Machine → Gate Decision → Decision Trail
```

If the answer is no, execution stops. Structurally.
The agent cannot override it. The LLM cannot talk its way through.

---

## Core architecture

### Three-state execution control

```
ACTIVE ──→ OBSERVE ──→ COOLDOWN
  ↑                        │
  └────────────────────────┘
       (hysteresis exit)
```

Most systems are binary: PASS or FAIL.
This system has **OBSERVE** — a state where execution is restricted
but not frozen. Severity drives the transitions. Hysteresis prevents oscillation.

| State    | Meaning                            | Gate threshold |
|----------|------------------------------------|----------------|
| ACTIVE   | Normal operation                   | risk ≥ 80 → DENY |
| OBSERVE  | Elevated risk — tightened boundary | risk ≥ 60 → DENY |
| COOLDOWN | High risk — near-lockdown          | risk ≥ 30 → DENY |

Transitions use hysteresis:
- Enter COOLDOWN: severity ≥ 0.40
- Exit COOLDOWN: severity < 0.28
- Between 0.28–0.40: previous state maintained — no oscillation

### Deterministic gate

Every execution request is evaluated against:

- **Action risk score** — rule-based, 0–100 scale
- **Current system severity** — continuous signal [0.0–1.0]
- **State machine** — ACTIVE / OBSERVE / COOLDOWN with hysteresis
- **Effective threshold** — dynamically adjusted by state

Fail-closed by default. Unrecognized action → DENY. Unknown state → DENY.

### Decision trail

Every gate decision is logged with:

- `boundary_id` — unique decision identifier (per boundary crossing)
- `decision_hash` — deterministic content fingerprint (SHA-256)
- `decision_instance_hash` — per-boundary tamper-evident ID
- `policy_hash` — which policy version was enforced
- `outcome` — ALLOW / HOLD / DENY / EXPIRED
- `proof_signature` — ED25519 signature over the decision entry
- `ledger_index` — position in the append-only hash-chain ledger

Compatible with OpenTelemetry `exec.*` semantic conventions.

---

## Quick start

```bash
pip install cryptography pyyaml
```

### Basic gate

```python
from datetime import datetime, timezone
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent, enforce_boundary
from execution_boundary import ExecutionDeniedError, ExecutionHeldError

engine = ExecutionBoundaryEngine(halt_threshold=80)

intent = ExecutionIntent(
    actor="agent.finance",
    action="wire_transfer",
    payload="wire_transfer amount=50000 to=external",
    timestamp=datetime.now(timezone.utc),
)

try:
    record = enforce_boundary(intent, engine=engine)
    # ALLOW — proceed with execution
    print(f"Allowed: {record.boundary_id}")

except ExecutionDeniedError as e:
    # DENY — structurally blocked, signed proof issued
    print(f"Denied: {e.reason}")

except ExecutionHeldError as e:
    # HOLD — awaiting human authorization
    print(f"Held until: {e.deadline_ts}")
```

### Severity-adaptive gate

```python
from execution_boundary import SeverityGate, SystemSeverity

gate = SeverityGate()

# System severity from any source: infrastructure, portfolio, CI/CD, etc.
current_severity = SystemSeverity(score=0.55, source="infra_error_rate")

result = gate.evaluate(
    intent,
    engine=engine,
    system_severity=current_severity,
)

print(f"State: {result.state}")               # COOLDOWN
print(f"Threshold: {result.effective_threshold}")  # 30
print(f"Denied: {result.denied}")             # True (risk=40 > threshold=30)
print(f"State changed: {result.state_changed}")
```

---

## Why this exists

The AI agent ecosystem is building execution capabilities
faster than execution accountability.

Current approaches:

- **Alignment** — hopes the model behaves correctly
- **Guardrails** — filters input/output at the prompt level
- **Monitoring** — observes what happened after the fact

What's missing:

- **Deterministic execution control** — structure that prevents unauthorized execution before it happens
- **Risk-adaptive authority** — execution permissions that respond to system state
- **Cryptographic decision trails** — proof of what was decided, why, and under which policy

This layer fills that gap.

---

## Production evidence

This architecture is not theoretical.

The core state machine — severity scoring, hysteresis-based transitions,
and deterministic execution control — has been validated
in a live risk-adaptive system handling real financial decisions.

Same structure. Different domain. Proven behavior.

---

## Components

| Module | Responsibility |
|--------|----------------|
| `engine.py` | Rule-based risk scoring + ALLOW/HALT/HOLD decisions |
| `enforce.py` | Unified lifecycle: evaluate → proof → ledger → exception |
| `severity_gate.py` | Severity score → state machine → adaptive threshold |
| `crypto.py` | ED25519 key management + signing |
| `ledger.py` | Append-only NDJSON hash-chain ledger |
| `models.py` | `ExecutionIntent`, `Decision`, `BoundaryRecord`, exceptions |

---

## Risk scoring

Rule-based evaluation (0–100 scale):

| Range | Level    | Examples                         |
|-------|----------|----------------------------------|
| 0–20  | Low      | `ls`, `cat`, `grep`, `pwd`       |
| 21–60 | Medium   | `rm file`, general modifications |
| 61–80 | High     | `drop table`, schema changes     |
| 81–100| Critical | `rm -rf /`, root deletion        |

Default halt threshold: **80** (dynamically adjusted by severity state).

---

## Cryptographic proof

**Every decision — ALLOW and DENY — is signed and ledgered.**

- Algorithm: ED25519
- Ledger: append-only NDJSON with SHA-256 hash chain
- Verification: offline, no external dependencies

```python
# Verify any past decision
result = engine.verify(proof)
print(result.valid)    # True
print(result.message)  # "Proof verified at ledger index 7"
```

---

## Roadmap

- [x] Rule-based risk scoring (ALLOW / HALT)
- [x] ED25519 cryptographic proof
- [x] Append-only hash-chain ledger
- [x] Unified enforcement lifecycle (enforce_boundary)
- [x] HOLD state + human approval flow
- [x] 2-hash structure (decision_hash + decision_instance_hash)
- [x] Severity-driven state machine (ACTIVE / OBSERVE / COOLDOWN)
- [x] Hysteresis-based state transitions
- [ ] OTel-native decision trail export
- [ ] MCP integration for agent frameworks
- [ ] Policy versioning and hot-reload
- [ ] Human-in-the-loop authority token protocol

---

## Related work

- [OpenTelemetry GenAI Semantic Conventions](https://github.com/open-telemetry/semantic-conventions)
- NIST AI Risk Management Framework
- EU AI Act high-risk classification

---

## License

Apache 2.0

---

*"Observability without control is incomplete.
Control without risk adaptation is brittle.
This layer connects both."*
