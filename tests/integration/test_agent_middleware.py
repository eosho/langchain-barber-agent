"""Integration tests for agent with middleware stack."""

import pytest

from src.agent.agent import create_booking_agent
from src.agent.middleware.usage_tracking import UsageTrackingMiddleware


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

    def test_usage_tracking_middleware_exists(self):
        """Test that usage tracking middleware is properly initialized."""
        assert UsageTrackingMiddleware() is not None
        assert UsageTrackingMiddleware().name == "usage_tracking"

        # Can get stats
        stats = UsageTrackingMiddleware().get_stats()
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


class TestAgentToolsIntegration:
    """Test that agent has access to all required tools."""

    def test_agent_has_tools(self, agent):
        """Test that agent is configured with tools."""
        # CompiledStateGraph should have nodes
        assert hasattr(agent, "nodes")
        # Agent should have tools node for tool execution
        assert "tools" in agent.nodes or "agent" in agent.nodes
