"""
Tests for LangChain adapter (GuardedTool).
"""
import pytest

from agent_execution_guard.langchain_adapter import GuardedTool
from execution_boundary.engine import ExecutionBoundaryEngine
from execution_boundary.models import ExecutionDeniedError


def safe_tool(path: str) -> str:
    return f"read {path}"


def _guarded(threshold: int = 80) -> GuardedTool:
    engine = ExecutionBoundaryEngine(halt_threshold=threshold)
    return GuardedTool(safe_tool, actor="agent.test", engine=engine)


def test_allow_low_risk():
    """Low-risk call passes through and returns tool result."""
    result = _guarded(threshold=80)("README.md")
    assert result == "read README.md"


def test_deny_high_risk():
    """High-risk payload is blocked before tool executes."""
    with pytest.raises(ExecutionDeniedError):
        _guarded(threshold=39)("rm -rf /")


def test_deny_critical_command():
    """rm -rf / scores critical → always blocked at default threshold=80."""
    with pytest.raises(ExecutionDeniedError):
        _guarded(threshold=80)("rm -rf /")


def test_tool_not_called_on_deny():
    """Tool function must not execute when denied."""
    called = []

    def tracked_tool(cmd: str) -> str:
        called.append(cmd)
        return "executed"

    engine = ExecutionBoundaryEngine(halt_threshold=39)
    guarded = GuardedTool(tracked_tool, actor="agent.test", engine=engine)

    with pytest.raises(ExecutionDeniedError):
        guarded("rm -rf /")

    assert called == [], "tool must not be called on DENY"


def test_repr():
    assert "safe_tool" in repr(_guarded())
    assert "agent.test" in repr(_guarded())
