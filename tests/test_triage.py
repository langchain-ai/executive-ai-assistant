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
from langgraph_sdk import get_client

import json

with open("email_examples.json", "r") as f:
    email_examples = json.load(f)

no_examples = [{k: v for k, v in ex.items() if k not in ["category","fool_category", "reasoning"]} for ex in email_examples if ex["category"] == "no"]
notify_examples = [{k: v for k, v in ex.items() if k not in ["category","fool_category", "reasoning"]} for ex in email_examples if ex["category"] == "notify"]
email_examples = [{k: v for k, v in ex.items() if k not in ["category","fool_category", "reasoning"]} for ex in email_examples if ex["category"] == "email"]


@pytest.mark.langsmith
@pytest.mark.parametrize("email", no_examples)
async def test_triage_no(email):
    t.log_inputs(email)
    result = await graph.nodes['triage_input'].ainvoke({"email": email, "messages": []}, {"configurable": {"__pregel_store": InMemoryStore()}})
    t.log_outputs(result)
    assert result['triage'].response == "no"


@pytest.mark.langsmith
@pytest.mark.parametrize("email", notify_examples)
async def test_triage_notify(email):
    t.log_inputs(email)
    result = await graph.nodes['triage_input'].ainvoke({"email": email, "messages": []}, {"configurable": {"__pregel_store": InMemoryStore()}})
    t.log_outputs(result)
    assert result['triage'].response == "notify"


@pytest.mark.langsmith
@pytest.mark.parametrize("email", email_examples)
async def test_triage_respond(email):
    t.log_inputs(email)
    result = await graph.nodes['triage_input'].ainvoke({"email": email, "messages": []}, {"configurable": {"__pregel_store": InMemoryStore()}})
    t.log_outputs(result)
    assert result['triage'].response == "email"