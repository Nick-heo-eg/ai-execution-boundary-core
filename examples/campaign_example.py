"""
Example 2 — Campaign AI + Severity: DENY via COOLDOWN

A campaign AI attempts aggressive targeting.
System severity is elevated (0.60) → COOLDOWN state.
In COOLDOWN, the threshold drops from 80 to 30.
The action scores 40 → DENY.

Same action at normal severity (0.10, ACTIVE state):
threshold=80, risk=40 → ALLOW.

The severity state is what causes the DENY — not a hard block on the action.

Run:
    python examples/campaign_example.py
"""
from datetime import datetime, timezone
from agent_execution_guard import (
    ExecutionGuard,
    Intent,
    SystemSeverity,
    GuardDeniedError,
)

guard = ExecutionGuard()

intent = Intent(
    actor="campaign_ai",
    action="aggressive_targeting",
    payload="launch targeted ad campaign segment=undecided_voters",
    timestamp=datetime.now(timezone.utc),
)

print("=== Scenario: Elevated severity (COOLDOWN) ===")
print(f"  actor:    {intent.actor}")
print(f"  action:   {intent.action}")
print()

# Score=0.60 → COOLDOWN → threshold=30 → risk(40) > 30 → DENY
high_severity = SystemSeverity(score=0.60, source="geopolitical_risk_model")

try:
    result = guard.evaluate(intent, severity=high_severity)
    print(f"ALLOW — boundary_id: {result.boundary_id}")

except GuardDeniedError as e:
    print(f"DENY (COOLDOWN state — threshold=30, risk=40)")
    print(f"  boundary_id: {e.boundary_id}")
    print(f"  reason:      {e.reason}")
    print()

print("=== Scenario: Normal severity (ACTIVE) ===")
print(f"  Same action, same actor")
print()

# Score=0.10 → ACTIVE → threshold=80 → risk(40) < 80 → ALLOW
low_severity = SystemSeverity(score=0.10, source="baseline")

try:
    result = guard.evaluate(intent, severity=low_severity)
    print(f"ALLOW (ACTIVE state — threshold=80, risk=40)")
    print(f"  boundary_id: {result.boundary_id}")

except GuardDeniedError as e:
    print(f"DENY — {e.reason}")

print()
print("Same action. Different severity state. Different outcome.")
print("The boundary adapts. The agent does not decide.")
