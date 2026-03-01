"""
Severity Gate — Risk-adaptive execution control layer.

Connects severity scoring to the execution boundary state machine.

Architecture:
    ExecutionIntent
        ↓
    SeverityGate.evaluate(intent, system_severity)
        ↓ computes effective_threshold from severity
        ↓ determines state: ACTIVE | OBSERVE | COOLDOWN
        ↓
    enforce_boundary(intent, engine=adapted_engine)
        ↓
    BoundaryRecord (ALLOW) or Exception (DENY/HOLD)

Severity input:
    System severity score [0.0–1.0] from any source:
    - Portfolio risk engine (mdd + vol_spike + concentration)
    - Infrastructure error rate + latency spike
    - CI/CD test failure rate + deployment frequency
    - Any domain that produces a continuous risk signal

State machine:
    ACTIVE   : severity < SEV_OBSERVE        → normal gate (threshold=80)
    OBSERVE  : SEV_OBSERVE ≤ sev < SEV_ENTER → tightened (threshold=60)
    COOLDOWN : sev ≥ SEV_ENTER               → locked down (threshold=30)

Hysteresis (COOLDOWN ↔ ACTIVE):
    Enter COOLDOWN : sev ≥ SEV_ENTER (0.40)
    Exit  COOLDOWN : sev <  SEV_EXIT  (0.28)
    Between 0.28–0.40: previous state maintained

Usage:
    from execution_boundary.severity_gate import SeverityGate, SystemSeverity

    gate = SeverityGate()

    sev = SystemSeverity(score=0.45, source="portfolio_risk", raw={...})
    result = gate.evaluate(intent, engine=engine, system_severity=sev)
    # result.state == "COOLDOWN"
    # result.effective_threshold == 30
    # result.record == BoundaryRecord (if ALLOW)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .engine import ExecutionBoundaryEngine
from .enforce import enforce_boundary
from .models import (
    BoundaryRecord,
    ExecutionIntent,
    ExecutionDeniedError,
    ExecutionHeldError,
    ExecutionExpiredError,
)

# ── Hysteresis thresholds (aligned with execution-gate severity.py) ───────────

SEV_ENTER   = 0.40   # COOLDOWN 진입
SEV_EXIT    = 0.28   # COOLDOWN 해제
SEV_OBSERVE = 0.20   # OBSERVE 진입

# ── Effective halt_threshold per state ────────────────────────────────────────
# Lower threshold = tighter gate = more actions blocked

THRESHOLD_ACTIVE   = 80   # Default: risk ≥ 80 → DENY
THRESHOLD_OBSERVE  = 60   # OBSERVE: risk ≥ 60 → DENY
THRESHOLD_COOLDOWN = 30   # COOLDOWN: risk ≥ 30 → DENY (almost all blocked)

STATE_LOG_PATH = Path(__file__).parent.parent.parent / "severity_state.json"


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class SystemSeverity:
    """
    Severity signal from any domain.

    score:  float [0.0–1.0]
    source: identifier of the scoring system
    raw:    original metrics for audit trail
    """
    score:  float
    source: str = "unknown"
    raw:    Dict[str, Any] = field(default_factory=dict)


@dataclass
class SeverityGateResult:
    """
    Result of SeverityGate.evaluate().

    state:               "ACTIVE" | "OBSERVE" | "COOLDOWN"
    prev_state:          previous state (for state_change detection)
    state_changed:       True if state transitioned
    effective_threshold: halt_threshold used for this evaluation
    severity_score:      input severity score
    record:              BoundaryRecord if ALLOW, None if exception path
    denied:              True if ExecutionDeniedError raised
    held:                True if ExecutionHeldError raised
    error:               exception if denied/held, else None
    ts:                  ISO-8601 UTC
    """
    state:               str
    prev_state:          str
    state_changed:       bool
    effective_threshold: int
    severity_score:      float
    record:              Optional[BoundaryRecord]
    denied:              bool
    held:                bool
    error:               Optional[Exception]
    ts:                  str


# ── Gate ──────────────────────────────────────────────────────────────────────

class SeverityGate:
    """
    Risk-adaptive execution gate.

    Wraps enforce_boundary() with severity-driven threshold adjustment
    and 3-state hysteresis machine.
    """

    def __init__(self, state_log: Path = STATE_LOG_PATH) -> None:
        self._state_log = state_log
        self._prev_state: str = self._load_state()

    def evaluate(
        self,
        intent:          ExecutionIntent,
        engine:          ExecutionBoundaryEngine,
        system_severity: Optional[SystemSeverity] = None,
        policy:          Any = None,
        hold_deadline_seconds: int = 300,
    ) -> SeverityGateResult:
        """
        Evaluate execution intent against current severity state.

        Args:
            intent:               The execution request.
            engine:               Base ExecutionBoundaryEngine instance.
            system_severity:      Current system risk score. None = ACTIVE.
            policy:               Policy snapshot for policy_hash.
            hold_deadline_seconds: HOLD window duration.

        Returns:
            SeverityGateResult — always returns (never re-raises).
            Check .denied / .held / .error for non-ALLOW outcomes.
        """
        ts    = datetime.now(timezone.utc).isoformat()
        score = system_severity.score if system_severity else 0.0

        # ── 1. Determine state (with hysteresis) ──────────────────────────────
        state     = self._apply_hysteresis(score, self._prev_state)
        threshold = self._threshold(state)

        # ── 2. Create severity-adapted engine (threshold only) ─────────────────
        adapted = ExecutionBoundaryEngine(
            halt_threshold = threshold,
            key_file       = engine.key_manager.key_file if hasattr(engine, 'key_manager') else None,
            ledger_file    = engine.ledger.ledger_file   if hasattr(engine, 'ledger')      else None,
        )

        # ── 3. Enforce boundary ───────────────────────────────────────────────
        state_changed = (state != self._prev_state)
        record: Optional[BoundaryRecord] = None
        denied = held = False
        error: Optional[Exception] = None

        try:
            record = enforce_boundary(
                intent,
                engine                = adapted,
                policy                = policy,
                hold_deadline_seconds = hold_deadline_seconds,
                _severity_state       = state,
                _severity_score       = score,
                _severity_threshold   = threshold,
            )
        except ExecutionDeniedError as e:
            denied, error = True, e
        except ExecutionHeldError as e:
            held, error = True, e
        except ExecutionExpiredError as e:
            denied, error = True, e

        # ── 4. Persist state + audit ──────────────────────────────────────────
        self._save_state(state, score, system_severity, ts)
        prev = self._prev_state
        self._prev_state = state

        return SeverityGateResult(
            state               = state,
            prev_state          = prev,
            state_changed       = state_changed,
            effective_threshold = threshold,
            severity_score      = round(score, 4),
            record              = record,
            denied              = denied,
            held                = held,
            error               = error,
            ts                  = ts,
        )

    # ── State machine ─────────────────────────────────────────────────────────

    @staticmethod
    def _apply_hysteresis(score: float, prev_state: str) -> str:
        """
        3-state machine with hysteresis on COOLDOWN transitions.

        OBSERVE/ACTIVE transitions have no hysteresis (low-risk region).
        """
        if prev_state == "COOLDOWN":
            if score < SEV_EXIT:
                # Severity dropped below exit threshold → leave COOLDOWN
                if score >= SEV_OBSERVE:
                    return "OBSERVE"
                return "ACTIVE"
            return "COOLDOWN"   # hysteresis hold

        # Not in COOLDOWN
        if score >= SEV_ENTER:
            return "COOLDOWN"
        if score >= SEV_OBSERVE:
            return "OBSERVE"
        return "ACTIVE"

    @staticmethod
    def _threshold(state: str) -> int:
        return {
            "ACTIVE":   THRESHOLD_ACTIVE,
            "OBSERVE":  THRESHOLD_OBSERVE,
            "COOLDOWN": THRESHOLD_COOLDOWN,
        }.get(state, THRESHOLD_ACTIVE)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_state(self) -> str:
        if not self._state_log.exists():
            return "ACTIVE"
        try:
            d = json.loads(self._state_log.read_text(encoding="utf-8"))
            return d.get("state", "ACTIVE")
        except (json.JSONDecodeError, OSError):
            return "ACTIVE"

    def _save_state(
        self,
        state:    str,
        score:    float,
        sev:      Optional[SystemSeverity],
        ts:       str,
    ) -> None:
        self._state_log.parent.mkdir(parents=True, exist_ok=True)
        self._state_log.write_text(
            json.dumps({
                "state":          state,
                "prev_state":     self._prev_state,
                "state_changed":  state != self._prev_state,
                "severity_score": round(score, 4),
                "severity_source": sev.source if sev else "none",
                "ts":             ts,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
