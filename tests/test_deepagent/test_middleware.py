from eaia.deepagent.deepagent import EmailAgentMiddleware
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, ToolCall

SAMPLE_FIRST_MESSAGE = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Hello, how are you?"),
]

SAMPLE_MISSING_TOOL_CALL = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Hello, how are you?"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="123", name="get_events_for_days", args={"date_str": "2025-01-01"})]),
    HumanMessage(content="What is the weather in Tokyo?"),
]

SAMPLE_NO_MISSING_MESSAGES = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Hello, how are you?"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="123", name="get_events_for_days", args={"date_str": "2025-01-01"})]),
    ToolMessage(content="I have no events for that date.", tool_call_id="123"),
    HumanMessage(content="What is the weather in Tokyo?"),
]

SAMPLE_MISSING_TOOL_CALL_IN_FOLLOWUP = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Hello, how are you?"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="123", name="get_events_for_days", args={"date_str": "2025-01-01"})]),
    ToolMessage(content="I have no events for that date.", tool_call_id="123"),
    HumanMessage(content="What is the weather in Tokyo?"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="456", name="get_events_for_days", args={"date_str": "2025-01-01"})]),
    HumanMessage(content="What is the weather in Tokyo?"),
]

SAMPLE_MISSING_OLD_TOOL_CALL_AND_IN_FOLLOWUP = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Hello, how are you?"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="123", name="get_events_for_days", args={"date_str": "2025-01-01"})]),
    HumanMessage(content="What is the weather in Tokyo?"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="456", name="get_events_for_days", args={"date_str": "2025-01-01"})]),
    HumanMessage(content="What is the weather in Tokyo?"),
]

class TestMiddleware:
    def test_email_agent_middleware_first_message(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_FIRST_MESSAGE}
        no_update = middleware.before_model(agent_state, None)
        assert no_update is agent_state

    def test_email_agent_middleware_missing_tool_call(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_MISSING_TOOL_CALL}
        state_object = middleware.before_model(agent_state, None)
        assert state_object["messages"][3].type == "tool"
        assert len(state_object["messages"]) == 5

    def test_email_agent_middleware_no_missing_messages(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_NO_MISSING_MESSAGES}
        state_object = middleware.before_model(agent_state, None)
        assert state_object == agent_state

    def test_email_agent_middleware_missing_tool_call_in_followup(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_MISSING_TOOL_CALL_IN_FOLLOWUP}
        state_object = middleware.before_model(agent_state, None)
        assert len(state_object["messages"][2].tool_calls) == 1
        assert len(state_object["messages"][5].tool_calls) == 1
        assert state_object["messages"][6].type == "tool"
        assert len(state_object["messages"]) == 8

    def test_email_agent_middleware_missing_old_tool_call_and_in_followup(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_MISSING_OLD_TOOL_CALL_AND_IN_FOLLOWUP}
        state_object = middleware.before_model(agent_state, None)
        assert len(state_object["messages"][2].tool_calls) == 1
        assert state_object["messages"][3].type == "tool"
        assert state_object["messages"][3].tool_call_id == "123"
        assert len(state_object["messages"][5].tool_calls) == 1
        assert state_object["messages"][6].type == "tool"
        assert state_object["messages"][6].tool_call_id == "456"
        assert len(state_object["messages"]) == 8