"""Unit tests for booking context middleware."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.agent.middleware.booking_context import BookingContextMiddleware


@pytest.fixture
def middleware():
    """Create a BookingContextMiddleware instance for testing."""
    return BookingContextMiddleware()


@pytest.fixture
def mock_state():
    """Create a mock agent state."""
    return {"messages": []}


@pytest.fixture
def mock_runtime():
    """Create a mock runtime."""
    return Mock()


class TestBookingContext:
    """Tests for booking context middleware."""

    def test_middleware_name(self, middleware):
        """Test middleware has correct name."""
        assert middleware.name == "booking_context"

    def test_before_model_adds_current_date(self, middleware, mock_state, mock_runtime):
        """Test that current date is added if not present."""
        result = middleware.before_model(mock_state, mock_runtime)

        assert result is not None
        assert "current_date" in result
        # Verify it's a valid date format
        datetime.strptime(result["current_date"], "%Y-%m-%d")

    def test_before_model_adds_conversation_stage(self, middleware, mock_state, mock_runtime):
        """Test that conversation stage is initialized."""
        result = middleware.before_model(mock_state, mock_runtime)

        assert result is not None
        assert "conversation_stage" in result
        assert result["conversation_stage"] == "greeting"

    def test_before_model_adds_business_name(self, middleware, mock_state, mock_runtime):
        """Test that business name is added."""
        result = middleware.before_model(mock_state, mock_runtime)

        assert result is not None
        assert "business_name" in result
        assert result["business_name"] == "The Barbershop"

    def test_before_model_skips_existing_values(self, middleware, mock_runtime):
        """Test that existing values are not overwritten."""
        state_with_values = {
            "messages": [],
            "current_date": "2025-01-01",
            "conversation_stage": "booking",
            "business_name": "Custom Shop",
        }

        result = middleware.before_model(state_with_values, mock_runtime)

        # Should return None or empty dict since all values exist
        assert result is None or result == {}

    def test_before_model_adds_only_missing_values(self, middleware, mock_runtime):
        """Test that only missing values are added."""
        state_with_partial = {
            "messages": [],
            "current_date": "2025-01-01",
            # Missing conversation_stage and business_name
        }

        result = middleware.before_model(state_with_partial, mock_runtime)

        assert result is not None
        assert "current_date" not in result  # Already exists
        assert "conversation_stage" in result
        assert "business_name" in result

    def test_before_model_handles_customer_context(self, middleware, mock_runtime, capsys):
        """Test that customer context is logged when present."""
        state_with_context = {
            "messages": [],
            "customer_id": "cust-123",
            "service_id": "svc-456",
        }

        middleware.before_model(state_with_context, mock_runtime)

        # Check console output
        captured = capsys.readouterr()
        assert "BookingContext" in captured.out
        assert "cust-123" in captured.out
        assert "svc-456" in captured.out


class TestBookingContextSingleton:
    """Test booking context singleton instance."""

    def test_singleton_instance_exists(self):
        """Test that singleton instance is available."""
        from src.agent.middleware.booking_context import booking_context_middleware

        assert booking_context_middleware is not None
        assert isinstance(booking_context_middleware, BookingContextMiddleware)
