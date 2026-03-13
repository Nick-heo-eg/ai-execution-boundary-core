from datetime import datetime, timezone
from agent_execution_guard import ExecutionGuard, Intent, ALLOW_ALL, GuardDeniedError, SystemSeverity

# Quickstart
guard = ExecutionGuard()
intent = Intent(
    actor="agent.finance",
    action="wire_transfer",
    payload="wire_transfer amount=50000 to=external",
    timestamp=datetime.now(timezone.utc),
)
result = guard.evaluate(intent, policy=ALLOW_ALL)
print(f"[1] Quickstart: risk_score={result.risk_score}")  # 기대: 40

# Example 1 — DENY
guard2 = ExecutionGuard(halt_threshold=39)
try:
    guard2.evaluate(intent, policy=ALLOW_ALL)
except GuardDeniedError as e:
    print(f"[2] DENY: reason={e.reason}, boundary_id={e.boundary_id[:8]}...")

# Example 2 — Severity
guard3 = ExecutionGuard()
intent2 = Intent(
    actor="campaign_ai",
    action="aggressive_targeting",
    payload="launch targeted ad campaign segment=undecided_voters",
    timestamp=datetime.now(timezone.utc),
)
high = SystemSeverity(score=0.60, source="risk_model")
low  = SystemSeverity(score=0.10, source="baseline")
try:
    guard3.evaluate(intent2, severity=high, policy=ALLOW_ALL)
except GuardDeniedError:
    print("[3] DENY  (COOLDOWN — threshold=30)")
result2 = guard3.evaluate(intent2, severity=low, policy=ALLOW_ALL)
print("[4] ALLOW (ACTIVE  — threshold=80)")

print("\nAll checks passed.")
