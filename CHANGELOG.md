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

## [Unreleased]

### Planned for v0.2.0

- LangChain tool adapter
- README example + 1 integration test

---

## Version History

- **v0.1.0** (2026-03-01): Initial public release
