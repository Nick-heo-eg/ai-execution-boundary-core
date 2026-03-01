# Product Identity

**Version:** 0.2.0
**Positioning:** Developer Infrastructure
**Status:** Public (Apache 2.0)

---

## Core Identity (One Sentence)

> **A deterministic execution boundary engine for AI agents with cryptographic proof.**

This sentence defines everything:
- **What:** Execution boundary engine
- **How:** Deterministic (rule-based, no randomness)
- **For whom:** AI agents (not general software)
- **Why:** Cryptographic proof (verifiable, tamper-proof)

---

## Product Positioning

### We Are

- **Developer infrastructure** for AI agent safety
- **Drop-in SDK** that requires minimal integration
- **Deterministic engine** that produces verifiable outcomes
- **Offline-capable** runtime guardrail (no cloud dependency)

### We Are NOT

- Compliance tool (we don't claim regulatory certification)
- Enterprise governance platform (not multi-tenant SaaS)
- Model quality improvement tool (not performance optimizer)
- Cost reduction solution (judgment has value beyond cost)

---

## Target Users

### Primary Audience

**AI Agent Developers:**
- Building custom AI agents (LangChain, AutoGPT, CrewAI, etc.)
- Need pre-execution safety without cloud dependencies
- Want cryptographic audit trail for decisions
- Value deterministic behavior over probabilistic risk scoring

**LLM Application Engineers:**
- Integrating LLMs into production systems
- Need runtime boundaries for dangerous operations
- Want signed proof of what AI was allowed/blocked from doing
- Require offline verification capability

**DevOps/Platform Engineers:**
- Responsible for AI infrastructure safety
- Need lightweight, embeddable decision layer
- Want minimal dependencies (cryptography only)
- Value simplicity over feature bloat

### Secondary Audience

**Open Source AI Projects:**
- Community-driven AI tools needing governance layer
- Want transparent, auditable decision logic
- Need zero-cost, self-hosted solution

**Startup AI Teams:**
- Moving fast with AI features
- Need safety guardrails without enterprise overhead
- Want proof of responsible AI decisions for future compliance

### Not Our Audience (Now)

- Enterprise security teams → Future v1.0+
- Compliance officers → Future product extension
- AI researchers → May use, but not primary design driver

---

## Use Cases

### 1. AI Agent Shell Execution

**Scenario:** LangChain agent can execute shell commands

**Without Core:**
```python
# No safety boundary
result = subprocess.run(agent_command, shell=True)
```

**With Core:**
```python
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent

engine = ExecutionBoundaryEngine()
intent = ExecutionIntent(
    actor="agent#123",
    action="shell.exec",
    payload=agent_command,
    timestamp=datetime.now()
)

decision = engine.evaluate(intent)

if decision.decision == "ALLOW":
    result = subprocess.run(agent_command, shell=True)
    proof = engine.issue_proof(decision)
    # Proof signed and logged to ledger
else:
    # Blocked with cryptographic proof of rejection
    proof = engine.issue_proof(decision)
```

**Value:**
- Pre-execution blocking (not post-execution detection)
- Signed proof of every decision (ALLOW or HALT)
- Offline verification of audit trail

---

### 2. API Call Governance

**Scenario:** AI agent making external API calls

**With Core:**
```python
intent = ExecutionIntent(
    actor="agent#123",
    action="api.call",
    payload=f"POST /payments amount={amount}",
    timestamp=datetime.now()
)

decision = engine.evaluate(intent)
# Risk score based on amount, method, endpoint
```

---

### 3. Database Operation Boundary

**Scenario:** AI assistant with database access

**With Core:**
```python
intent = ExecutionIntent(
    actor="assistant#456",
    action="db.query",
    payload="DROP TABLE users",
    timestamp=datetime.now()
)

decision = engine.evaluate(intent)
# HIGH risk → HALT → Signed proof of block
```

---

## Product Strategy

### Current Phase: v0.1 (Developer Infrastructure)

**Focus:**
- Clean SDK interface
- Minimal dependencies
- Maximum portability
- Developer documentation
- Integration examples

**Distribution:**
- Public (PyPI: agent-execution-guard)
- Apache 2.0

---

### Future Phases

**v0.2: LangChain Adapter** ✅
- GuardedTool wrapper
- Optional langchain-core dependency

**v0.3: OTel + MCP**
- OTel-native decision trail export
- MCP integration for agent frameworks

**v0.4+: Ecosystem Expansion**
- Additional framework adapters
- Advanced audit/reporting

---

## Competitive Positioning

### vs. LLM-based Content Filters

**Them:** Post-generation filtering (after LLM output)
**Us:** Pre-execution boundary (before action taken)

**Them:** Probabilistic (different results each run)
**Us:** Deterministic (same input → same output)

---

### vs. Enterprise AI Governance Platforms

**Them:** Heavy, multi-tenant, cloud-required
**Us:** Lightweight, embeddable, offline-capable

**Them:** Compliance-first positioning
**Us:** Developer-first, compliance-ready

---

### vs. API Rate Limiters / Circuit Breakers

**Them:** Performance/availability focus
**Us:** Risk/safety focus

**Them:** No cryptographic proof
**Us:** Signed, verifiable decisions

---

## Design Constraints (Locked)

These constraints define the product and must not change in v0.x:

1. **Deterministic:** Same intent → same decision
2. **Offline:** No network calls in decision path
3. **Minimal:** Only `cryptography` dependency
4. **Stateless:** No engine state (except ledger append)
5. **Verifiable:** Every decision produces cryptographic proof

Breaking any of these = major version bump (v1.0+)

---

## Success Metrics (Future)

When we go public, success looks like:

**Adoption:**
- GitHub stars (developer interest)
- pip installs (actual usage)
- Integration examples (ecosystem fit)

**Quality:**
- Issue response time
- Documentation clarity
- API stability (zero breaking changes in minor versions)

**Community:**
- Contributor growth
- Third-party integrations
- Conference talks / blog posts

---

## Language and Messaging

### Permitted Language

- "Execution boundary engine"
- "Pre-execution judgment layer"
- "Deterministic risk evaluation"
- "Cryptographic proof of decisions"
- "Offline-capable guardrail"
- "Developer infrastructure"

### Forbidden Language

- "Compliance tool" (implies regulatory certification)
- "High-risk AI solution" (regulatory positioning)
- "Make models run better" (we don't improve model quality)
- "Cost reduction" (judgment has value beyond cost)
- "AI safety silver bullet" (we're one layer, not complete solution)

---

## Open vs. Closed Strategy

**Runtime Core (This Repo):**
- Currently: Private
- Future: Public (OSS or dual-license)
- Rationale: Execution logic is valuable but not secret

**Interface Layer:**
- Open from start (integration patterns, examples)
- Value: Ecosystem growth, adoption

**Extensions (Future):**
- Additional framework adapters
- Compliance modules (future)

---

## Decision Authority

Product decisions validate against this document.

If a feature doesn't align with "Developer Infrastructure for AI Agents," it belongs in a different product or future version.

**Last Updated:** 2026-03-01
**Next Review:** v0.3.0 planning
