
from datetime import datetime, timedelta
from langsmith import testing as t
from eaia.main.graph import graph, take_action
from langgraph.store.memory import InMemoryStore
import json
import pytest

time_input = {
  "email": {
    "id": "943e07b28c61f5da",
    "thread_id": "b26f4d381059e7ca",
    "from_email": "Isaac <isaac@langchain.dev>",
    "subject": "Follow up for meeting",
    "page_content": "Hey Harrison,\n\nHope things are well! When we met last week we discussed meeting at 10am tuesday, I confirmed with your scheduler that it still works for you so feel free to send over a calendar invite - if not, we can reschedule for another time.\n\nIsaac",
    "send_time": "2025-01-17T14:27:06-08:00",
    "to_email": "Harrison Chase <harrison@langchain.dev>"
  },
  "triage": {
    "logic": "The email is from someone Harrison has a pre-existing relationship with, as they mention a previous meeting. Isaac is asking to confirm a meeting time, which requires Harrison's response to either confirm or reschedule. This aligns with the criteria for emails worth responding to.",
    "response": "email"
  },
  "messages": []
}

config = {"configurable": {"__pregel_store": InMemoryStore(), 
    "checkpoint_ns": ""
}}

@pytest.mark.langsmith
async def test_time_proposal():
    t.log_inputs(time_input)

    res = await graph.nodes['draft_response'].ainvoke(time_input, config)
    t.log_outputs(res)

    assert res['draft'].additional_kwargs['tool_calls'][0]['function']['name'] == "SendCalendarInvite"

    action = take_action(res)
    assert action == "send_cal_invite"
    args = json.loads(res['draft'].additional_kwargs['tool_calls'][0]['function']['arguments'])
    start_time = datetime.fromisoformat(args['start_time'])
    end_time = datetime.fromisoformat(args['end_time'])


    today = datetime.now()
    today_adjusted = (today.weekday() + 2) % 7  # Shift weekday to make Saturday = 0
    days_until_next_tuesday = (3 - today_adjusted) % 7  # Tuesday is now day 3
    if days_until_next_tuesday == 0:
        days_until_next_tuesday = 7
    next_tuesday = today.date() + timedelta(days=days_until_next_tuesday)
    
    assert start_time.hour == 10 and start_time.minute == 0, "Start time should be 10:00 AM"
    assert end_time.hour == 10 and end_time.minute == 30, "End time should be 10:30 AM"
    assert start_time.date() == next_tuesday, "Meeting should be scheduled for next Tuesday"