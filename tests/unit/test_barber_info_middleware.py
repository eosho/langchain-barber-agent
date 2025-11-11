"""Tests for BarberInfoMiddleware."""

from unittest.mock import Mock

import pytest

from src.agent.middleware.barber_info import BarberInfoMiddleware


class TestBarberInfoMiddleware:
    """Test suite for BarberInfoMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        return BarberInfoMiddleware()

    def test_middleware_name(self, middleware):
        """Test middleware has correct name."""
        assert middleware.name is not None
        assert len(middleware.name) > 0

    def test_has_state_schema(self, middleware):
        """Test that middleware has state schema defined."""
        assert middleware.state_schema is not None
        assert hasattr(middleware.state_schema, "__annotations__")

    def test_state_schema_fields(self, middleware):
        """Test state schema has required fields."""
        annotations = middleware.state_schema.__annotations__
        assert "selected_barber" in annotations

    def test_has_tools(self, middleware):
        """Test that middleware has tools defined."""
        assert middleware.tools is not None
        assert len(middleware.tools) == 3

    def test_tool_names(self, middleware):
        """Test barber info tool names."""
        tool_names = [tool.name for tool in middleware.tools]
        assert "list_barbers" in tool_names
        assert "get_barber_by_name" in tool_names
        assert "find_barbers_by_specialty" in tool_names

    def test_tools_have_descriptions(self, middleware):
        """Test that all tools have descriptions."""
        for tool in middleware.tools:
            assert tool.description is not None
            assert len(tool.description) > 0

    def test_tools_have_args_schema(self, middleware):
        """Test that all tools have args schema."""
        for tool in middleware.tools:
            assert tool.args_schema is not None

    def test_wrap_model_call_exists(self, middleware):
        """Test that wrap_model_call is configured."""
        assert middleware.wrap_model_call is not None

    def test_wrap_model_call_injects_prompt(self, middleware):
        """Test that wrap_model_call injects system prompt."""
        mock_request = Mock()
        mock_request.messages = []
        mock_request.system_prompt = ""

        mock_handler = Mock(return_value=Mock())

        result = middleware.wrap_model_call(mock_request, mock_handler)
        # wrap_model_call should inject system prompt
        assert result is not None
        # System prompt should have been updated
        assert len(mock_request.system_prompt) > 0

    def test_prompt_injection_updates_request(self, middleware):
        """Test that prompt injection updates the request."""
        mock_request = Mock()
        mock_request.messages = []
        mock_request.system_prompt = "original"
        original_prompt = mock_request.system_prompt

        mock_handler = Mock(return_value=Mock())

        middleware.wrap_model_call(mock_request, mock_handler)

        # System prompt should be updated
        assert mock_request.system_prompt != original_prompt
