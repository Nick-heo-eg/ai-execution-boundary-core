"""
tests/test_enforce.py — enforce_boundary() unified lifecycle tests

E1.  boundary_id 생성 — trace_id와 독립적인 UUID
E2.  decision_hash — canonical SHA-256, 동일 입력 deterministic
E3.  policy_hash   — policy snapshot SHA-256
E4.  ALLOW outcome — BoundaryRecord 반환, 예외 없음
E5.  DENY outcome  — ExecutionDeniedError 발생, ledger에 negative_proof=True
E6.  HOLD outcome  — ExecutionHeldError 발생, deadline_ts 포함
E7.  EXPIRED      — check_hold_expired() 과거 deadline → ExecutionExpiredError
E8.  HOLD pending  — check_hold_expired() 미래 deadline → ExecutionHeldError
E9.  negative proof — DENY/HOLD 모두 ledger에 append됨
E10. run_id 전파   — BoundaryRecord.run_id == intent.run_id
E11. enforce_boundary DENY → adapter.send() 절대 미호출 (control flow)
E12. OTel no-op    — opentelemetry 없어도 정상 작동
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

from execution_boundary import (
    ExecutionBoundaryEngine,
    ExecutionIntent,
    ExecutionDeniedError,
    ExecutionHeldError,
    ExecutionExpiredError,
    EnforcementOutcome,
    enforce_boundary,
    check_hold_expired,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine(tmp_path):
    return ExecutionBoundaryEngine(
        key_file    = str(tmp_path / "key.pem"),
        ledger_file = str(tmp_path / "ledger.ndjson"),
    )


def _intent(payload: str = "ls -la", run_id: str = "run-test-001") -> ExecutionIntent:
    return ExecutionIntent(
        actor     = "test_actor",
        action    = "shell.exec",
        payload   = payload,
        timestamp = datetime.now(timezone.utc),
        run_id    = run_id,
    )


# ── E1: boundary_id 생성 ──────────────────────────────────────────────────────

def test_E1_boundary_id_is_unique(engine):
    """enforce_boundary()는 매 호출마다 다른 boundary_id를 생성한다."""
    rec1 = enforce_boundary(_intent(), engine=engine)
    rec2 = enforce_boundary(_intent(), engine=engine)
    assert rec1.boundary_id != rec2.boundary_id
    assert len(rec1.boundary_id) == 36  # UUIDv4 형식


# ── E2: decision_hash deterministic ──────────────────────────────────────────

def test_E2_decision_hash_is_deterministic(engine):
    """동일한 boundary_id + 내용이면 decision_hash가 동일해야 한다."""
    from execution_boundary.models import Decision
    import hashlib, json
    d = Decision(
        decision   = "ALLOW",
        risk_score = 10,
        reason     = "Read-only command",
        timestamp  = datetime(2026, 2, 28, 0, 0, 0, tzinfo=timezone.utc),
        boundary_id = "fixed-id",
    )
    h1 = d.decision_hash
    # 같은 boundary_id로 다시 계산
    d2 = Decision(
        decision   = "ALLOW",
        risk_score = 10,
        reason     = "Read-only command",
        timestamp  = datetime(2026, 2, 28, 0, 0, 0, tzinfo=timezone.utc),
        boundary_id = "fixed-id",
    )
    assert h1 == d2.decision_hash


# ── E3: policy_hash ───────────────────────────────────────────────────────────

def test_E3_policy_hash_in_record(engine):
    """BoundaryRecord에 policy_hash가 포함된다."""
    policy = {"max_risk": 80, "version": "v1"}
    rec = enforce_boundary(_intent(), engine=engine, policy=policy)
    assert len(rec.policy_hash) == 64  # sha256 hex
    assert rec.policy_hash != "0" * 64


# ── E4: ALLOW ─────────────────────────────────────────────────────────────────

def test_E4_allow_returns_record(engine):
    """저위험 명령 → BoundaryRecord 반환, outcome=ALLOW"""
    rec = enforce_boundary(_intent("ls -la"), engine=engine)
    assert rec.outcome == EnforcementOutcome.ALLOW
    assert rec.negative_proof is False
    assert rec.boundary_id
    assert rec.proof_signature


# ── E5: DENY ──────────────────────────────────────────────────────────────────

def test_E5_deny_raises_execution_denied_error(engine):
    """고위험 명령 → ExecutionDeniedError 발생"""
    with pytest.raises(ExecutionDeniedError) as exc_info:
        enforce_boundary(_intent("rm -rf /"), engine=engine)
    err = exc_info.value
    assert err.risk_score >= 80
    assert err.boundary_id


def test_E5_deny_negative_proof_in_ledger(engine, tmp_path):
    """DENY 시 ledger에 negative_proof=True 항목이 append된다."""
    with pytest.raises(ExecutionDeniedError):
        enforce_boundary(_intent("rm -rf /"), engine=engine)
    entries = engine.ledger.read_all()
    assert len(entries) >= 1
    last = entries[-1]
    assert last["negative_proof"] is True
    assert last["decision"] == "HALT"


# ── E6: HOLD ──────────────────────────────────────────────────────────────────

def test_E6_hold_raises_execution_held_error():
    """HOLD decision → ExecutionHeldError with deadline_ts"""
    with tempfile.TemporaryDirectory() as tmpdir:
        from execution_boundary.engine import ExecutionBoundaryEngine as _Eng
        from execution_boundary.models import Decision
        from execution_boundary.enforce import enforce_boundary as _enf

        engine = _Eng(
            key_file    = os.path.join(tmpdir, "key.pem"),
            ledger_file = os.path.join(tmpdir, "ledger.ndjson"),
            halt_threshold = 100,  # nothing auto-halts
        )

        # Monkey-patch evaluate() to return HOLD
        original_evaluate = engine.evaluate
        def _hold_evaluate(intent):
            d = original_evaluate(intent)
            d.decision = "HOLD"
            d.negative_proof = True
            return d
        engine.evaluate = _hold_evaluate

        with pytest.raises(ExecutionHeldError) as exc_info:
            _enf(_intent("transfer_money"), engine=engine, hold_deadline_seconds=300)

        err = exc_info.value
        assert err.deadline_ts is not None
        assert err.boundary_id


# ── E7: EXPIRED ───────────────────────────────────────────────────────────────

def test_E7_expired_raises_execution_expired_error(engine):
    """과거 deadline_ts → check_hold_expired() → ExecutionExpiredError"""
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with pytest.raises(ExecutionExpiredError) as exc_info:
        check_hold_expired(
            boundary_id = "old-boundary-id",
            deadline_ts = past,
            engine      = engine,
            intent      = _intent(),
        )
    assert exc_info.value.deadline_ts == past


# ── E8: HOLD still pending ────────────────────────────────────────────────────

def test_E8_hold_pending_still_raises_held_error(engine):
    """미래 deadline_ts → check_hold_expired() → ExecutionHeldError (아직 유효)"""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    with pytest.raises(ExecutionHeldError):
        check_hold_expired(
            boundary_id = "pending-boundary-id",
            deadline_ts = future,
            engine      = engine,
            intent      = _intent(),
        )


# ── E9: negative proof ledger append ─────────────────────────────────────────

def test_E9_both_allow_and_deny_appear_in_ledger(engine):
    """ALLOW와 DENY 모두 ledger에 기록된다."""
    enforce_boundary(_intent("ls"), engine=engine)          # ALLOW
    with pytest.raises(ExecutionDeniedError):
        enforce_boundary(_intent("rm -rf /"), engine=engine)  # DENY

    entries = engine.ledger.read_all()
    assert len(entries) == 2
    outcomes = [e["decision"] for e in entries]
    assert "ALLOW" in outcomes
    assert "HALT"  in outcomes

    deny_entry = next(e for e in entries if e["decision"] == "HALT")
    assert deny_entry["negative_proof"] is True
    assert "boundary_id" in deny_entry


# ── E10: run_id propagation ───────────────────────────────────────────────────

def test_E10_run_id_propagated_to_record(engine):
    """intent.run_id가 BoundaryRecord.run_id로 전파된다."""
    rec = enforce_boundary(_intent(run_id="run-abc-123"), engine=engine)
    assert rec.run_id == "run-abc-123"


# ── E11: control flow — send never called after DENY ─────────────────────────

def test_E11_send_never_called_after_deny(engine):
    """
    DENY 예외 발생 시 adapter.send() 절대 미호출 (control flow 검증).

    실제 패턴: caller가 enforce_boundary() 이후에만 send()를 호출하도록 설계.
    ExecutionDeniedError가 발생하면 send()에 도달하는 코드가 실행되지 않는다.
    """
    send_called = []

    def fake_send(payload):
        send_called.append(payload)
        return {"ok": True}

    # caller 패턴 시뮬레이션
    denied = False
    try:
        enforce_boundary(_intent("rm -rf /"), engine=engine)
        # ALLOW 경로만 도달 — send 호출
        fake_send({"payload": "would_execute"})
    except ExecutionDeniedError:
        denied = True
        # DENY 경로 — send 절대 미호출

    assert denied is True
    assert send_called == []  # DENY 후 send가 한 번도 호출되지 않음


# ── E12: OTel no-op ──────────────────────────────────────────────────────────

def test_E12_works_without_otel(engine, monkeypatch):
    """opentelemetry가 없어도 enforce_boundary()가 정상 작동한다."""
    import execution_boundary.enforce as _mod
    monkeypatch.setattr(_mod, "_HAS_OTEL", False)

    rec = enforce_boundary(_intent("ls -la"), engine=engine)
    assert rec.outcome == EnforcementOutcome.ALLOW
    assert rec.boundary_id


# ── T1~T5: 2-hash 구조 검증 ───────────────────────────────────────────────────

from execution_boundary.models import Decision
from datetime import datetime, timezone as _tz

_TS = datetime(2026, 2, 28, 0, 0, 0, tzinfo=_tz.utc)


def _decision(boundary_id: str, policy_hash: str = "phash-001", reason: str = "Read-only command") -> Decision:
    return Decision(
        decision    = "ALLOW",
        risk_score  = 10,
        reason      = reason,
        timestamp   = _TS,
        boundary_id = boundary_id,
        policy_hash = policy_hash,
    )


def test_T1_fingerprint_invariant_to_boundary_id():
    """T1: boundary_id가 달라도 동일 content → decision_hash(fingerprint) 동일."""
    d1 = _decision("id-aaa")
    d2 = _decision("id-bbb")
    assert d1.decision_hash == d2.decision_hash
    # instance_hash는 달라야 함
    assert d1.decision_instance_hash != d2.decision_instance_hash


def test_T2_fingerprint_invariant_to_timestamp():
    """T2: timestamp가 달라도 동일 content → fingerprint 동일."""
    d1 = Decision(decision="ALLOW", risk_score=10, reason="Read-only command",
                  timestamp=datetime(2026, 1, 1, tzinfo=_tz.utc),
                  boundary_id="id-aaa", policy_hash="phash-001")
    d2 = Decision(decision="ALLOW", risk_score=10, reason="Read-only command",
                  timestamp=datetime(2026, 6, 1, tzinfo=_tz.utc),
                  boundary_id="id-aaa", policy_hash="phash-001")
    assert d1.decision_hash == d2.decision_hash


def test_T3_fingerprint_changes_on_payload_change():
    """T3: reason(action_digest 대리값)이 바뀌면 fingerprint도 바뀐다."""
    d1 = _decision("id-aaa", reason="Read-only command")
    d2 = _decision("id-aaa", reason="Root path recursive deletion attempt")
    assert d1.decision_hash != d2.decision_hash


def test_T4_fingerprint_changes_on_policy_change():
    """T4: policy_hash가 바뀌면 fingerprint도 바뀐다."""
    d1 = _decision("id-aaa", policy_hash="policy-v1-hash")
    d2 = _decision("id-aaa", policy_hash="policy-v2-hash")
    assert d1.decision_hash != d2.decision_hash


def test_T5_instance_hash_changes_on_boundary_id_or_timestamp():
    """T5: fingerprint 동일 + boundary_id/timestamp 다르면 instance_hash 다름."""
    d_base = _decision("id-aaa")

    d_diff_id = _decision("id-bbb")
    assert d_base.decision_hash == d_diff_id.decision_hash          # fingerprint 동일
    assert d_base.decision_instance_hash != d_diff_id.decision_instance_hash  # instance 다름

    d_diff_ts = Decision(decision="ALLOW", risk_score=10, reason="Read-only command",
                         timestamp=datetime(2025, 1, 1, tzinfo=_tz.utc),
                         boundary_id="id-aaa", policy_hash="phash-001")
    assert d_base.decision_hash == d_diff_ts.decision_hash          # fingerprint 동일
    assert d_base.decision_instance_hash != d_diff_ts.decision_instance_hash  # instance 다름
