# API Stability Policy

**Version:** 0.1.0
**Status:** Interface Frozen
**Effective:** 2026-02-22

---

## Public API Surface

The following interfaces are **stable** and will follow semantic versioning:

### Core Engine

```python
from execution_boundary import ExecutionBoundaryEngine

engine = ExecutionBoundaryEngine(
    halt_threshold: int = 80,
    key_file: Optional[str] = None,
    ledger_file: Optional[str] = None
)

# Stable methods
decision = engine.evaluate(intent: ExecutionIntent) -> Decision
proof = engine.issue_proof(decision: Decision) -> Proof
result = engine.verify(proof: Proof) -> VerificationResult
```

### Data Models

```python
from execution_boundary import (
    ExecutionIntent,
    Decision,
    Proof,
    VerificationResult,
    DecisionType
)

# All fields in these dataclasses are stable
```

### Public Exports

```python
__all__ = [
    "ExecutionBoundary",           # Abstract interface
    "ExecutionBoundaryEngine",     # Concrete implementation
    "ExecutionIntent",             # Input model
    "Decision",                    # Evaluation result
    "Proof",                       # Cryptographic proof
    "VerificationResult",          # Verification result
    "DecisionType",                # Literal["ALLOW", "HALT", "HOLD"]
    "calculate_risk_score",        # Utility function
]
```

---

## Stability Guarantees

### v0.x (Current)

- **Minor version bumps** (0.1 → 0.2): May add new fields, methods, or optional parameters
- **Patch version bumps** (0.1.0 → 0.1.1): Bug fixes only, no interface changes
- **Breaking changes**: Will increment major version (0.x → 1.0)

### v1.x (Future)

- **Major version bumps** (1.x → 2.0): May introduce breaking changes
- **Minor version bumps** (1.0 → 1.1): Backward-compatible additions only
- **Patch version bumps** (1.0.0 → 1.0.1): Bug fixes only

---

## Internal Implementation

The following are **internal** and may change without notice:

- `execution_boundary.crypto` (KeyManager, signing internals)
- `execution_boundary.ledger` (Ledger internals, file format details)
- `execution_boundary.risk` (Risk scoring rules)
- Any module or class prefixed with `_`

**Do not import these directly.** Use the public API surface only.

---

## Deprecation Policy

When we need to deprecate an API:

1. **Announcement**: Deprecated in version X.Y with warning message
2. **Grace period**: Minimum 2 minor versions (e.g., deprecated in 0.2, removed in 0.4)
3. **Removal**: Breaking change in next major version

Example:
```python
# v0.2: Deprecation warning added
warnings.warn("old_method() is deprecated, use new_method()", DeprecationWarning)

# v0.4: Still works, warning remains
# v1.0: Removed entirely
```

---

## Breaking Change Policy

**Before v1.0:**
- Interface changes are possible but will be clearly documented
- Major architectural changes will increment minor version (0.1 → 0.2)

**After v1.0:**
- Breaking changes only in major version bumps (1.x → 2.0)
- All changes follow strict semantic versioning

---

## Future-Openable Design

This core is currently **private** but designed to be **publicly releasable** in the future.

**Current strategy:**
- Private repository (proprietary use)
- Public API designed for stability
- Internal implementation may change

**Future options:**
- Open source release (when strategically appropriate)
- Dual licensing (Core open, Extensions proprietary)
- Enterprise licensing (SaaS uses private core)

**Design principles:**
- Public API is minimal and clean
- Internal modules are encapsulated
- No leakage of proprietary logic into public interface

---

## Version Compatibility Matrix

| Core Version | Python Version | Cryptography Lib | Ledger Format |
|--------------|----------------|------------------|---------------|
| 0.1.x        | 3.10+          | cryptography     | NDJSON v1     |
| 0.2.x        | 3.10+          | cryptography     | NDJSON v1     |
| 1.0.x        | 3.11+          | TBD              | TBD           |

---

## Contact

For questions about API stability or breaking changes:
- Open an issue in the repository
- Contact: maintainers via GitHub

---

**Last Updated:** 2026-02-22
**Next Review:** v0.2.0 release
