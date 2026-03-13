from agent_execution_guard.langchain_adapter import GuardedTool
from agent_execution_guard import GuardDeniedError

def shell_exec(command: str) -> str:
    return f"executed: {command}"

guarded = GuardedTool(shell_exec, actor="langchain#agent")

# low risk → executes
result = guarded("ls -la")
print(f"[1] low risk: {result}")

# high risk → DENY
try:
    guarded("rm -rf /")
except Exception as e:
    print(f"[2] high risk DENY: {type(e).__name__}")

print("\nLangChain adapter OK.")
