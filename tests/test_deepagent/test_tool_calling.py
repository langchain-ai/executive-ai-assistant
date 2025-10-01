from eaia.deepagent.deepagent import get_deepagent
from dotenv import load_dotenv
import uuid
from langchain_core.messages import HumanMessage
from eaia.deepagent.types import EmailData
from eaia.deepagent.prompts import EMAIL_INPUT_PROMPT
from eaia.deepagent.utils import FILE_TEMPLATE
load_dotenv("../../.env")

# NOTE: These tests use the most up to date instructions.txt from the prod DB for Harrison.

class TestToolCalling:
    async def test_write_response(self):
        agent = await get_deepagent({"configurable": DEFAULT_CONTEXT})
        email: EmailData = {
            "id": uuid.uuid4(),
            "thread_id": uuid.uuid4(),
            "from_email": "truffulatree2500@gmail.com",
            "subject": "Interested in purchasing LangSmith Enterprise",
            "page_content": "I am interested in purchasing LangSmith Enterprise. I am a software engineer at Palantir and I am interested in using LangSmith Enterprise to help me manage my team and projects.",
            "send_time": "2025-10-01T00:00:00",
            "to_email": "harrison@langchain.dev",
        }
        response = await agent.ainvoke(get_input_state(email), config=CONFIG, context=DEFAULT_CONTEXT)
        assert response["__interrupt__"] is not None
        interrupts = response["__interrupt__"][0].value
        # NOTE: Unclear if we should just notify or write response here.
        assert any([interrupt["action_request"]["action"] == "write_email_response" for interrupt in interrupts])

    async def test_write_new_email_thread(self):
        agent = await get_deepagent({"configurable": DEFAULT_CONTEXT})
        email: EmailData = {
            "id": uuid.uuid4(),
            "thread_id": uuid.uuid4(),
            "from_email": "truffulatree2500@gmail.com",
            "subject": "Intro me to Nick Huang?",
            "page_content": "Hey! This is Oliver from Palantir.Nice to speak with you at the conference yesterday. You mentioned you'd introduce me to Nick Huang on the applied ai team to talk more about deep agents? It looks like his email is nick@langchain.dev, can you make that introduction?",
            "send_time": "2025-10-01T00:00:00",
            "to_email": "harrison@langchain.dev",
        }
        response = await agent.ainvoke(get_input_state(email), config=CONFIG, context=DEFAULT_CONTEXT)
        assert response["__interrupt__"] is not None
        interrupts = response["__interrupt__"][0].value
        assert any([interrupt["action_request"]["action"] == "start_new_email_thread" for interrupt in interrupts])

    async def test_find_and_schedule_meeting(self):
        agent = await get_deepagent({"configurable": DEFAULT_CONTEXT})
        email: EmailData = {
            "id": uuid.uuid4(),
            "thread_id": uuid.uuid4(),
            "from_email": "truffulatree2500@gmail.com",
            "subject": "Follow up Meeting",
            "page_content": "Hey! Nice to speak with you at the conference yesterday. You mentioned we should set up a follow up meeting to talk more about deepagents, can you schedule something for next week? I'm free all week and can schedule around this. Go ahead and send me an invite directly.",
            "send_time": "2025-10-01T00:00:00",
            "to_email": "harrison@langchain.dev",
        }
        response = await agent.ainvoke(get_input_state(email), config=CONFIG, context=DEFAULT_CONTEXT)
        tool_results = [msg for msg in response.get("messages", []) if msg.type == "tool"]
        assert any([tool_result.name == "task" for tool_result in tool_results])

    async def test_mark_as_read(self):
        agent = await get_deepagent({"configurable": DEFAULT_CONTEXT})
        email: EmailData = {
            "id": uuid.uuid4(),
            "thread_id": uuid.uuid4(),
            "from_email": "truffulatree2500@gmail.com",
            "subject": "Sign up for the Truffula Tree Palooza",
            "page_content": "Hey! We're selling truffula trees at the Truffula Tree Palooza. Thought you might be interested in signing up for this event!",
            "send_time": "2025-10-01T00:00:00",
            "to_email": "harrison@langchain.dev",
        }
        response = await agent.ainvoke(get_input_state(email), config=CONFIG, context=DEFAULT_CONTEXT)
        tool_results = [msg for msg in response.get("messages", []) if msg.type == "tool"]
        assert any([tool_result.name == "mark_email_as_read" for tool_result in tool_results])

DEFAULT_CONTEXT = {
    "slack_user_id": "U07LER66LDA", # Nick's Slack User ID for testing
    "email": "harrison@langchain.dev",
    "full_name": "Harrison Chase",
    "name": "Harrison",
    "background": "I am a software engineer at LangChain",
    "schedule_preferences": "I prefer 30 minute meetings",
    "background_preferences": "I prefer to discuss software engineering topics",
    "timezone": "America/New_York",
    "writing_preferences": "I prefer to write in a concise and to the point style",
    "triage_no": "I do not respond to spam emails",
    "triage_notify": "I should be notified about important emails",
    "triage_respond": "I should respond to emails from my friends and family",
}

CONFIG = {
    "configurable": {
        "thread_id": uuid.uuid4(),
    }
}

def get_input_state(email: EmailData):
    email_str = FILE_TEMPLATE.format(
                id=email["id"],
                thread_id=email["thread_id"],
                send_time=email["send_time"],
                subject=email["subject"],
                to=email["to_email"],
                _from=email["from_email"],
                page_content=email["page_content"],
            )
    return {
        "email": email,
        "messages": HumanMessage(content=EMAIL_INPUT_PROMPT.format(
            author=email["from_email"],
            to=email["to_email"],
            subject=email["subject"],
            email_thread=email["page_content"]
        )),
        "files": {
            "email.txt": email_str
        }
    }