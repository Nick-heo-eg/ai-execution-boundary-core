# Changelog

---

## [0.1.0] - 2026-03-01

Initial public release.

### Added

- `ExecutionBoundaryEngine` — risk scoring, ALLOW/DENY decisions, ED25519 proof, hash-chain ledger
- `SeverityGate` — ACTIVE / OBSERVE / COOLDOWN state machine with hysteresis
- `PolicyGuard` — unknown agent/action → immediate DENY
- `enforce_boundary()` — unified lifecycle: evaluate → proof → ledger → exception
- `agent_execution_guard` public API — `ExecutionGuard`, `Intent`, `SystemSeverity`
- HOLD state + human approval checkpoint
- OTel span attributes: `execution.state`, `severity.score`, `severity.threshold`

### Design

- Fail-closed by default: unrecognized action → DENY, unknown state → DENY
- Every decision (ALLOW and DENY) signed and ledgered
- Offline verification, no external dependencies

---

## [0.1.1] - 2026-03-01

### Changed

- README aligned with public release strategy
- Removed LLM fusion roadmap
- Changelog condensed

---

## [0.2.0] - 2026-03-01

### Added

- `GuardedTool` LangChain adapter — wraps any callable with execution guard
- Optional `langchain-core` dependency (`pip install agent-execution-guard[langchain]`)
- 5 adapter tests

## [Unreleased]

### Planned for v0.3.0

- OTel-native decision trail export
- MCP integration

---

## Version History

- **v0.1.1** (2026-03-01): README alignment, roadmap cleanup
- **v0.1.0** (2026-03-01): Initial public release
