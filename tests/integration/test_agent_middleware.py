"""Integration tests for agent with middleware stack."""

import pytest

from src.agent.agent import create_booking_agent
from src.agent.middleware.booking_context import booking_context_middleware
from src.agent.middleware.business_rules import business_rules_middleware
from src.agent.middleware.usage_tracking import usage_tracking_middleware


@pytest.fixture
def agent():
    """Create a booking agent for testing."""
    return create_booking_agent(business_name="Test Barbershop")


class TestAgentStructure:
    """Tests for agent structure and middleware integration."""

    def test_agent_creation_with_middleware(self, agent):
        """Test that agent is created successfully with middleware stack."""
        assert agent is not None
        # Agent should be a compiled graph
        assert hasattr(agent, "invoke")
        assert hasattr(agent, "stream")

    def test_agent_has_checkpointer(self, agent):
        """Test that agent has memory checkpointer for HITL."""
        # Agent should have checkpointer for state management
        assert hasattr(agent, "checkpointer")
        assert agent.checkpointer is not None

    def test_business_rules_middleware_configured(self):
        """Test that business rules middleware has correct configuration."""
        assert business_rules_middleware.min_booking_hours == 2
        assert business_rules_middleware.max_booking_days == 90
        assert business_rules_middleware.min_cancellation_hours == 24
        assert business_rules_middleware.business_hours_start == 9
        assert business_rules_middleware.business_hours_end == 18
        assert 6 in business_rules_middleware.blocked_days  # Sunday

    def test_booking_context_middleware_exists(self):
        """Test that booking context middleware is properly initialized."""
        assert booking_context_middleware is not None
        assert booking_context_middleware.name == "booking_context"

    def test_usage_tracking_middleware_exists(self):
        """Test that usage tracking middleware is properly initialized."""
        assert usage_tracking_middleware is not None
        assert usage_tracking_middleware.name == "usage_tracking"

        # Can get stats
        stats = usage_tracking_middleware.get_stats()
        assert "total_input_tokens" in stats
        assert "total_output_tokens" in stats
        assert "total_tokens" in stats
        assert "total_calls" in stats


class TestMiddlewareIsolation:
    """Test that middleware instances are properly isolated."""

    def test_usage_tracking_independent_instances(self):
        """Test that usage tracking stats are independent."""
        from src.agent.middleware.usage_tracking import UsageTrackingMiddleware

        middleware1 = UsageTrackingMiddleware()
        middleware2 = UsageTrackingMiddleware()

        # They should have independent state
        assert middleware1 is not middleware2

        # Reset one shouldn't affect the other's initial state
        middleware1.reset_stats()
        stats1 = middleware1.get_stats()
        stats2 = middleware2.get_stats()

        assert stats1["total_calls"] == 0
        assert stats2["total_calls"] == 0

    def test_business_rules_customizable(self):
        """Test that business rules can be customized per instance."""
        from src.agent.middleware.business_rules import BusinessRulesMiddleware

        custom_rules = BusinessRulesMiddleware(
            min_booking_hours=4,
            max_booking_days=30,
            business_hours_start=10,
            business_hours_end=20,
            blocked_days=[5, 6],  # Sat, Sun
        )

        assert custom_rules.min_booking_hours == 4
        assert custom_rules.max_booking_days == 30
        assert custom_rules.business_hours_start == 10
        assert custom_rules.business_hours_end == 20
        assert 5 in custom_rules.blocked_days
        assert 6 in custom_rules.blocked_days


class TestAgentToolsIntegration:
    """Test that agent has access to all required tools."""

    def test_agent_has_tools(self, agent):
        """Test that agent is configured with tools."""
        # CompiledStateGraph should have nodes
        assert hasattr(agent, "nodes")
        # Agent should have tools node for tool execution
        assert "tools" in agent.nodes or "agent" in agent.nodes
