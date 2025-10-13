from eaia.deepagent.deepagent import EmailAgentMiddleware
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, ToolCall, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.graph.message import add_messages

SAMPLE_FIRST_MESSAGE = [
    SystemMessage(content="You are a helpful assistant.", id="1"),
    HumanMessage(content="Hello, how are you?", id="2"),
]

SAMPLE_MISSING_TOOL_CALL = [
    SystemMessage(content="You are a helpful assistant.", id="1"),
    HumanMessage(content="Hello, how are you?", id="2"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="123", name="get_events_for_days", args={"date_str": "2025-01-01"})], id="3"),
    HumanMessage(content="What is the weather in Tokyo?", id="4"),
]

SAMPLE_NO_MISSING_MESSAGES = [
    SystemMessage(content="You are a helpful assistant.", id="1"),
    HumanMessage(content="Hello, how are you?", id="2"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="123", name="get_events_for_days", args={"date_str": "2025-01-01"})], id="3"),
    ToolMessage(content="I have no events for that date.", tool_call_id="123", id="4"),
    HumanMessage(content="What is the weather in Tokyo?", id="5"),
]

SAMPLE_MISSING_TOOL_CALL_IN_FOLLOWUP = [
    SystemMessage(content="You are a helpful assistant.", id="1"),
    HumanMessage(content="Hello, how are you?", id="2"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="123", name="get_events_for_days", args={"date_str": "2025-01-01"})], id="3"),
    ToolMessage(content="I have no events for that date.", tool_call_id="123", id="4"),
    HumanMessage(content="What is the weather in Tokyo?", id="5"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="456", name="get_events_for_days", args={"date_str": "2025-01-01"})], id="6"),
    HumanMessage(content="What is the weather in Tokyo?", id="7"),
]

SAMPLE_MISSING_OLD_TOOL_CALL_AND_IN_FOLLOWUP = [
    SystemMessage(content="You are a helpful assistant.", id="1"),
    HumanMessage(content="Hello, how are you?", id="2"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="123", name="get_events_for_days", args={"date_str": "2025-01-01"})], id="3"),
    HumanMessage(content="What is the weather in Tokyo?", id="4"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="456", name="get_events_for_days", args={"date_str": "2025-01-01"})], id="5"),
    HumanMessage(content="What is the weather in Tokyo?", id="6"),
]

SAMPLE_FIX_BAD_MESSAGES = [
    SystemMessage(content="You are a helpful assistant.", id="1"),
    HumanMessage(content="Hello, how are you?", id="2"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="123", name="get_events_for_days", args={"date_str": "2025-01-01"})], id="3"),
    HumanMessage(content="What is the weather in Tokyo?", id="4"),
    HumanMessage(content="What is the weather in Tokyo?", id="5"),
    ToolMessage(content="I have no events for that date.", tool_call_id="123", id="6"),
    HumanMessage(content="What is the weather in Tokyo?", id="7"),
    HumanMessage(content="What is the weather in Tokyo?", id="8"),
    HumanMessage(content="What is the weather in Tokyo?", id="9"),
]

SAMPLE_FIX_BAD_MESSAGES_2 = [
    SystemMessage(content="You are a helpful assistant.", id="1"),
    HumanMessage(content="Hello, how are you?", id="2"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="123", name="get_events_for_days", args={"date_str": "2025-01-01"})], id="3"),
    HumanMessage(content="What is the weather in Tokyo?", id="4"),
    HumanMessage(content="What is the weather in Tokyo?", id="5"),
    ToolMessage(content="I have no events for that date.", tool_call_id="123", id="6"),
    HumanMessage(content="What is the weather in Tokyo?", id="7"),
    HumanMessage(content="What is the weather in Tokyo?", id="8"),
    AIMessage(content="I'm doing well, thank you!", tool_calls=[ToolCall(id="456", name="get_events_for_days", args={"date_str": "2025-01-01"})], id="9"),
    HumanMessage(content="What is the weather in Tokyo?", id="10"),
    HumanMessage(content="What is the weather in Tokyo?", id="11"),
]

class TestMiddleware:
    def test_email_agent_middleware_first_message(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_FIRST_MESSAGE}
        state_update = middleware.before_agent(agent_state, None)
        assert state_update["messages"] == [RemoveMessage(id=REMOVE_ALL_MESSAGES)] + SAMPLE_FIRST_MESSAGE
        final_messages = add_messages(agent_state["messages"], state_update["messages"])
        assert final_messages == SAMPLE_FIRST_MESSAGE

    def test_email_agent_middleware_missing_tool_call(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_MISSING_TOOL_CALL}
        state_update = middleware.before_agent(agent_state, None)
        assert len(state_update["messages"]) == 6
        assert state_update["messages"][0].type == "remove"
        final_messages = add_messages(agent_state["messages"], state_update["messages"])
        assert len(final_messages) == 5
        assert state_update["messages"][0].type == "remove"
        assert final_messages[0].type == "system"
        assert final_messages[1].type == "human"
        assert final_messages[2].type == "ai"
        assert final_messages[2].tool_calls[0]["id"] == "123"
        assert final_messages[3].type == "tool"
        assert final_messages[3].tool_call_id == "123"
        assert final_messages[4].type == "human"

    def test_email_agent_middleware_no_missing_messages(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_NO_MISSING_MESSAGES}
        state_update = middleware.before_agent(agent_state, None)
        assert len(state_update["messages"]) == 6
        assert state_update["messages"][0].type == "remove"
        final_messages = add_messages(agent_state["messages"], state_update["messages"])
        assert len(final_messages) == 5
        assert state_update["messages"][0].type == "remove"
        assert final_messages[0].type == "system"
        assert final_messages[1].type == "human"
        assert final_messages[2].type == "ai"
        assert final_messages[2].tool_calls[0]["id"] == "123"
        assert final_messages[3].type == "tool"
        assert final_messages[3].tool_call_id == "123"
        assert final_messages[4].type == "human"

    def test_email_agent_middleware_missing_tool_call_in_followup(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_MISSING_TOOL_CALL_IN_FOLLOWUP}
        state_update = middleware.before_agent(agent_state, None)
        assert len(state_update["messages"]) == 9
        assert state_update["messages"][0].type == "remove"
        final_messages = add_messages(agent_state["messages"], state_update["messages"])
        assert len(final_messages) == 8
        assert state_update["messages"][0].type == "remove"
        assert final_messages[0].type == "system"
        assert final_messages[1].type == "human"
        assert final_messages[2].type == "ai"
        assert final_messages[2].tool_calls[0]["id"] == "123"
        assert final_messages[3].type == "tool"
        assert final_messages[3].tool_call_id == "123"
        assert final_messages[4].type == "human"
        assert final_messages[5].type == "ai"
        assert final_messages[5].tool_calls[0]["id"] == "456"
        assert final_messages[6].type == "tool"
        assert final_messages[6].tool_call_id == "456"
        assert final_messages[7].type == "human"

    def test_email_agent_middleware_missing_old_tool_call_and_in_followup(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_MISSING_OLD_TOOL_CALL_AND_IN_FOLLOWUP}
        state_update = middleware.before_agent(agent_state, None)
        assert len(state_update["messages"]) == 9
        assert state_update["messages"][0].type == "remove"
        final_messages = add_messages(agent_state["messages"], state_update["messages"])
        assert len(final_messages) == 8
        assert state_update["messages"][0].type == "remove"
        assert final_messages[0].type == "system"
        assert final_messages[1].type == "human"
        assert final_messages[2].type == "ai"
        assert final_messages[2].tool_calls[0]["id"] == "123"
        assert final_messages[3].type == "tool"
        assert final_messages[3].tool_call_id == "123"
        assert final_messages[4].type == "human"
        assert final_messages[5].type == "ai"
        assert final_messages[5].tool_calls[0]["id"] == "456"
        assert final_messages[6].type == "tool"
        assert final_messages[6].tool_call_id == "456"
        assert final_messages[7].type == "human"

    def test_sample_fix_bad_messages(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_FIX_BAD_MESSAGES}
        state_update = middleware.before_agent(agent_state, None)
        assert len(state_update["messages"]) == 8
        assert state_update["messages"][0].type == "remove"
        final_messages = add_messages(agent_state["messages"], state_update["messages"])
        assert len(final_messages) == 7
        assert state_update["messages"][0].type == "remove"
        assert final_messages[0].type == "system"
        assert final_messages[1].type == "human"
        assert final_messages[2].type == "ai"
        assert final_messages[2].tool_calls[0]["id"] == "123"
        assert final_messages[3].type == "tool"
        assert final_messages[3].tool_call_id == "123"
        assert final_messages[4].type == "human"
        assert final_messages[5].type == "human"
        assert final_messages[6].type == "human"

    def test_sample_fix_bad_messages_2(self):
        middleware = EmailAgentMiddleware()
        agent_state = {"messages": SAMPLE_FIX_BAD_MESSAGES_2}
        state_update = middleware.before_agent(agent_state, None)
        assert len(state_update["messages"]) == 11
        assert state_update["messages"][0].type == "remove"
        final_messages = add_messages(agent_state["messages"], state_update["messages"])
        assert len(final_messages) == 10
        assert state_update["messages"][0].type == "remove"
        assert final_messages[0].type == "system"
        assert final_messages[1].type == "human"
        assert final_messages[2].type == "ai"
        assert final_messages[2].tool_calls[0]["id"] == "123"
        assert final_messages[3].type == "tool"
        assert final_messages[3].tool_call_id == "123"
        assert final_messages[4].type == "human"
        assert final_messages[5].type == "human"
        assert final_messages[6].type == "ai"
        assert final_messages[6].tool_calls[0]["id"] == "456"
        assert final_messages[7].type == "tool"
        assert final_messages[7].tool_call_id == "456"
        assert final_messages[8].type == "human"
        assert final_messages[9].type == "human"