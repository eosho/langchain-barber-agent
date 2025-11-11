"""Unit tests for usage tracking middleware."""

from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage

from src.agent.middleware.usage_tracking import UsageTrackingMiddleware


@pytest.fixture
def middleware():
    """Create a UsageTrackingMiddleware instance for testing."""
    return UsageTrackingMiddleware()


@pytest.fixture
def mock_state():
    """Create a mock agent state."""
    return {"messages": []}


@pytest.fixture
def mock_runtime():
    """Create a mock runtime."""
    return Mock()


class TestUsageTracking:
    """Tests for usage tracking middleware."""

    def test_middleware_name(self, middleware):
        """Test middleware has correct name."""
        assert middleware.name == "usage_tracking"

    def test_after_model_tracks_tokens(self, middleware, mock_runtime):
        """Test that after_model tracks token usage from AI messages."""
        # Create AI message with token usage
        ai_message = AIMessage(
            content="Test response",
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        )
        state_with_message = {"messages": [ai_message]}

        # Call after_model
        middleware.after_model(state_with_message, mock_runtime)

        # Verify tracking
        stats = middleware.get_stats()
        assert stats["total_input_tokens"] == 100
        assert stats["total_output_tokens"] == 50
        assert stats["total_tokens"] == 150
        assert stats["total_calls"] == 1

    def test_after_model_accumulates_tokens(self, middleware, mock_runtime):
        """Test that multiple calls accumulate token counts."""
        # First message
        ai_message1 = AIMessage(
            content="First response",
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        )
        middleware.after_model({"messages": [ai_message1]}, mock_runtime)

        # Second message
        ai_message2 = AIMessage(
            content="Second response",
            usage_metadata={
                "input_tokens": 200,
                "output_tokens": 75,
                "total_tokens": 275,
            },
        )
        middleware.after_model({"messages": [ai_message2]}, mock_runtime)

        # Verify accumulated totals
        stats = middleware.get_stats()
        assert stats["total_input_tokens"] == 300
        assert stats["total_output_tokens"] == 125
        assert stats["total_tokens"] == 425
        assert stats["total_calls"] == 2

    def test_after_model_handles_missing_usage_metadata(self, middleware, mock_runtime):
        """Test that messages without usage_metadata are handled gracefully."""
        ai_message = AIMessage(content="Test response without metadata")
        state_with_message = {"messages": [ai_message]}

        # Should not raise error
        middleware.after_model(state_with_message, mock_runtime)

        # Stats should remain at zero
        stats = middleware.get_stats()
        assert stats["total_input_tokens"] == 0
        assert stats["total_output_tokens"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_calls"] == 0

    def test_after_model_handles_empty_messages(self, middleware, mock_runtime):
        """Test that empty message list is handled gracefully."""
        middleware.after_model({"messages": []}, mock_runtime)

        # Should not raise error and stats remain zero
        stats = middleware.get_stats()
        assert stats["total_input_tokens"] == 0
        assert stats["total_output_tokens"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_calls"] == 0

    def test_reset_stats(self, middleware, mock_runtime):
        """Test that reset_stats clears all counters."""
        # Add some usage
        ai_message = AIMessage(
            content="Test response",
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        )
        middleware.after_model({"messages": [ai_message]}, mock_runtime)

        # Verify stats exist
        stats = middleware.get_stats()
        assert stats["total_tokens"] > 0

        # Reset
        middleware.reset_stats()

        # Verify stats are cleared
        stats = middleware.get_stats()
        assert stats["total_input_tokens"] == 0
        assert stats["total_output_tokens"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_calls"] == 0

    def test_get_stats_returns_copy(self, middleware):
        """Test that get_stats returns a copy, not reference."""
        stats1 = middleware.get_stats()
        stats1["total_input_tokens"] = 999

        stats2 = middleware.get_stats()
        assert stats2["total_input_tokens"] == 0  # Original unchanged


class TestUsageTrackingSingleton:
    """Test usage tracking singleton instance."""

    def test_singleton_instance_exists(self):
        """Test that singleton instance is available."""
        from src.agent.middleware.usage_tracking import UsageTrackingMiddleware

        assert UsageTrackingMiddleware() is not None
        assert isinstance(UsageTrackingMiddleware(), UsageTrackingMiddleware)
