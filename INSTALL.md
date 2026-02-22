# Installation Guide

Installation instructions for AI Execution Boundary Core.

**Version:** 0.1.0
**Python:** 3.10+
**Status:** Private repository (manual installation)

---

## Prerequisites

- Python 3.10 or higher
- pip package manager
- Git

---

## Method 1: Local Development (Recommended)

For development and testing:

```bash
# Clone repository
git clone https://github.com/Nick-heo-eg/ai-execution-boundary-core.git
cd ai-execution-boundary-core

# Install dependencies
pip install cryptography

# Verify installation by running tests
PYTHONPATH=src pytest tests/ -v
# → 39 passed in 0.22s
```

**Usage:**
```python
# In your project
import sys
sys.path.insert(0, '/path/to/ai-execution-boundary-core/src')

from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent
```

---

## Method 2: Editable Install

For integration with other projects:

```bash
# Clone repository
git clone https://github.com/Nick-heo-eg/ai-execution-boundary-core.git
cd ai-execution-boundary-core

# Install in editable mode
pip install -e .

# Verify
python -c "from execution_boundary import ExecutionBoundaryEngine; print('✅ Installed')"
```

**Usage:**
```python
# No sys.path modification needed
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent
```

---

## Method 3: Direct Install from GitHub

Install directly into your Python environment:

```bash
# Install from GitHub (requires authentication for private repos)
pip install git+https://github.com/Nick-heo-eg/ai-execution-boundary-core.git@v0.1.0

# Or install from local clone
pip install /path/to/ai-execution-boundary-core
```

**Usage:**
```python
from execution_boundary import ExecutionBoundaryEngine, ExecutionIntent
```

---

## Method 4: Integration with Existing Project

For projects like the Telegram demo:

```bash
# Project structure:
# /home/user/projects/
#   ├── ai-execution-boundary-core/  (this repo)
#   └── my-ai-project/                (your project)

# From your project
cd my-ai-project

# Install core as dependency
pip install -e ../ai-execution-boundary-core
```

**In your `requirements.txt`:**
```txt
# Option 1: Editable install (development)
-e ../ai-execution-boundary-core

# Option 2: Direct GitHub install (if public in future)
# execution-boundary @ git+https://github.com/Nick-heo-eg/ai-execution-boundary-core.git@v0.1.0

# Option 3: PyPI install (when published)
# execution-boundary==0.1.0
```

---

## Verification

After installation, verify it works:

```python
from execution_boundary import (
    ExecutionBoundaryEngine,
    ExecutionIntent,
    Decision,
    Proof
)

# Create engine
engine = ExecutionBoundaryEngine()
print(f"✅ Engine initialized: {engine}")

# Test evaluation
from datetime import datetime, timezone

intent = ExecutionIntent(
    actor="test#user",
    action="shell.exec",
    payload="ls -la",
    timestamp=datetime.now(timezone.utc)
)

decision = engine.evaluate(intent)
print(f"✅ Evaluation works: {decision.decision} (risk: {decision.risk_score})")

# Test proof issuance
proof = engine.issue_proof(decision)
print(f"✅ Proof issuance works: {proof.signature[:16]}...")

# Test verification
result = engine.verify(proof)
print(f"✅ Verification works: {result.valid}")
```

**Expected output:**
```
✅ Engine initialized: <ExecutionBoundaryEngine object>
✅ Evaluation works: ALLOW (risk: 15)
✅ Proof issuance works: 3a7f8c2d1e9b...
✅ Verification works: True
```

---

## Dependencies

### Required

- **cryptography** (>= 42.0.0) — ED25519 digital signatures

### Optional (Development)

- **pytest** (>= 7.0.0) — Testing framework
- **pytest-cov** (>= 4.0.0) — Code coverage

Install development dependencies:
```bash
pip install -e ".[dev]"
```

---

## File Artifacts

After first use, the engine creates:

```
.private_key.pem          # ED25519 private key (auto-generated)
judgment_ledger.ndjson    # Append-only decision ledger
```

**Important:**
- `.private_key.pem` is needed to verify proofs — **back it up securely**
- `judgment_ledger.ndjson` is the audit trail — **do not modify manually**
- Both files are in `.gitignore` — **not committed to version control**

---

## Troubleshooting

### Import Error: No module named 'execution_boundary'

**Solution:**
```bash
# Verify installation
pip list | grep execution-boundary

# If not found, install again
pip install -e /path/to/ai-execution-boundary-core

# Or use PYTHONPATH
export PYTHONPATH=/path/to/ai-execution-boundary-core/src:$PYTHONPATH
```

---

### Import Error: No module named 'cryptography'

**Solution:**
```bash
pip install cryptography
```

---

### Permission Error: Cannot write to ledger file

**Solution:**
```bash
# Check file permissions
ls -la judgment_ledger.ndjson

# Fix permissions
chmod 644 judgment_ledger.ndjson

# Or specify custom ledger path
engine = ExecutionBoundaryEngine(ledger_file="/tmp/my_ledger.ndjson")
```

---

### Tests Failing

**Solution:**
```bash
# Ensure PYTHONPATH is set
cd /path/to/ai-execution-boundary-core
PYTHONPATH=src pytest tests/ -v

# Or install in editable mode first
pip install -e .
pytest tests/ -v
```

---

## Uninstallation

```bash
# If installed with pip
pip uninstall execution-boundary

# Remove generated files (optional)
rm .private_key.pem judgment_ledger.ndjson
```

---

## Next Steps

- See [README.md](README.md) for usage examples
- See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for framework integrations
- See [API_STABILITY.md](API_STABILITY.md) for versioning guarantees

---

**Last Updated:** 2026-02-22
**Version:** 0.1.0
