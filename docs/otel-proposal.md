# Pre-Execution Boundary Spans for Agentic AI: A Gap in the Current GenAI Semantic Conventions

**Author:** Nick Heo
**Date:** 2026-02-28
**Target:** OpenTelemetry semantic-conventions — GenAI / Agentic AI Discussion
**Reference impl:** [`ai-execution-boundary-core`](https://github.com/Nick-heo-eg/ai-execution-boundary-core) (Python, 57 tests — deterministic fingerprint + instance hash)

---

## The Gap

The current `gen_ai` semantic conventions ([status: Development](https://opentelemetry.io/docs/specs/semconv/gen-ai/)) define spans for:

- `gen_ai.invoke_agent` — agent invocation
- `gen_ai.execute_tool` — tool execution result

**What is missing:** the moment *between* `invoke_agent` and `execute_tool` — where an agent decides to take a real-world action, and where a governance layer must decide whether that action is permitted.

Today's `execute_tool` span captures **what ran**. It cannot capture **what was stopped**.

When an AI agent attempts `rm -rf /`, `DROP TABLE users`, or `transfer_money(amount=50000)`, the trace shows either a successful `execute_tool` span — or silence. There is no standard span structure for the enforcement decision that prevented execution.

This is not a logging gap. It is a **provability gap**: you cannot prove a boundary was enforced if the only evidence is absence of a span.

---

## The Problem, Precisely

```
[current topology]

gen_ai.invoke_agent
  └─ gen_ai.execute_tool   ← exists on success; absent on block
                              no standard evidence of blocking decision

[problem]
If execute_tool is absent, three explanations are equally valid:
  1. The agent decided not to act
  2. A boundary blocked the action
  3. A bug prevented execution

These are indistinguishable in the current spec.
```

For autonomous agents with real-world consequences — financial transactions, system operations, API calls — this ambiguity is not acceptable.

---

## Proposed Span: `execution.boundary`

A standard span that sits between agent decision and tool execution, emitted **unconditionally** for every enforcement evaluation:

```
gen_ai.invoke_agent
  └─ execution.boundary                       ← always emitted
       attrs: exec.boundary.id                 ← UUIDv4, ≠ trace_id
              exec.decision.outcome            ← ALLOW | HOLD | DENY | EXPIRED
              exec.decision.hash               ← sha256(canonical decision fields)
              exec.policy.hash                 ← sha256(policy snapshot)
              exec.decision.risk_score         ← 0–100
              exec.actor.id                    ← who requested
              exec.run.id                      ← groups multi-step agent runs
              exec.negative_proof              ← true when non-ALLOW
       │
       ├─ [ALLOW]  gen_ai.execute_tool         ← execution proceeds
       ├─ [HOLD]   execution.awaiting_approval ← negative proof span
       └─ [DENY]   execution.blocked           ← negative proof span
```

**Key invariant:** If `exec.decision.outcome != ALLOW`, no `gen_ai.execute_tool` span exists.
**Key invariant:** If `exec.decision.outcome != ALLOW`, `exec.negative_proof = true` is written to ledger.

This makes blocking decisions **observable, attributable, and verifiable** — not just inferred from silence.

---

## Why `boundary_id ≠ trace_id`

A trace may contain multiple agent steps. A single `boundary_id` represents exactly one enforcement evaluation — a logical decision unit independent of the distributed trace.

- `trace_id`: groups all spans in a request
- `run_id`: groups multiple boundaries in one agent run (`exec.run.id`)
- `boundary_id`: uniquely identifies one enforcement decision (`exec.boundary.id`)

This allows fine-grained audit: "which boundary, in which run, made which decision, under which policy version."

---

## Negative Proof as a First-Class Concept

Current observability thinking treats absence as acceptable evidence of non-occurrence. For agentic AI, this is insufficient.

**Negative proof** means: when an action is blocked, the blocking decision must be as observable as the action itself would have been.

- `execution.blocked` span — emitted on DENY
- `execution.awaiting_approval` span — emitted on HOLD
- Both include `exec.negative_proof = true`
- Both are written to an append-only, cryptographically signed ledger (ED25519)
- Sampling rule: non-ALLOW traces **must** be sampled at 100%

This produces an audit trail where the absence of `execute_tool` is not silence — it is a signed, ledger-backed record that execution was evaluated and blocked.

---

## Implementation Evidence

This is not a theoretical proposal. The full lifecycle is implemented and tested:

| Component | Status |
|-----------|--------|
| `enforce_boundary()` single entry point | ✅ implemented |
| `boundary_id` (UUIDv4, ≠ trace_id) | ✅ 57 tests pass (T1–T5 determinism & instance separation verified) |
| `decision_hash` (SHA-256, deterministic) | ✅ |
| `policy_hash` (policy snapshot audit) | ✅ |
| DENY → `ExecutionDeniedError` (exception-based halt) | ✅ |
| HOLD → `ExecutionHeldError` + `deadline_ts` | ✅ |
| EXPIRED → `ExecutionExpiredError` + OTel event | ✅ |
| Negative proof to ED25519 ledger (ALLOW + DENY) | ✅ |
| OTel `exec.*` attributes (no-op fallback) | ✅ |
| `run_id` propagation to span attribute | ✅ |
| Works without OTel installed | ✅ |

Determinism guarantee: identical decision inputs produce identical `decision_hash` (content fingerprint), while each boundary crossing produces a unique `decision_instance_hash`.

Span topology verified in Node.js OTel 1.39 demo (Jaeger UI).
Integration: `invest-core-private` financial execution pipeline (190/190 tests pass).

---

## Proposed `exec.*` Attribute Namespace

| Attribute | Type | Description |
|-----------|------|-------------|
| `exec.boundary.id` | string | UUIDv4 per enforcement evaluation (≠ trace_id) |
| `exec.decision.outcome` | string | `ALLOW` / `HOLD` / `DENY` / `EXPIRED` |
| `exec.decision.hash` | string | SHA-256 over canonical decision fields |
| `exec.policy.hash` | string | SHA-256 over policy snapshot |
| `exec.decision.risk_score` | int | 0–100 |
| `exec.actor.id` | string | Agent/system requesting execution |
| `exec.run.id` | string | Groups multiple boundaries in one agent run |
| `exec.approval.deadline` | string | ISO-8601 UTC — HOLD state only |
| `exec.negative_proof` | bool | `true` when HOLD / DENY / EXPIRED |
| `exec.block.reason` | string | Human-readable reason for non-ALLOW |

---

## The Ask

1. **Recognize `execution.boundary` as a semantic convention span** for agentic AI enforcement
2. **Define `exec.*` as a reserved namespace** for pre-execution boundary attributes
3. **Establish the negative proof invariant** as a required property: non-ALLOW decisions must produce observable spans, not silence
4. **Align with `gen_ai.execute_tool`**: `execution.boundary` should be the mandatory parent when enforcement is present

This is consistent with existing OTel RPC and messaging semantic conventions, which define not just success spans but error and retry spans — making non-success paths as observable as success paths.

---

## References

- Reference implementation: [ai-execution-boundary-core](https://github.com/Nick-heo-eg/ai-execution-boundary-core)
- OTel demo (Node.js, Jaeger): [execution-boundary-otel-1.39-demo](https://github.com/Nick-heo-eg/ai-execution-boundary-telegram-demo)
- Current GenAI semantic conventions: [opentelemetry.io/docs/specs/semconv/gen-ai](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- OTel semantic-conventions repo: [github.com/open-telemetry/semantic-conventions](https://github.com/open-telemetry/semantic-conventions)
