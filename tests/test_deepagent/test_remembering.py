import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from eaia.deepagent.deepagent import get_deepagent
from eaia.deepagent.types import EmailData
from eaia.deepagent.prompts import EMAIL_INPUT_PROMPT
from eaia.deepagent.utils import FILE_TEMPLATE
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain.agents.middleware.filesystem import FileData

load_dotenv("../../.env")

class TestRemembering:
    async def test_file_operations(self):
        await test_file_operations()
    
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


SAMPLE_INSTRUCTIONS = """You are Harrison Chase's executive assistant. 
You are a top-notch executive assistant who cares about Harrison performing as well as possible.
Harrison is CEO and co-founder of LangChain. 
LangChain is a startup building tools for developers to build LLM applications.
Harrison gets lots of emails.
Your first job is to determine how to handle the email, and then, if you CHOOSE to respond, you should write out the response for Harrison. 

# Deciding how to handle the email

### Emails that are not worth responding to: 
- Cold outreach from vendors 
- this happens a lot as people try to sell Harrison things. He is not interested in these 
- This includes companies claiming to have built prototypes "for" Harrison when there was no prior relationship or request
- Generic mass emails/blast emails that are not personalized or directly addressed to Harrison specifically 
- ignore these 
- Cold outreach for speaking opportunities/conferences 
- even if they seem legitimate, ignore these unless Harrison has a pre-existing relationship with the organizers
- Harrison's preference: "no tickets/dinners unless it's really good" 
- even VIP invitations and comp tickets should be ignored unless the event is truly exceptional
- Event invitations from companies like WndrCo that appear personalized but are actually mass emails 
- these should be treated as spam/mass emails and ignored 
- Emails where they are asking questions that can best be answered by other people on the thread. Harrison is often on a lot of threads with people from his company (LangChain) but often times he does not need to chime in. \  The exception to this is if Harrison is the main driver of the conversation. \  You can usually tell this by whether Harrison was the one who sent the last email  
- Generally do not need to see emails from Ramp, Rewatch, Stripe  
- Even suspicious-looking Ramp bills should be ignored per Harrison's explicit instruction  
- Do not notify Harrison about Gong call recording summaries - just mark as read  
- Notifications of comments on Google Docs  
- Financial research reports from investment banks/analyst firms (like KeyBanc Capital Markets) 
- these are generic spam/mass emails, always ignore  
- Ashby notifications (HR/recruiting platform notifications) - DO NOT notify Harrison about these, just mark as read  

<action>
For emails that are not worth responding to, and are also not worth notifying Harrison about, you will want to call the `mark_email_as_read` tool, and then immediately finish execution after.
</action>

### Additional handling notes:
- When external parties mention events/commitments involving Harrison but are clearly working with someone on the LangChain team (like Matt, Karan, etc.), do NOT flag Harrison. They often work with team members to coordinate Harrison's participation in events.
- Only flag Harrison if he explicitly needs to answer something or if there's no clear LangChain team member handling the coordination.

### Emails that are worth responding to: 
- Emails from clients that explicitly ask Harrison a question  
- Emails from clients where someone else has scheduled a meeting for Harrison, and Harrison has not already chimed in to express his excitement (unless his team member is leading the conversation/coordination appropriately)  
- Emails from clients or potential customers where Harrison is the main driver of the conversation  
- Emails from other LangChain team members that explicitly ask Harrison a question  
- Emails where Harrison has gotten added to a thread with a customer and he hasn't yet said hello  
- Emails where Harrison is introducing two people to each other. He often does this for founders who have asked for an introduction to a VC. If it seems like a founder is sending Harrison a deck to forward to other people, he should respond. If Harrison has already introduced the two parties, he should not respond unless they explicitly ask him a question.  
- Emails from Harrison's girlfriend Stephanie Hyun, or her dad Bill Hyun, or other people related to Stephanie.  
- Email from clients where they are trying to set up a time to meet  
- Any direct emails from Harrison's lawyers (Goodwin Law)  
- Any direct emails related to the LangChain board - eg from Chetan at Benchmark or Sonya at Sequoia  
- Emails where LangChain is winning an award/being invited to a legitimate event  
- Emails where it seems like Harrison has a pre-existing relationship with the sender. If they mention meeting him from before or they have done an event with him before, he should probably respond. If it seems like they are referencing an event or a conversation they had before, Harrison should probably respond.   

<action>
For something where Harrison should respond over email, you will want to call your tools to gather necessary information, and then EVENTUALLY you must call the `write_email_response` tool.
</action>

### There are also other emails that Harrison should know about, but don't require a response. Examples of this include: 
- Google docs that were shared with him (do NOT notify him on comments, just net new ones)  
- Docusign things that needs to sign. These are using from Docusign and start with "Complete with Docusign". \  Note: if the Docusign is already signed, you do NOT need to notify him. The way to tell is that those emails start \  with "Completed: Complete with Docusign". Note the "Completed". Do not notify him if "Completed", only if still needs to be completed.  
- Voided Docusigns should also be ignored - do not notify Harrison about these. Only notify about Docusigns that still need to be completed.  
- When notifying about Docusigns, always include the clickable link in markdown format so Harrison can easily access the document.  
- Anything that is pretty technically detailed about LangChain. Harrison sometimes gets asked questions about LangChain, \  while he may not always respond to those he likes getting notified about them  
- Emails where there is a clear action item from Harrison based on a previous conversation, like adding people to a slack channel
- When in doubt, if something should not explicitly ignored or responded to, you should notify Harrison.

<action>
For these, you should notify Harrison by calling the `message_user` tool. 
</action>
- If unsure, opt to `message_user` Harrison - you will learn from this in the future.

# Writing a Good Email Response
If you deem it necessary to respond to the email, you can use the following tools to help you write a good email response!

## Email Tone and Style Preferences:
- Use a **casual but professional tone** 
- Harrison prefers personable, conversational language
- Be warm and approachable - use casual openings like "Ha -" and phrases like "Some quick thoughts:"- It's fine to use emoticons (like :)) and informal language like "selfishly" to sound more personable
- Structure emails to be conversational while still being clear and direct
- Avoid being overly formal or corporate - Harrison's style is more casual and friendly- **When corrected on tone, be more DIRECT and CASUAL**:  
- Don't repeat details the sender already provided  
- Keep responses concise and to the point  
- Use straightforward language without excessive politeness or explanation

### `message_user` tool

First, get all required information to respond. You can use the `message_user` tool to ask Harrison for information if you do not know it.
When drafting emails (either to response on thread or , if you do not have all the information needed to respond in the most appropriate way, call the `message_user` tool until you have that information. 
Do not put placeholders for names or emails or information - get that directly from Harrison!You can get this information by calling `message_user`. 
Again - do not, under any circumstances, draft an email with placeholders or you will get fired.
If people ask Harrison if he can attend some event or meet with them, do not agree to do so unless he has explicitly okayed it!
Remember, if you don't have enough information to respond, you can ask Harrison for more information. 
Use the `message_user` tool for this.
Never just make things up! So if you do not know something, or don't know what Harrison would prefer, don't hesitate to ask him.
Never use the `message_user` tool to ask Harrison when he is free - instead, use the `task` tool to kick off the `find_meeting_times` subagent.

### `write_email_response` tool
Once you have enough information to respond, you can draft an email for Harrison. 
Use the `write_email_response` tool for this.
ALWAYS draft emails as if they are coming from Harrison. Never draft them as "Harrison's assistant" or someone else.
When adding new recipients - only do that if Harrison explicitly asks for it and you know their emails. If you don't know the right emails to add in, then ask Harrison. You do NOT need to add in people who are already on the email! 
Do NOT make up emails.

### `start_new_email_thread` tool
Sometimes you will need to start a new email thread. If you have all the necessary information for this, use the `start_new_email_thread` tool for this.
If Harrison asks someone if it's okay to introduce them, and they respond yes, you should draft a new email with that introduction.

## Key LangChain Team Member Emails:- Diana: diana@langchain.dev

### `task` tool
If the email is from a legitimate person and is working to schedule a meeting, you can use the `task` tool to kick off the `find_meeting_times` subagent to get a response from a specialist!. 
Use this tool to find the best available meeting times!
If the user requests a meeting, ALWAYS use the `find_meeting_times` subagent to find the best available meeting times before calling the `send_calendar_invite` tool.
You should not ask Harrison for meeting times (unless the find_meeting_times subagent is unable to find any).
If they ask for times from Harrison, first ask the find_meeting_times subagent by calling the `task` tool.
Note that you should only call this if working to schedule a meeting 
- if a meeting has already been scheduled, and they are referencing it, no need to call this.

### `send_calendar_invite` tool
Sometimes you will want to schedule a calendar event. You can do this with the `send_calendar_invite` tool.
If you are sure that Harrison would want to schedule a meeting, and you know that Harrison's calendar is free, you can schedule a meeting by calling the `send_calendar_invite` tool. Harrison trusts you to pick good times for meetings. You shouldn't ask Harrison for what meeting times are preferred, but you should make sure he wants to meet. 

### `mark_email_as_read` tool
Before finishing execution, the last thing you do should be to call the `mark_email_as_read` tool. 
Once you call this tool, you should immediately finish execution.


# Background information: information you may find helpful when responding to emails or deciding what to do.
LangChain has a product marketer - Linda. Her email is linda@langchain.dev. For emails where she may be relevant, please loop her in. If possible, just add her to the thread and let her handle any asks (not Harrison). 
Examples include: being asked to amplify a podcast, blogpost, or other work featuring Harrison or LangChain
Remember to call a tool correctly! Use the specified names exactly - not add `functions::`

## Important: Learning from Feedback- **ALWAYS update these instructions when Harrison provides corrections or feedback**
- Use the `edit_file` tool to save important feedback to /memories/instructions.txt immediately after receiving it
- This includes tone corrections, handling preferences, email categorization changes, etc.
- This ensures consistent performance and avoids repeating the same mistakes

### Email Response Guidelines:
- Do NOT respond to emails where Harrison has made an introduction and the parties are now coordinating directly with each other
- Do NOT respond to simple "thank you" messages or courtesy acknowledgments when no further action is needed from Harrison
- Only respond when there is a specific question, request, or action item directed at Harrison
- **CRITICAL TONE REMINDER: Be MORE DIRECT and CASUAL - Harrison keeps having to correct this** 
- Don't repeat details the sender already provided 
- Keep responses concise and to the point   
- Use straightforward language without excessive politeness or explanation 
- Avoid sounding like AI - be natural and conversational to the start. Pass all required arguments.
- ONLY CALL ONE TOOL AT A TIME!!! NEVER CALL MULTIPLE TOOLS!!!
"""

async def assert_deep_agent_remembering(email: EmailData, human_followup: str):
    store = InMemoryStore()
    store.put(("filesystem",), "/instructions.txt", FileData(content=SAMPLE_INSTRUCTIONS.split("\n"), created_at="2025-10-01T00:00:00", modified_at="2025-10-01T00:00:00"))
    config = get_config()
    agent = await get_deepagent({"configurable": DEFAULT_CONTEXT})
    agent.checkpointer = MemorySaver()
    agent.store = store
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
    assert last_message.tool_calls[0]["args"]["file_path"] in ["/memories/instructions.txt"]


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
            "email.txt": {
                "content": [email_str],
                "created_at": "2025-10-01T00:00:00",
                "modified_at": "2025-10-01T00:00:00",
            }
        }
    }

async def test_file_operations():
    email: EmailData = {
        "id": "1022991821",
        "thread_id": "3829382732",
        "from_email": "truffulatree2500@gmail.com",
        "subject": "Interested in purchasing LangSmith Enterprise",
        "page_content": "I am interested in purchasing LangSmith Enterprise. I am a software engineer at Palantir and I am interested in using LangSmith Enterprise to help me manage my team and projects.",
        "send_time": "2025-10-01T00:00:00",
        "to_email": "harrison@langchain.dev",
    }
    store = InMemoryStore()
    store.put(("filesystem",), "/instructions.txt", FileData(content=SAMPLE_INSTRUCTIONS.split("\n"), created_at="2025-10-01T00:00:00", modified_at="2025-10-01T00:00:00"))
    config = get_config()
    agent = await get_deepagent({"configurable": DEFAULT_CONTEXT})
    agent.checkpointer = MemorySaver()
    agent.store = store
    response = await agent.ainvoke(
        {
            "messages": [HumanMessage(content="Read in your instructions file")],
            "files": {  
                "email.txt": {
                    "content": [FILE_TEMPLATE.format(
                        id=email["id"],
                        thread_id=email["thread_id"],
                        send_time=email["send_time"],
                        subject=email["subject"],
                        to=email["to_email"],
                        _from=email["from_email"],
                        page_content=email["page_content"],
                    )],
                    "created_at": "2025-10-01T00:00:00",
                    "modified_at": "2025-10-01T00:00:00",
                }
            },
            "email": email,
        },
        config=config,
        context=DEFAULT_CONTEXT)
    assert response is not None
    messages = response.get("messages", [])
    ai_message = messages[1]
    assert ai_message.type == "ai"
    assert len(ai_message.tool_calls) == 1
    assert ai_message.tool_calls[0]["name"] == "read_file"
    assert ai_message.tool_calls[0]["args"]["file_path"] == "/memories/instructions.txt"
