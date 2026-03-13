import yaml
from datetime import datetime, timezone
from agent_execution_guard import ExecutionGuard, Intent, GuardDeniedError

policy = yaml.safe_load("""
defaults:
  unknown_agent: DENY
  unknown_action: DENY
identity:
  agents:
    - agent_id: "agent.finance"
      allowed_actions:
        - action: "wire_transfer"
""")

guard = ExecutionGuard()

# known agent + known action → ALLOW
intent_ok = Intent(
    actor="agent.finance",
    action="wire_transfer",
    payload="wire_transfer amount=50000 to=external",
    timestamp=datetime.now(timezone.utc),
)
result = guard.evaluate(intent_ok, policy=policy)
print(f"[1] known agent + known action: ALLOW (risk={result.risk_score})")

# unknown agent → DENY
intent_bad_agent = Intent(
    actor="unknown.agent",
    action="wire_transfer",
    payload="wire_transfer amount=50000 to=external",
    timestamp=datetime.now(timezone.utc),
)
try:
    guard.evaluate(intent_bad_agent, policy=policy)
except GuardDeniedError as e:
    print(f"[2] unknown agent: DENY reason={e.reason}")

# known agent + unknown action → DENY
intent_bad_action = Intent(
    actor="agent.finance",
    action="delete_all",
    payload="delete_all",
    timestamp=datetime.now(timezone.utc),
)
try:
    guard.evaluate(intent_bad_action, policy=policy)
except GuardDeniedError as e:
    print(f"[3] unknown action: DENY reason={e.reason}")

# policy=None → DENY (fail-closed)
try:
    guard.evaluate(intent_ok, policy=None)
except GuardDeniedError as e:
    print(f"[4] policy=None: DENY reason={e.reason}")

print("\nAll policy checks passed.")
