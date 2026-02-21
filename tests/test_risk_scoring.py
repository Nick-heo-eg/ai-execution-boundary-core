"""
Unit tests for risk scoring engine
"""

import pytest
from execution_boundary.risk import calculate_risk_score


class TestRiskScoring:
    """Test risk scoring logic"""

    def test_critical_risk_rm_rf_root(self):
        """Root path deletion should have critical risk"""
        score, reason = calculate_risk_score("rm -rf /")
        assert score == 95
        assert "Root path" in reason

    def test_critical_risk_rm_rf_recursive(self):
        """Recursive force deletion should have critical risk"""
        score, reason = calculate_risk_score("rm -rf something")
        assert score == 90
        assert "Recursive" in reason

    def test_critical_risk_system_delete(self):
        """System data deletion should have high risk"""
        score, reason = calculate_risk_score("delete all system files")
        assert score == 85
        assert "System data" in reason

    def test_high_risk_rm(self):
        """Simple rm command should have medium-high risk"""
        score, reason = calculate_risk_score("rm file.txt")
        assert score == 60
        assert "deletion" in reason.lower()

    def test_high_risk_drop_table(self):
        """Database operations should have high risk"""
        score, reason = calculate_risk_score("drop table users")
        assert score == 70
        assert "Database" in reason

    def test_low_risk_ls(self):
        """Read-only ls command should have low risk"""
        score, reason = calculate_risk_score("ls -la")
        assert score == 10
        assert "Read-only" in reason

    def test_low_risk_cat(self):
        """Read-only cat command should have low risk"""
        score, reason = calculate_risk_score("cat /etc/passwd")
        assert score == 10

    def test_low_risk_grep(self):
        """Search command should have low risk"""
        score, reason = calculate_risk_score("grep pattern file.txt")
        assert score == 15
        assert "Search" in reason

    def test_default_risk(self):
        """Unknown commands should have default risk"""
        score, reason = calculate_risk_score("some_unknown_command")
        assert score == 40
        assert "General" in reason

    def test_case_insensitive(self):
        """Risk scoring should be case-insensitive"""
        score1, _ = calculate_risk_score("RM -RF /")
        score2, _ = calculate_risk_score("rm -rf /")
        assert score1 == score2 == 95
