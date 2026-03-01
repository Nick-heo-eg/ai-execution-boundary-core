"""
LangChain adapter for agent-execution-guard.

Wraps any callable tool with an ExecutionGuard evaluation.
The guard runs before the tool executes — DENY blocks execution entirely.

Install:
    pip install agent-execution-guard[langchain]

Usage:
    from agent_execution_guard.langchain_adapter import GuardedTool

    def delete_file(path: str) -> str:
        return f"Deleted {path}"

    guarded = GuardedTool(delete_file, actor="agent.ops")

    guarded("test.txt")       # low risk → executes
    guarded("rm -rf /")       # critical risk → raises GuardDeniedError
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from execution_boundary.engine import ExecutionBoundaryEngine
from execution_boundary.models import ExecutionIntent
from execution_boundary.enforce import enforce_boundary


class GuardedTool:
    """
    Wrap a callable with an execution guard.

    The guard evaluates the tool call as an ExecutionIntent before
    allowing execution. High-risk calls raise GuardDeniedError.

    Args:
        tool:      Any callable to wrap.
        actor:     Identity of the agent invoking the tool.
        engine:    ExecutionBoundaryEngine instance. Default created if None.
        policy:    Policy dict for identity checks. None = no identity check.
    """

    def __init__(
        self,
        tool: Callable[..., Any],
        *,
        actor: str = "agent",
        engine: Optional[ExecutionBoundaryEngine] = None,
        policy: Any = None,
    ) -> None:
        self.tool   = tool
        self.actor  = actor
        self.engine = engine or ExecutionBoundaryEngine()
        self.policy = policy

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Evaluate intent, then call the tool if ALLOW.

        Raises:
            GuardDeniedError — if risk exceeds threshold or policy denies.
        """
        payload = _build_payload(self.tool.__name__, args, kwargs)

        intent = ExecutionIntent(
            actor     = self.actor,
            action    = self.tool.__name__,
            payload   = payload,
            timestamp = datetime.now(timezone.utc),
        )

        # Raises ExecutionDeniedError / ExecutionHeldError on non-ALLOW
        enforce_boundary(intent, engine=self.engine, policy=self.policy)

        return self.tool(*args, **kwargs)

    def __repr__(self) -> str:
        return f"GuardedTool({self.tool.__name__!r}, actor={self.actor!r})"


# ── Helper ────────────────────────────────────────────────────────────────────

def _build_payload(name: str, args: tuple, kwargs: dict) -> str:
    """Build a readable payload string from tool name + args."""
    parts = [name]
    if args:
        parts.append(" ".join(str(a) for a in args))
    if kwargs:
        parts.append(" ".join(f"{k}={v}" for k, v in kwargs.items()))
    return " ".join(parts)
