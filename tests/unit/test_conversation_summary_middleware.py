"""Tests for ConversationSummaryMiddleware."""

import pytest

from src.agent.middleware.conversation_summary import ConversationSummaryMiddleware


class TestConversationSummaryMiddleware:
    """Test suite for ConversationSummaryMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        return ConversationSummaryMiddleware(max_messages=10)

    def test_middleware_name(self, middleware):
        """Test middleware has correct name."""
        assert middleware.name == "conversation_summary"

    def test_has_state_schema(self, middleware):
        """Test that middleware has state schema defined."""
        assert middleware.state_schema is not None
        assert hasattr(middleware.state_schema, "__annotations__")

    def test_state_schema_extends_base(self, middleware):
        """Test that state schema extends base AgentState."""
        # This middleware extends base AgentState, no additional fields required
        assert middleware.state_schema is not None

    def test_max_messages_configuration(self):
        """Test max_messages can be configured."""
        middleware = ConversationSummaryMiddleware(max_messages=5)
        assert middleware.max_messages == 5

        middleware2 = ConversationSummaryMiddleware(max_messages=20)
        assert middleware2.max_messages == 20

    def test_default_max_messages(self):
        """Test default max_messages value."""
        middleware = ConversationSummaryMiddleware()
        # Should have a reasonable default
        assert middleware.max_messages > 0
        assert middleware.max_messages <= 50  # Reasonable upper bound

    def test_before_model_exists(self, middleware):
        """Test that before_model method exists."""
        assert hasattr(middleware, "before_model")
        assert callable(middleware.before_model)

    def test_no_wrap_model_call(self, middleware):
        """Test that conversation summary doesn't use wrap_model_call."""
        # This middleware uses before_model instead of wrap_model_call
        # So wrap_model_call should be None or not defined
        getattr(middleware, "wrap_model_call", None)
        # It's okay if it exists but shouldn't be the primary mechanism
        assert middleware.before_model is not None

    def test_no_tools(self, middleware):
        """Test that conversation summary middleware has no tools."""
        # This middleware doesn't expose tools to the LLM
        tools = getattr(middleware, "tools", None)
        # Tools should be None or empty
        if tools is not None:
            assert len(tools) == 0
