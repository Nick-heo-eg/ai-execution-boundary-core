"""
Risk scoring engine for shell command evaluation.

This module evaluates shell commands and assigns risk scores
based on keyword patterns and command characteristics.
"""

import re
from typing import Tuple


def calculate_risk_score(command: str) -> Tuple[int, str]:
    """
    Evaluate risk score for a shell command.

    Risk levels:
    - 0-20: Low risk (read-only operations)
    - 21-60: Medium risk (modifications)
    - 61-80: High risk (destructive operations)
    - 81-100: Critical risk (system-level destruction)

    Args:
        command: Shell command string to evaluate

    Returns:
        Tuple of (risk_score, reason)
        - risk_score: Integer 0-100
        - reason: Human-readable explanation
    """
    cmd_lower = command.lower()

    # CRITICAL: System destruction potential
    if re.search(r'rm\s+-rf\s+/', cmd_lower):
        return 95, "Root path recursive deletion attempt"

    if 'rm -rf' in cmd_lower:
        return 90, "Recursive force deletion command"

    if 'delete' in cmd_lower and any(kw in cmd_lower for kw in ['system', 'all', 'database']):
        return 85, "System data deletion risk"

    # HIGH: Data loss potential
    if cmd_lower.startswith('rm '):
        return 60, "File deletion command"

    if any(kw in cmd_lower for kw in ['drop table', 'truncate']):
        return 70, "Database modification detected"

    # LOW: Read-only operations
    if cmd_lower.startswith(('ls', 'cat', 'echo', 'pwd')):
        return 10, "Read-only command"

    if cmd_lower.startswith(('grep', 'find', 'head')):
        return 15, "Search command"

    # DEFAULT: Unknown command
    return 40, "General command"
