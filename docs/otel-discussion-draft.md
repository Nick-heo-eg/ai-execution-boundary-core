# Modeling Pre-Execution Enforcement Decisions in Agentic AI — Is There a Gap?

**Author:** Nick Heo
**Date:** 2026-02-28
**Target:** OpenTelemetry semantic-conventions — GenAI / Agentic AI Discussion

---

## Context

As agentic AI systems become more capable of taking real-world actions — executing shell commands, calling payment APIs, modifying databases — teams building on top of them are adding enforcement layers between an agent's decision and actual execution.

The current `gen_ai` semantic conventions define:

- `gen_ai.invoke_agent` — agent invocation
- `gen_ai.execute_tool` — tool execution

In practice, many systems have a layer between these two: something that evaluates whether the requested action should proceed, and either allows or blocks it. This could be a policy engine, a risk scorer, a human-approval gate, or a combination.

I haven't seen this layer represented in the current spec, and wanted to raise it as a question.

---

## Observed Ambiguity

When an enforcement layer blocks execution, the trace currently shows either a `gen_ai.execute_tool` span (if allowed) — or nothing (if blocked).

```
[current]

gen_ai.invoke_agent
  └─ gen_ai.execute_tool   ← present on allow; absent on block

If execute_tool is absent, at least three explanations are valid:
  1. The agent decided not to act
  2. An enforcement layer blocked the action
  3. A bug or error prevented execution
```

For low-stakes use cases this ambiguity may be acceptable. For systems where agents can initiate financial transactions, modify production infrastructure, or interact with external services, the inability to distinguish "blocked by policy" from "agent chose not to act" seems like a meaningful observability gap.

I've been thinking about this as a *provability gap* rather than just a logging gap: if the only evidence that an enforcement boundary was enforced is the absence of a span, that's not a verifiable audit trail.

---

## Open Questions

These are genuine questions rather than proposals — I'm curious how others are thinking about this:

**1. How are teams currently representing blocked executions in traces?**

Are there existing patterns — perhaps borrowed from RPC error spans or messaging dead-letter conventions — that already address this?

**2. Should enforcement evaluation have its own span?**

One approach we experimented with: a span emitted unconditionally for every enforcement evaluation, with outcome as an attribute (`ALLOW` / `HOLD` / `DENY`). The span exists whether or not execution proceeds, making the enforcement decision directly observable.

Would something like this belong under the `gen_ai` namespace? Or somewhere else?

**3. How should non-success paths be modeled?**

In RPC and messaging conventions, non-success paths (errors, retries, dead letters) are as observable as success paths. Should something similar apply to enforcement decisions in agentic systems?

**4. Is there a meaningful distinction between `boundary_id` and `trace_id`?**

A trace may contain multiple agent steps, each with its own enforcement evaluation. In our experimentation, treating each enforcement decision as a distinct logical unit (separate from the trace) made audit queries more tractable. Is this a pattern worth standardizing, or is it over-engineering for the current state of agentic systems?

---

## What We've Been Experimenting With

For context: we've been building a reference implementation of this enforcement layer ([`ai-execution-boundary-core`](https://github.com/Nick-heo-eg/ai-execution-boundary-core), Python, 57 tests) and a Node.js OTel 1.39 demo with Jaeger to visualize the span topology.

The span structure we arrived at looks like this:

```
gen_ai.invoke_agent
  └─ execution.boundary          ← emitted for every enforcement evaluation
       attr: exec.decision.outcome  = ALLOW | HOLD | DENY
             exec.decision.hash     = sha256(decision content, deterministic)
             exec.policy.hash       = sha256(policy snapshot)
             exec.boundary.id       = UUIDv4, independent of trace_id
       │
       ├─ [ALLOW]  gen_ai.execute_tool
       ├─ [HOLD]   execution.awaiting_approval
       └─ [DENY]   execution.blocked
```

One property we found useful: `exec.decision.hash` is a content fingerprint — identical decision inputs always produce the same hash, regardless of when or how many times the evaluation runs. This makes it possible to detect duplicate decisions and replay audit queries.

We're not proposing this as a spec — we're sharing it as one data point in case it's useful for discussion.

---

## Is This Already Being Discussed?

Before going further, it would help to know:

- Is there an existing issue or discussion on enforcement/policy evaluation spans in agentic contexts?
- Is the GenAI SIG actively working on the gap between `invoke_agent` and `execute_tool`?
- Would this be better raised as a separate working group topic, or does it fit within the current GenAI discussion?

Happy to provide more detail on the implementation or the specific use cases that motivated this, if that would be useful.

---

## References

- Reference implementation: [ai-execution-boundary-core](https://github.com/Nick-heo-eg/ai-execution-boundary-core)
- Current GenAI semantic conventions: [opentelemetry.io/docs/specs/semconv/gen-ai](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
