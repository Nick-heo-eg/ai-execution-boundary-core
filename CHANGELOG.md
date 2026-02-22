# Changelog

All notable changes to the AI Execution Boundary Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-02-22

### Added

**Core Engine:**
- `ExecutionBoundaryEngine` implementation with complete risk evaluation, decision logic, cryptographic proof, and ledger integration
- `ExecutionBoundary` abstract interface defining core contract (`evaluate`, `issue_proof`, `verify`)
- `ExecutionIntent` input model for execution requests
- `Decision` output model with risk scoring and decision logic
- `Proof` cryptographic proof model with ED25519 signatures
- `VerificationResult` model for proof verification

**Risk Scoring:**
- Rule-based risk evaluation engine (`risk.py`)
- 0-100 risk score calculation based on command patterns
- Risk tiers: LOW (0-20), MEDIUM (21-60), HIGH (61-80), CRITICAL (81-100)
- Default halt threshold: 80 (blocks CRITICAL commands)

**Cryptographic Proof:**
- ED25519 digital signature implementation (`crypto.py`)
- `KeyManager` for private key generation and persistence
- Deterministic signing with canonical JSON serialization
- Public key verification support

**Immutable Ledger:**
- Hash-chain ledger implementation (`ledger.py`)
- NDJSON file format (newline-delimited JSON)
- Genesis hash support (`"0" * 64` for first entry)
- Chain integrity verification (signature + hash continuity)
- Append-only design (no modifications or deletions)

**Testing:**
- 39 comprehensive tests covering all components
- Unit tests: risk scoring, crypto, ledger, engine
- Integration tests: end-to-end evaluation → proof → verification flows
- Test coverage for edge cases (empty commands, malformed inputs, chain breaks)

**Documentation:**
- Complete README with architecture overview
- Interface examples and usage patterns
- Component breakdown and file structure
- Installation and testing instructions
- API stability policy (`API_STABILITY.md`)

### Design Principles

- **Deterministic**: Same input → same output (no randomness in decision logic)
- **Offline-capable**: No network dependencies for evaluation or verification
- **Stateless**: Engine has no internal state (except ledger append operations)
- **Minimal dependencies**: Only `cryptography` library required

### Scope

**In Scope:**
- Pre-execution risk evaluation
- Cryptographic proof issuance (ED25519)
- Immutable ledger (hash chain)
- Offline verification

**Out of Scope:**
- UI/UX layers
- Transport adapters (Telegram, HTTP, etc.)
- Multi-tenant support
- SaaS hosting infrastructure
- LLM-based risk scoring (reserved for v0.2+)

### Technical Details

- **Algorithm**: ED25519 (elliptic curve digital signatures)
- **Hash function**: SHA-256 (for ledger chain)
- **File format**: NDJSON (newline-delimited JSON)
- **Python version**: 3.10+
- **Total source files**: 7 modules
- **Total test files**: 6 test suites
- **Lines of code**: ~725 (source + tests)

### Known Limitations

- Risk scoring is rule-based only (no ML/LLM fusion)
- No `HOLD` state implementation (reserved for v0.3)
- No enforcement gate integration (reserved for v0.4)
- Ledger is file-based (no database backend)
- Single-key signature (no multi-sig support)

---

## [Unreleased]

### Planned for v0.2.0
- Risk Fusion: Rule-based + LLM hybrid scoring
- Configurable risk thresholds per action type
- Enhanced ledger query API

### Planned for v0.3.0
- `HOLD` decision state
- Human approval flow integration
- Time-bounded decision expiration

### Planned for v0.4.0
- Enforcement gate integration
- Pre-commit hook example
- CI/CD pipeline integration guide

---

## Version History

- **v0.1.0** (2026-02-22): Initial release - Core engine with risk, crypto, and ledger
