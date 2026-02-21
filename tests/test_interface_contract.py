"""
Interface contract tests.

These tests verify that the ExecutionBoundary interface exists
and has the required methods. Implementation tests come later.
"""

from execution_boundary.interface import ExecutionBoundary


def test_interface_methods_exist():
    """Verify the core interface contract exists."""
    engine = ExecutionBoundary()

    assert hasattr(engine, "evaluate")
    assert hasattr(engine, "issue_proof")
    assert hasattr(engine, "verify")


def test_interface_methods_raise_not_implemented():
    """Base interface should raise NotImplementedError."""
    from execution_boundary.models import ExecutionIntent, Decision
    from datetime import datetime

    engine = ExecutionBoundary()

    intent = ExecutionIntent(
        actor="test",
        action="test",
        payload="test",
        timestamp=datetime.now()
    )

    try:
        engine.evaluate(intent)
        assert False, "Should raise NotImplementedError"
    except NotImplementedError:
        pass
