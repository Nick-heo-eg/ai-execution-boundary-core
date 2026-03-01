# Changelog

---

## [0.2.1] - 2026-03-02

### Fixed

- `policy=None` → `GuardDeniedError("no_policy")` — fail-closed enforced at API level
- Add `ALLOW_ALL` sentinel for explicit opt-out of identity check
- README examples aligned with required `policy` argument

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

## [Unreleased]

### Planned for v0.2.0

- LangChain tool adapter
- README example + 1 integration test

---

## Version History

- **v0.1.1** (2026-03-01): README alignment, roadmap cleanup
- **v0.1.0** (2026-03-01): Initial public release
