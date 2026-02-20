"""
Tests for GuardRails configuration and error handling.
"""

import pytest

from shared.config import GuardRailsConfig
from shared.guardrails import (
    build_guardrails_config,
    is_guardrails_error,
    handle_guardrails_error,
    get_guardrails_intervention_message,
    GUARDRAILS_INTERVENTION_MESSAGE,
)


class TestBuildGuardrailsConfig:
    """Tests for build_guardrails_config function."""
    
    def test_returns_none_when_disabled(self):
        """Should return None when GuardRails is disabled."""
        config = GuardRailsConfig()
        result = build_guardrails_config(config)
        assert result is None
    
    def test_returns_config_when_enabled(self):
        """Should return config dict when GuardRails is enabled."""
        config = GuardRailsConfig(
            guardrail_id="gr-test123456",
            guardrail_version="1",
        )
        result = build_guardrails_config(config)
        
        assert result is not None
        assert result["guardrailIdentifier"] == "gr-test123456"
        assert result["guardrailVersion"] == "1"
        assert result["trace"] == "enabled"
    
    def test_uses_draft_version(self):
        """Should use DRAFT version when specified."""
        config = GuardRailsConfig(
            guardrail_id="gr-test123456",
            guardrail_version="DRAFT",
        )
        result = build_guardrails_config(config)
        
        assert result["guardrailVersion"] == "DRAFT"


class TestIsGuardrailsError:
    """Tests for is_guardrails_error function."""
    
    def test_detects_guardrail_keyword(self):
        """Should detect 'guardrail' keyword."""
        error = Exception("GuardRail intervention blocked the request")
        assert is_guardrails_error(error) is True
    
    def test_detects_intervention_keyword(self):
        """Should detect 'intervention' keyword."""
        error = Exception("Content intervention occurred")
        assert is_guardrails_error(error) is True
    
    def test_detects_blocked_keyword(self):
        """Should detect 'blocked' keyword."""
        error = Exception("Request was blocked due to policy")
        assert is_guardrails_error(error) is True
    
    def test_detects_content_policy_keyword(self):
        """Should detect 'content policy' keyword."""
        error = Exception("Violated content policy")
        assert is_guardrails_error(error) is True
    
    def test_case_insensitive(self):
        """Should be case insensitive."""
        error = Exception("GUARDRAIL INTERVENTION")
        assert is_guardrails_error(error) is True
    
    def test_returns_false_for_other_errors(self):
        """Should return False for non-GuardRails errors."""
        error = Exception("Connection timeout")
        assert is_guardrails_error(error) is False
    
    def test_returns_false_for_empty_message(self):
        """Should return False for empty error message."""
        error = Exception("")
        assert is_guardrails_error(error) is False


class TestHandleGuardrailsError:
    """Tests for handle_guardrails_error function."""
    
    def test_returns_intervention_message(self):
        """Should return the standard intervention message."""
        error = Exception("GuardRail blocked the request")
        result = handle_guardrails_error(error)
        
        assert result == GUARDRAILS_INTERVENTION_MESSAGE
    
    def test_accepts_guardrail_id(self):
        """Should accept guardrail_id parameter."""
        error = Exception("GuardRail blocked the request")
        result = handle_guardrails_error(
            error,
            guardrail_id="gr-test123456",
        )
        
        assert result == GUARDRAILS_INTERVENTION_MESSAGE
    
    def test_accepts_prompt_preview(self):
        """Should accept prompt_preview parameter."""
        error = Exception("GuardRail blocked the request")
        result = handle_guardrails_error(
            error,
            prompt_preview="This is a test prompt",
        )
        
        assert result == GUARDRAILS_INTERVENTION_MESSAGE


class TestGetGuardrailsInterventionMessage:
    """Tests for get_guardrails_intervention_message function."""
    
    def test_returns_standard_message(self):
        """Should return the standard intervention message."""
        result = get_guardrails_intervention_message()
        assert result == GUARDRAILS_INTERVENTION_MESSAGE
    
    def test_message_is_user_friendly(self):
        """Message should be user-friendly."""
        result = get_guardrails_intervention_message()
        
        assert "apologize" in result.lower()
        assert "rephrase" in result.lower()
