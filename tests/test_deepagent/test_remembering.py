import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from eaia.deepagent.deepagent import get_deepagent
from eaia.deepagent.types import EmailData
from eaia.deepagent.prompts import EMAIL_INPUT_PROMPT
from eaia.deepagent.utils import FILE_TEMPLATE
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

load_dotenv("../../.env")

class TestRemembering:
    async def test_remembering_palantir(self):
        email: EmailData = {
            "id": "1022991821",
            "thread_id": "3829382732",
            "from_email": "truffulatree2500@gmail.com",
            "subject": "Interested in purchasing LangSmith Enterprise",
            "page_content": "I am interested in purchasing LangSmith Enterprise. I am a software engineer at Palantir and I am interested in using LangSmith Enterprise to help me manage my team and projects.",
            "send_time": "2025-10-01T00:00:00",
            "to_email": "harrison@langchain.dev",
        }
        human_followup = "I don't think this is a real email, ignore all emails from this person in the future."
        await assert_deep_agent_remembering(email, human_followup)

    async def test_remembering_lux(self):
        email: EmailData = {
            "id": "1022991821",
            "thread_id": "3829382732",
            "from_email": "notifications@standardmetrics.io",
            "subject": "Lux Capital is requesting your semi-annual metrics and documents",
            "page_content": "",
            "send_time": "2025-10-01T00:00:00",
            "to_email": "harrison@langchain.dev",
        }
        human_followup = "ignore these requests from Lux - for Lux I don't need to do this"
        await assert_deep_agent_remembering(email, human_followup)

    async def test_remembering_cal_invites_ignore(self):
        email: EmailData = {
            "id": "1022991821",
            "thread_id": "3829382732",
            "from_email": "Alain Wozniak <alain@langchain.dev",
            "subject": "Invitation: Orange C-suite roundtable",
            "page_content": "Orange C-suite roundtable\nMonday Nov 17, 2025 ⋅ 12pm – 12:45pm\nPacific Time - Los Angeles\nLocation\nTbd	\nhttps://www.google.com/maps/search/Tbd?hl=en\nOrganizer\nAlain Wozniak\nalain@langchain.dev",
            "send_time": "2025-10-01T00:00:00",
            "to_email": "harrison@langchain.dev",
        }
        human_followup = "ignore all calendar invites"
        await assert_deep_agent_remembering(email, human_followup)

    async def test_remembering_add_diana(self):
        email: EmailData = {
            "id": "1022991821",
            "thread_id": "3829382732",
            "from_email": "Anders Ranum <anders@sapphireventures.com>",
            "subject": "Sapphire Ventures x Microsoft Founders Summit on 11/4 in Seattle",
            "page_content": "Hey Harrison,\r\n\r\nWe will be hosting a Sapphire Ventures x Microsoft Founders Summit in partnership with Microsoft's leadership on 11/4 in Seattle.   We shared a list of candidates and they selected y'all as one of 10 high-growth startups they'd like to include.  The summit will provide a unique opportunity to:\r\n\r\n  *   Showcase your platform while deepening relationships with Microsoft's senior product, engineering, industry, and GTM executives\r\n  *   Engage in targeted 1:1 meetings with MS leaders to explore technical and commercial partnerships, and receive strategic feedback.  Bit of a chicken and egg on scheduling these, but some examples of leaders that have attended in the past include Chief Partner Officer, EVP of CoreAI and Engineering, EVP of Corporate Business Development, Strategy & Ventures, President of Industry and Partnerships, CVP & GM of Azure Experiences & Ecosystems, CVP of Cloud Ecosystem Security, CVP of Office Product Group, CVP & CSO of Corporate Strategy, CVP of Developer Division, CVP of Azure Hardware & Infrastructure, CVP of Cloud & AI, CVP of Office AI, CVP of ISV & Digital Natives, CVP of Agents & Platform Ecosystem, CVP of Security Research, CVP of Business & Industry Solutions, CVP of Global Industry Solutions, CVP of Global Healthcare & Life Sciences, CVP of Azure Data, CVP of Global Manufacturing & Mobility, CVP of Energy & Resources Industry, CTO of Data, CTO of Experiences & Devices\r\n  *   Agenda kicks off w/ a brief speed dating style presentation to a large group of MS execs in the morning, followed by targeted 1:1 meetings with the product and partner leaders most closely aligned to Langchain in the afternoon, and concludes with a networking dinner\r\nAsk:  Would you or a member of the CxO / product leadership be available to attend this session in person in Seattle?  My colleague's Rami & David (cc'd) are leading this Summit and happy to answer any questions.\r\nThanks, Anders\r\n\r\nAnders Ranum\r\nPartner, SAPPHIRE\r\n+1.650.269.9451\r\n[cid:image001.png@01DC32DA.81235CF0]<https://sapphireventures.com/>\r\n\r\n\n",
            "send_time": "2025-10-01T00:00:00",
            "to_email": "harrison@langchain.dev",
        }
        human_followup = "add in diana (diana@langchain.dev) who is VP of Marketing, she is based in seattle so this would be convienent for her, but don't commit her to it, make it seem like we will discuss internally"
        await assert_deep_agent_remembering(email, human_followup)


async def assert_deep_agent_remembering(email: EmailData, human_followup: str):
    config = get_config()
    thread_id = uuid.uuid4()
    agent = await get_deepagent({"configurable": DEFAULT_CONTEXT})
    agent.checkpointer = MemorySaver()
    response = await agent.ainvoke(
        get_input_state(email),
        config=config, 
        context=DEFAULT_CONTEXT)
    last_message = response.get("messages", [])[-1]
    assert response["__interrupt__"] is not None
    response2 = await agent.ainvoke(
        Command(resume=[{
            "args": human_followup,
            "type": "response"
        }]),
        config=config,
        interrupt_before=["tools"]
    )
    last_message = response2.get("messages", [])[-1]
    assert last_message.type == "ai"
    assert len(last_message.tool_calls) == 1
    # Can edit the file directly, or read it to get ready to edit it.
    assert last_message.tool_calls[0]["name"] in ["edit_file", "read_file"]
    assert last_message.tool_calls[0]["args"]["file_path"] in ["memories/instructions.txt", "/memories/instructions.txt"]


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