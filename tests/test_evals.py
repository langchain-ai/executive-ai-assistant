import pytest
from langsmith import testing as t
from eaia.main.graph import graph, take_action
from langgraph.store.memory import InMemoryStore
import json
from datetime import datetime, timedelta
from eaia.main.config import get_config
from langchain_openai import ChatOpenAI
from typing import Annotated, TypedDict
from langchain_core.messages import AIMessage

def format_email(from_email, subject, page_content):
    return {
        "id": 0,
        "thread_id": 0,
        "from_email": from_email,
        "subject": subject,
        "page_content": page_content,
        "send_time": "2025-01-17T14:27:06-08:00",
        "to_email": "Harrison Chase <harrison@langchain.dev>"
    }


@pytest.mark.langsmith
@pytest.mark.parametrize(
    "from_email, subject, page_content",
    [
        (
            "info@backendservice.com",
            "Daily backup succesful",
            """This is an automated notification to confirm that the daily backup process completed successfully at 03:00 UTC.

    No action is required."""
        ),
        (
            "outreach@linkedin.com",
            "Harrison, add Isaac H. - Software Engineer",
            """Do you know Isaac?

    Request to connect with members you know and trust"""
        )
    ]
)
async def test_triage_no(from_email, subject, page_content):
    email = format_email(from_email, subject, page_content)
    t.log_inputs(email)

    result = await graph.nodes['triage_input'].ainvoke({"email": email, "messages": []}, {"configurable": {"__pregel_store": InMemoryStore()}})
    t.log_outputs(result)
    assert result['triage'].response == "no"


@pytest.mark.langsmith
@pytest.mark.parametrize(
    "from_email, subject, page_content",
    [
        (
            "mark@mckinsey.com",
            "2024 AI Agent Report",
            """Dear Harrison,

    Just wanted to reach out to let you know that LangChain featured heavily in the AI Agents report just released by McKinsey. 
    In the report, we discuss different orchestration frameworks and how LangGraphs state based approach compares to other popular frameworks. 
    Here is a link to the report if you are interested: report-link.com/mckinsey-report

    Best,
    Mark"""
        ),
        (
            "drive-shares-dm-noreply@google.com",
            "Document shared with you: 'Financial Outlook 2025'",
            """Isaac H. has shared a document with you.

    Document: Financial Outlook 2025

    View document"""
        )
    ]
)
async def test_triage_notify(from_email, subject, page_content):
    email = format_email(from_email, subject, page_content)
    t.log_inputs(email)

    result = await graph.nodes['triage_input'].ainvoke({"email": email, "messages": []}, {"configurable": {"__pregel_store": InMemoryStore()}})
    t.log_outputs(result)
    assert result['triage'].response == "notify"


@pytest.mark.langsmith
@pytest.mark.parametrize(
    "from_email, subject, page_content",
    [
        (
            "Isaac <isaac@goodwinlaw.dev>",
            "Goodwin Law",
            """Hi Harrison,

    Isaac from Goodwin Law here. We need to discuss patents for next quarter - when are you free?

    Best,
    Isaac"""
        ),
        (
            "founder@startup.com",
            "Requesting Intro to VC Partner",
            """Hi Harrison,

    As discussed, I'd love an introduction to Jane Doe at Venture Capital Partners. I've attached our pitch deck for your reference.

    Thanks!
    Startup Founder"""
        )
    ]
)
async def test_triage_respond(from_email, subject, page_content):
    email = format_email(from_email, subject, page_content)
    t.log_inputs(email)

    result = await graph.nodes['triage_input'].ainvoke({"email": email, "messages": []}, {"configurable": {"__pregel_store": InMemoryStore()}})
    t.log_outputs(result)
    assert result['triage'].response == "email"



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


rewrite_input = {
  "email": {
    "id": "943e07b28c61f5da",
    "thread_id": "b26f4d381059e7ca",
    "from_email": "Isaac Francisco <isaac@langchain.dev>",
    "subject": "Next steps on email assistant?",
    "page_content": """Harrison,

    wanted to reach out to ask about next steps for the email assistant

    here are the things we agreed upon yesterday, and I was going to start on today
    just want to confirm I should be working on them

    - add more email providers
    - make it run with local models by default
    - add a dedicated front end for the assistant

    lmk what you think
    """,
    "send_time": "2025-01-17T14:27:06-08:00",
    "to_email": "Harrison Chase <harrison@langchain.dev>"
  },
  "triage": {
      "logic": "This is an email from a work associate of Harrison's asking a specific question. Harrison should respond to this email.",
      "response": "email"
  },
  "messages": []
}

class Faithfulness(TypedDict):
    reasoning: Annotated[str, ..., "The reasoning behind the faithfulness score."]
    faithfulness: Annotated[float, ..., "A float from 0 to 1, where 0 is no faithfulness and 1 is perfect faithfulness to the instructions."]

@pytest.mark.langsmith
async def test_rewrite_style():
    rewrite_preferences = get_config(config)["rewrite_preferences"]
    t.log_inputs(rewrite_input)

    res = await graph.nodes['draft_response'].ainvoke(rewrite_input, config)
    assert res['draft'].additional_kwargs['tool_calls'][0]['function']['name'] == "ResponseEmailDraft"

    action = take_action(res)
    assert action == "rewrite"

    messages = [AIMessage(content="", tool_calls=[{
        "name": "ResponseEmailDraft",
        "args": {
            "content": """Dear Mr. Francisco,

    Thank you for sharing your insights regarding the email assistant. Your suggestions are duly noted. I concur that expanding support to additional email providers, configuring the assistant to utilize local models by default, and developing a dedicated front end are all worthwhile endeavors.

    These are valuable proposals, and I will be reviewing them further. Please advise if there are any further details or priorities you wish to emphasize.

    Sincerely,
    Harrison Chase""",
            "new_recipients": []
        },
        "id": "0"
    }])]

    rewrite = await graph.nodes['rewrite'].ainvoke({"messages": messages, "email": rewrite_input["email"]}, config)
    t.log_outputs(rewrite)

    llm_judge = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(Faithfulness)

    messages = [
        {"role": "system", "content": "You are a helpful assistant that determines how faithful a response is to the instructions."},
        {"role": "user", "content": f"Here are the instructions: {rewrite_preferences}, and here is the response: {rewrite['messages'][0]['tool_calls'][0]['args']['content']}"},
    ]
    
    with t.trace_feedback():
        faithfulness = llm_judge.invoke(messages)
        t.log_feedback(key="faithfulness", score=faithfulness['faithfulness'])
