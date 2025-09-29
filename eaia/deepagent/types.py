from langchain.agents.middleware import AgentState
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class EmailData(TypedDict):
    id: str
    thread_id: str
    from_email: str
    subject: str
    page_content: str
    send_time: str
    to_email: str

class EmailAgentState(AgentState):
    email: EmailData

class NotifiedState(AgentState):
    notified: bool = False

class EmailConfigSchema(BaseModel):
    email: str = Field(description="Your email address", default="")
    slack_user_id: str = Field(description="Your Slack user ID", default="")
    full_name: str = Field(description="Your full name", default="")
    name: str = Field(description="Your first name", default="")
    background: str = Field(description="A brief description of your personal background", default="")
    schedule_preferences: str = Field(description="Your preferences for scheduling meetings, ex. how long they should be", default="")
    background_preferences: str = Field(description="Other preferences to keep in mind when responding to emails", default="")
    timezone: str = Field(description="Your timezone, ex. America/New_York", default="")
    writing_preferences: str = Field(description="Your preferences for how your emails should be written", default="")
    triage_no: str = Field(description="A string description of types of emails that you should NOT respond to", default="")
    triage_notify: str = Field(description="A string description of types of emails that you should be notified about", default="")
    triage_respond: str = Field(description="A string description of types of emails that you SHOULD respond to", default="")