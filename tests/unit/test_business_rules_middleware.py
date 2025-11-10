"""Unit tests for business rules middleware."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.agent.middleware.business_rules import BusinessRulesMiddleware


@pytest.fixture
def middleware():
    """Create a BusinessRulesMiddleware instance for testing."""
    return BusinessRulesMiddleware(
        min_booking_hours=2,
        max_booking_days=90,
        min_cancellation_hours=24,
        business_hours_start=9,
        business_hours_end=18,
        blocked_days=[6],  # Sunday
    )


@pytest.fixture
def mock_state():
    """Create a mock agent state."""
    return {"messages": []}


class TestValidateBookingCancellation:
    """Tests for _validate_booking_cancellation method."""

    @pytest.mark.asyncio
    async def test_cancellation_within_notice_period_blocked(self, middleware, mock_state):
        """Test that cancellations within 24 hours are blocked."""
        booking_id = "test-booking-123"

        # Booking is 12 hours from now (less than 24 hour minimum)
        future_time = datetime.now() + timedelta(hours=12)
        mock_booking = {
            "id": booking_id,
            "start_time": future_time.isoformat(),
            "status": "confirmed",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_booking
            mock_response.raise_for_status = Mock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await middleware._validate_booking_cancellation(
                {"booking_id": booking_id}, mock_state
            )

            assert result is not None
            assert "24 hours notice" in result

    @pytest.mark.asyncio
    async def test_cancellation_with_sufficient_notice_allowed(self, middleware, mock_state):
        """Test that cancellations with 24+ hours notice are allowed."""
        booking_id = "test-booking-456"

        # Booking is 48 hours from now (more than 24 hour minimum)
        future_time = datetime.now() + timedelta(hours=48)
        mock_booking = {
            "id": booking_id,
            "start_time": future_time.isoformat(),
            "status": "confirmed",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_booking
            mock_response.raise_for_status = Mock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await middleware._validate_booking_cancellation(
                {"booking_id": booking_id}, mock_state
            )

            assert result is None  # No violation

    @pytest.mark.asyncio
    async def test_cancellation_of_past_booking_blocked(self, middleware, mock_state):
        """Test that past bookings cannot be cancelled."""
        booking_id = "test-booking-789"

        # Booking was 2 hours ago
        past_time = datetime.now() - timedelta(hours=2)
        mock_booking = {
            "id": booking_id,
            "start_time": past_time.isoformat(),
            "status": "confirmed",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_booking
            mock_response.raise_for_status = Mock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await middleware._validate_booking_cancellation(
                {"booking_id": booking_id}, mock_state
            )

            assert result is not None
            assert "already passed" in result

    @pytest.mark.asyncio
    async def test_cancellation_handles_errors_gracefully(self, middleware, mock_state):
        """Test that API errors allow cancellation to proceed (fail-safe)."""
        booking_id = "test-booking-500"

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            http_error = httpx.HTTPStatusError(
                "Server error", request=Mock(), response=mock_response
            )

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=http_error)

            result = await middleware._validate_booking_cancellation(
                {"booking_id": booking_id}, mock_state
            )

            # Should return None (allow cancellation) on server errors
            assert result is None


class TestValidateBookingCreation:
    """Tests for _validate_booking_creation method."""

    def test_booking_within_business_hours_allowed(self, middleware):
        """Test that bookings within business hours are allowed."""
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        tool_input = {"date": future_date, "time": "10:00"}

        result = middleware._validate_booking_creation(tool_input)

        assert result is None  # No violation

    def test_booking_outside_business_hours_blocked(self, middleware):
        """Test that bookings outside business hours are blocked."""
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        # Before opening
        result = middleware._validate_booking_creation({"date": future_date, "time": "08:00"})
        assert result is not None
        assert "business hours" in result

        # After closing
        result = middleware._validate_booking_creation({"date": future_date, "time": "18:00"})
        assert result is not None
        assert "business hours" in result

    def test_booking_on_blocked_day(self, middleware):
        """Test that bookings on blocked days (Sunday) are rejected."""
        # Find next Sunday
        now = datetime.now()
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        next_sunday = now + timedelta(days=days_until_sunday)

        tool_input = {"date": next_sunday.strftime("%Y-%m-%d"), "time": "10:00"}

        result = middleware._validate_booking_creation(tool_input)

        assert result is not None
        assert "Sunday" in result

    def test_booking_minimum_advance_time_enforced(self, middleware):
        """Test that minimum 2 hours advance booking is enforced."""
        # 1 hour from now (less than minimum)
        future_time = datetime.now() + timedelta(hours=1)
        tool_input = {
            "date": future_time.strftime("%Y-%m-%d"),
            "time": future_time.strftime("%H:%M"),
        }

        result = middleware._validate_booking_creation(tool_input)

        assert result is not None
        assert "2 hours in advance" in result

    def test_booking_maximum_advance_time_enforced(self, middleware):
        """Test that maximum 90 days advance booking is enforced."""
        # 100 days from now (more than maximum)
        future_time = datetime.now() + timedelta(days=100)
        tool_input = {"date": future_time.strftime("%Y-%m-%d"), "time": "10:00"}

        result = middleware._validate_booking_creation(tool_input)

        assert result is not None
        assert "90 days" in result


class TestBeforeTool:
    """Tests for before_tool integration."""

    @pytest.mark.asyncio
    async def test_before_tool_validates_create_booking(self, middleware, mock_state):
        """Test that create_booking is validated."""
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        tool_input = {"date": future_date, "time": "10:00"}

        result = await middleware.before_tool("create_booking", tool_input, mock_state, Mock())

        assert result is None  # Valid booking

    @pytest.mark.asyncio
    async def test_before_tool_validates_cancel_booking(self, middleware, mock_state):
        """Test that cancel_booking is validated."""
        booking_id = "test-booking-123"
        future_time = datetime.now() + timedelta(hours=48)
        mock_booking = {
            "id": booking_id,
            "start_time": future_time.isoformat(),
            "status": "confirmed",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_booking
            mock_response.raise_for_status = Mock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await middleware.before_tool(
                "cancel_booking", {"booking_id": booking_id}, mock_state, Mock()
            )

            assert result is None  # Valid cancellation

    @pytest.mark.asyncio
    async def test_before_tool_blocks_invalid_operations(self, middleware, mock_state):
        """Test that rule violations are blocked with proper response structure."""
        # Try to book outside business hours
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        tool_input = {"date": future_date, "time": "20:00"}

        result = await middleware.before_tool("create_booking", tool_input, mock_state, Mock())

        assert result is not None
        assert "messages" in result
        assert "rule_violation" in result
        assert "business hours" in result["rule_violation"]
