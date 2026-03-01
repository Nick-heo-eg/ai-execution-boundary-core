"""
Example 1 — Finance: DENY

An AI agent attempts a wire transfer.
The guard evaluates risk and issues a signed denial.

Run:
    python examples/finance_example.py
"""
from datetime import datetime, timezone
from agent_execution_guard import ExecutionGuard, Intent, GuardDeniedError

# halt_threshold=39: wire_transfer scores 40 → DENY
# (default is 80 — adjust per your risk policy)
guard = ExecutionGuard(halt_threshold=39)

intent = Intent(
    actor="agent.finance",
    action="wire_transfer",
    payload="wire_transfer amount=50000 to=external",
    timestamp=datetime.now(timezone.utc),
)

print("Evaluating intent...")
print(f"  actor:   {intent.actor}")
print(f"  action:  {intent.action}")
print(f"  payload: {intent.payload}")
print()

try:
    result = guard.evaluate(intent)
    print(f"ALLOW — boundary_id: {result.boundary_id}")
    print(f"  risk_score: {result.risk_score}")

except GuardDeniedError as e:
    print(f"DENY")
    print(f"  reason:      {e.reason}")
    print(f"  boundary_id: {e.boundary_id}")
    print(f"  risk_score:  {e.risk_score}")
    print()
    print("Signed negative proof issued.")
    print("The agent cannot retry past this boundary.")
