# Barbershop Booking Agent - Multiple Implementations

This project provides two agent implementations for the barbershop booking system:

## 1. LangChain `create_agent` (Recommended for most use cases)

The high-level `create_agent` implementation provides a simpler interface with built-in middleware support.

### Features
- Built-in middleware for state management, conversation history, and error handling
- Automatic tool registration and execution
- Simplified configuration
- Best for: Quick setup, standard agent workflows

### Usage

```python
from src.agent.agent import create_booking_agent, run_agent_conversation

# Create agent (automatically uses middleware)
agent = create_booking_agent()

# Run conversation
result = await agent.ainvoke({
    "messages": [
        {"role": "user", "content": "I need a haircut this Friday at 2pm"}
    ]
})

print(result["messages"][-1]["content"])

# Or use convenience function
response = await run_agent_conversation("Book a haircut for Friday")
print(response["content"])
```

## 2. LangGraph `StateGraph` (Advanced use cases)

The LangGraph implementation provides granular control over the agent execution flow with explicit nodes and edges.

### Features
- Explicit node definitions for model and tools
- Conditional routing logic
- Full control over state updates
- Easier to debug and visualize
- Best for: Custom workflows, complex routing, debugging

### Usage

```python
from src.agent.graph import create_booking_graph, run_graph_conversation

# Create graph
graph = create_booking_graph()

# Run conversation
result = await graph.ainvoke({
    "messages": [
        {"role": "user", "content": "I need a haircut this Friday at 2pm"}
    ]
})

print(result["messages"][-1].content)

# Or use convenience function
response = await run_graph_conversation("Book a haircut for Friday")
print(response["content"])
```

### Visualize the graph

```python
from IPython.display import Image, display

graph = create_booking_graph()
display(Image(graph.get_graph().draw_mermaid_png()))
```

## Azure OpenAI Support

Both implementations support Azure OpenAI. Configure via environment variables:

```bash
# Option 1: Use OpenAI (default)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4

# Option 2: Use Azure OpenAI
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-03-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
OPENAI_MODEL=gpt-4  # Model name for internal reference
```

## Configuration

All settings are managed in `src/core/config.py` and can be overridden via environment variables:

```python
from src.core.config import get_settings

settings = get_settings()
print(f"Using provider: {settings.llm_provider}")
print(f"Model: {settings.openai_model}")
```

## Which implementation to choose?

| Use Case | Recommended Implementation |
|----------|---------------------------|
| Standard booking workflow | `create_agent` |
| Need middleware customization | `create_agent` |
| Quick prototyping | `create_agent` |
| Custom routing logic | `StateGraph` |
| Complex multi-step workflows | `StateGraph` |
| Need to visualize execution | `StateGraph` |
| Debugging agent behavior | `StateGraph` |
| Custom state management | `StateGraph` |

Both implementations:
- Use the same tools from `src/agent/tools/`
- Support the same LLM providers (OpenAI, Azure OpenAI)
- Maintain conversation history
- Handle errors gracefully
- Support async execution

The main difference is that `create_agent` abstracts away the graph structure and provides middleware hooks, while `StateGraph` gives you explicit control over nodes and edges.
