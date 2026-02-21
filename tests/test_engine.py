"""
Unit tests for execution boundary engine
"""

import pytest
from datetime import datetime
from execution_boundary import (
    ExecutionBoundaryEngine,
    ExecutionIntent,
    DecisionType
)


class TestExecutionBoundaryEngine:
    """Test core engine decision logic"""

    def test_engine_initialization(self):
        """Engine should initialize with default threshold"""
        engine = ExecutionBoundaryEngine()
        assert engine.halt_threshold == 80

    def test_engine_custom_threshold(self):
        """Engine should accept custom threshold"""
        engine = ExecutionBoundaryEngine(halt_threshold=70)
        assert engine.halt_threshold == 70

    def test_allow_decision_low_risk(self):
        """Low risk commands should be ALLOWED"""
        engine = ExecutionBoundaryEngine()
        intent = ExecutionIntent(
            actor="test_user",
            action="shell.exec",
            payload="ls -la",
            timestamp=datetime.now()
        )

        decision = engine.evaluate(intent)

        assert decision.decision == "ALLOW"
        assert decision.risk_score == 10
        assert "Read-only" in decision.reason

    def test_halt_decision_critical_risk(self):
        """Critical risk commands should be HALTED"""
        engine = ExecutionBoundaryEngine()
        intent = ExecutionIntent(
            actor="test_user",
            action="shell.exec",
            payload="rm -rf /",
            timestamp=datetime.now()
        )

        decision = engine.evaluate(intent)

        assert decision.decision == "HALT"
        assert decision.risk_score == 95
        assert "Root path" in decision.reason

    def test_allow_decision_below_threshold(self):
        """Commands below threshold should be ALLOWED"""
        engine = ExecutionBoundaryEngine(halt_threshold=80)
        intent = ExecutionIntent(
            actor="test_user",
            action="shell.exec",
            payload="rm file.txt",  # Risk score: 60
            timestamp=datetime.now()
        )

        decision = engine.evaluate(intent)

        assert decision.decision == "ALLOW"
        assert decision.risk_score == 60

    def test_halt_decision_at_threshold(self):
        """Commands at threshold should be HALTED"""
        engine = ExecutionBoundaryEngine(halt_threshold=70)
        intent = ExecutionIntent(
            actor="test_user",
            action="shell.exec",
            payload="drop table users",  # Risk score: 70
            timestamp=datetime.now()
        )

        decision = engine.evaluate(intent)

        assert decision.decision == "HALT"
        assert decision.risk_score == 70

    def test_decision_has_timestamp(self):
        """Decisions should include timestamp"""
        engine = ExecutionBoundaryEngine()
        intent = ExecutionIntent(
            actor="test_user",
            action="shell.exec",
            payload="echo test",
            timestamp=datetime.now()
        )

        decision = engine.evaluate(intent)

        assert decision.timestamp is not None
        assert isinstance(decision.timestamp, datetime)
