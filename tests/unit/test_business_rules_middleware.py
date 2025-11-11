"""Tests for BusinessRulesMiddleware."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.agent.middleware.business_rules import BusinessRulesMiddleware


class TestBusinessRulesMiddleware:
    """Test suite for BusinessRulesMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        return BusinessRulesMiddleware()

    @pytest.fixture
    def mock_state(self):
        """Create mock agent state."""
        return {}

    @pytest.fixture
    def mock_runtime(self):
        """Create mock runtime."""
        return Mock()

    def test_middleware_name(self, middleware):
        """Test middleware has correct name."""
        assert middleware.name == "business_rules"

    def test_valid_future_booking(self, middleware, mock_state, mock_runtime):
        """Test valid booking 2 days in future."""
        future_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        tool_input = {
            "date": future_date,
            "time": "14:00",
            "customer_id": "123",
            "barber_id": "456",
            "service_id": "789",
        }

        result = middleware.before_tool_call("create_booking", tool_input, mock_state, mock_runtime)

        assert result is None  # No error means validation passed

    def test_same_day_booking_insufficient_notice(self, middleware, mock_state, mock_runtime):
        """Test same-day booking with < 2 hours notice is rejected."""
        # Book 1 hour from now BEFORE cutoff (10am + 1h = 11am, cutoff is 2pm)
        now = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        booking_time = now + timedelta(hours=1)

        # Monkey patch datetime.now() for consistent testing
        with patch("src.agent.middleware.business_rules.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.strptime = datetime.strptime  # Keep strptime working

            tool_input = {
                "date": booking_time.strftime("%Y-%m-%d"),
                "time": booking_time.strftime("%H:%M"),
                "customer_id": "123",
                "barber_id": "456",
                "service_id": "789",
            }

            result = middleware.before_tool_call(
                "create_booking", tool_input, mock_state, mock_runtime
            )

            assert result is not None
            assert "error" in result
            assert result["policy"] == "minimum_notice"
            assert "2" in result["error"]  # 2 hours minimum

    def test_same_day_booking_after_cutoff(self, middleware, mock_state, mock_runtime):
        """Test same-day booking after daily cutoff is rejected."""
        # Mock current time to 3pm (after 2pm cutoff)
        now = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
        # Try to book for 6pm (still future, but after cutoff)
        booking_time = now.replace(hour=18, minute=0)

        with patch("src.agent.middleware.business_rules.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.strptime = datetime.strptime

            tool_input = {
                "date": booking_time.strftime("%Y-%m-%d"),
                "time": booking_time.strftime("%H:%M"),
                "customer_id": "123",
                "barber_id": "456",
                "service_id": "789",
            }

            result = middleware.before_tool_call(
                "create_booking", tool_input, mock_state, mock_runtime
            )

            assert result is not None
            assert "error" in result
            assert result["policy"] == "same_day_cutoff"

    def test_past_booking_rejected(self, middleware, mock_state, mock_runtime):
        """Test booking in the past is rejected."""
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        tool_input = {
            "date": past_date,
            "time": "14:00",
            "customer_id": "123",
            "barber_id": "456",
            "service_id": "789",
        }

        result = middleware.before_tool_call("create_booking", tool_input, mock_state, mock_runtime)

        assert result is not None
        assert "error" in result
        assert result["policy"] == "no_past_bookings"
        assert "past" in result["error"].lower()

    def test_booking_too_far_advance(self, middleware, mock_state, mock_runtime):
        """Test booking beyond maximum advance days is rejected."""
        # Try to book 30 days in advance (max is 14)
        far_future = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        tool_input = {
            "date": far_future,
            "time": "14:00",
            "customer_id": "123",
            "barber_id": "456",
            "service_id": "789",
        }

        result = middleware.before_tool_call("create_booking", tool_input, mock_state, mock_runtime)

        assert result is not None
        assert "error" in result
        assert result["policy"] == "max_advance_booking"

    def test_cancellation_insufficient_notice(self, middleware, mock_state, mock_runtime):
        """Test cancellation with < 24 hours notice is rejected."""
        # Try to cancel booking 12 hours from now
        booking_time = datetime.now() + timedelta(hours=12)
        tool_input = {
            "booking_id": "123",
            "booking_datetime": booking_time.isoformat(),
        }

        result = middleware.before_tool_call("cancel_booking", tool_input, mock_state, mock_runtime)

        assert result is not None
        assert "error" in result
        assert result["policy"] == "cancellation_notice"
        assert "24" in result["error"]  # 24 hours required

    def test_cancellation_sufficient_notice(self, middleware, mock_state, mock_runtime):
        """Test cancellation with > 24 hours notice is allowed."""
        # Cancel booking 48 hours from now
        booking_time = datetime.now() + timedelta(hours=48)
        tool_input = {
            "booking_id": "123",
            "booking_datetime": booking_time.isoformat(),
        }

        result = middleware.before_tool_call("cancel_booking", tool_input, mock_state, mock_runtime)

        assert result is None  # No error means validation passed

    def test_non_booking_tool_passes_through(self, middleware, mock_state, mock_runtime):
        """Test non-booking tools are not validated."""
        tool_input = {"email": "test@example.com"}

        result = middleware.before_tool_call(
            "lookup_customer", tool_input, mock_state, mock_runtime
        )

        assert result is None  # Should pass through without validation


class TestBusinessRulesMiddlewareSingleton:
    """Test singleton instance."""

    def test_singleton_instance_exists(self):
        """Test that singleton instance is importable."""
        from src.agent.middleware.business_rules import BusinessRulesMiddleware

        assert BusinessRulesMiddleware() is not None
        assert isinstance(BusinessRulesMiddleware(), BusinessRulesMiddleware)
