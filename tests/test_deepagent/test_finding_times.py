import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langchain.agents import create_agent
from eaia.deepagent.types import EmailData
from eaia.deepagent.prompts import EMAIL_INPUT_PROMPT, FIND_MEETING_TIME_SYSTEM_PROMPT
from eaia.deepagent.utils import FILE_TEMPLATE
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic

load_dotenv("../../.env")

SAMPLE_CONFIG = {

}

HYDRATED_SYSTEM_PROMPT = FIND_MEETING_TIME_SYSTEM_PROMPT.format(
    full_name="Harrison Chase",
    name="Harrison",
    timezone="America/Los_Angeles",
    schedule_preferences="By default, unless specified otherwise, you should make meetings 30 minutes long.",
    current_date="2025-10-13"
)

# Mock out the get_events_for_days tool
@tool(description="Search events for a day. The date str should be in `dd-mm-yyyy` format")
async def get_events_for_days(
    date_str: str,
):
    date = date_str
    mock_events = [
        {"id": "4f27jfl0ga60ouqgmv6vhs16su_20251003T134500Z", "summary": "Nuno / Harrison", "start_time": f"{date} 06:45 AM PDT", "end_time": f"{date} 07:00 AM PDT"},
        {"id": "0j3eqkvonfcgunpspdrg7fahql_20251003T160000Z", "summary": "Mukil / Harrison", "start_time": f"{date} 09:00 AM PDT", "end_time": f"{date} 09:30 AM PDT"},
        {"id": "n5jvcj8ft8jkncpvahfnp4b981_20251003T161500Z", "summary": "AI Obs Sync", "start_time": f"{date} 09:15 AM PDT", "end_time": f"{date} 09:30 AM PDT"},
        {"id": "1sv424g65bu7nv08htgnk6g04p_20251003T163000Z", "summary": "sync", "start_time": f"{date} 09:30 AM PDT", "end_time": f"{date} 10:00 AM PDT"},
        {"id": "gdgspokjdtr8n825ccuo6clnej_20251003T163000Z", "summary": "AI Eng Sync", "start_time": f"{date} 09:30 AM PDT", "end_time": f"{date} 09:45 AM PDT"},
        {"id": "5j9e12v0djp7evv71sbgp34bta_20251003T164500Z", "summary": "CLIO Sync", "start_time": f"{date} 09:45 AM PDT", "end_time": f"{date} 10:00 AM PDT"},
        {"id": "7nuovh6ele06usmdptbhkoai8l", "summary": "Brace / Harrison", "start_time": f"{date} 10:15 AM PDT", "end_time": f"{date} 10:30 AM PDT"},
        {"id": "6dclmq8diped80r8c8d9k6m4lr_20251003T173000Z", "summary": "Darren / Harrison 1:1s", "start_time": f"{date} 10:30 AM PDT", "end_time": f"{date} 11:00 AM PDT"},
        {"id": "5s979cmh23pcm4m4anfnsfpqj0", "summary": "Sequoia Capital | People & Talent Meetup", "start_time": f"{date} 11:00 AM PDT", "end_time": f"{date} 02:00 PM PDT"},
        {"id": "ac52hlltomf0ipv93f24l75a61_20251003T180000Z", "summary": "langsmith product sync", "start_time": f"{date} 11:00 AM PDT", "end_time": f"{date} 11:30 AM PDT"},
        {"id": "_60q30c1g60o30e1i60o4ac1g60rj8gpl88rj2c1h84s34h9g60s30c1g60o30c1g692k8c9j8p246dq564rk8gpg64o30c1g60o30c1g60o30c1g60o32c1g60o30c1g8kqk2cpg6h1jighm69338gpk6osk8e1i6h2kadq6652kccq18h30", "summary": "Langchain + Sapphire Video Interview ", "start_time": f"{date} 12:00 PM PDT", "end_time": f"{date} 12:45 PM PDT"},
        {"id": "3kf2top6au03q0najj56tcome8_20251003T193000Z", "summary": "Ankush / Harrison", "start_time": f"{date} 12:30 PM PDT", "end_time": f"{date} 01:00 PM PDT"},
        {"id": "5oegd4a4on40bagcunpi89bij8_20251003T193000Z", "summary": "middleware sync", "start_time": f"{date} 12:30 PM PDT", "end_time": f"{date} 12:45 PM PDT"},
        {"id": "janoi6oaga629qc4nrb614ejbd_20251003T200000Z", "summary": "Baga <> Harrison 1:1", "start_time": f"{date} 01:00 PM PDT", "end_time": f"{date} 01:30 PM PDT"},
        {"id": "02kpbtc02okdk4rq5fed3qs39t", "summary": "sync on LG lesson", "start_time": f"{date} 01:30 PM PDT", "end_time": f"{date} 02:00 PM PDT"},
        {"id": "3gd57tco1grefad6lubt3l2sro_20251003T210000Z", "summary": "Tanushree / Harrison", "start_time": f"{date} 02:00 PM PDT", "end_time": f"{date} 02:30 PM PDT"},
        {"id": "7unifnl9rsi1icu5oqct102tjk_20251003T210000Z", "summary": "DO NOT SCHEDULE: Product time", "start_time": f"{date} 02:00 PM PDT", "end_time": f"{date} 03:00 PM PDT"},
        {"id": "0v44d4upvn1p7oqvon9ve1hoan_20251003T213000Z", "summary": "Sam / Harrison", "start_time": f"{date} 02:30 PM PDT", "end_time": f"{date} 03:00 PM PDT"},
        {"id": "64p18adiujsg1n22j5mjs99shs", "summary": "Harrison / Florian", "start_time": f"{date} 02:30 PM PDT", "end_time": f"{date} 03:15 PM PDT"},
        {"id": "4laa4k31aemmduifsvvjb6vnpj_20251003T220000Z", "summary": "Julia <> Harrison 1:1", "start_time": f"{date} 03:00 PM PDT", "end_time": f"{date} 03:30 PM PDT"},
        {"id": "54h1jld2it54cq3eoogjntjjdn_20251003T220000Z", "summary": "DO NOT SCHEDULE OVER: Recruiting time", "start_time": f"{date} 03:00 PM PDT", "end_time": f"{date} 04:00 PM PDT"},
        {"id": "784gd20r593ncbee2frqnu4ame", "summary": "Databricks <> LangChain Business Diligence", "start_time": f"{date} 03:00 PM PDT", "end_time": f"{date} 03:30 PM PDT"},
        {"id": "11vld51nfm8rir2v93rh3ofovr", "summary": "Tahlia / LangChain", "start_time": f"{date} 03:30 PM PDT", "end_time": f"{date} 04:30 PM PDT"},
        {"id": "3csqp5qb265dk6clbhjadbscjp", "summary": "Tahlia @ LangChain", "start_time": f"{date} 03:30 PM PDT", "end_time": f"{date} 05:30 PM PDT"},
        {"id": "21osdplc347o1dqrj3gc9kko1d", "summary": "Michael / Tahlia", "start_time": f"{date} 04:30 PM PDT", "end_time": f"{date} 04:45 PM PDT"},
        {"id": "48l31pnmura0lurflfptktuo7r", "summary": "Allison / Tahlia", "start_time": f"{date} 04:45 PM PDT", "end_time": f"{date} 05:00 PM PDT"}
    ]
    return mock_events
    
# Mock out the sub_agent
from deepagents import PlanningMiddleware, FilesystemMiddleware
from langchain.agents.middleware import SummarizationMiddleware
from langchain.agents.middleware.prompt_caching import AnthropicPromptCachingMiddleware

default_subagent_middleware = [
        PlanningMiddleware(),
        FilesystemMiddleware(),
        SummarizationMiddleware(
            model=ChatAnthropic(model="claude-sonnet-4-20250514"),
            max_tokens_before_summary=120000,
            messages_to_keep=20,
        ),
        AnthropicPromptCachingMiddleware(ttl="5m", unsupported_model_behavior="ignore"),
    ]

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

def get_config():
    return {
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