from typing import Annotated, List, Literal
from pydantic import BaseModel, Field
from langgraph.graph.message import AnyMessage
from typing_extensions import TypedDict


from langgraph.graph import add_messages


class EmailData(TypedDict):
    id: str
    thread_id: str
    from_email: str
    subject: str
    page_content: str
    send_time: str
    to_email: str


class RespondTo(BaseModel):
    logic: str = Field(
        description="logic on WHY the response choice is the way it is", default=""
    )
    response: Literal["no", "email", "notify", "question"] = "no"


class ResponseEmailDraft(BaseModel):
    """Draft of an email to send as a response."""

    content: str
    new_recipients: List[str]


class NewEmailDraft(BaseModel):
    """Draft of a new email to send."""

    content: str
    recipients: List[str]


class ReWriteEmail(BaseModel):
    """Logic for rewriting an email"""

    tone_logic: str = Field(
        description="Logic for what the tone of the rewritten email should be"
    )
    rewritten_content: str = Field(description="Content rewritten with the new tone")


class Question(BaseModel):
    """Question to ask user."""

    content: str


class Ignore(BaseModel):
    """Call this to ignore the email. Only call this if user has said to do so."""

    ignore: bool


class MeetingAssistant(BaseModel):
    """Call this to have user's meeting assistant look at it."""

    call: bool


class SendCalendarInvite(BaseModel):
    """Call this to send a calendar invite."""

    emails: List[str] = Field(
        description="List of emails to send the calendar invitation for. Do NOT make any emails up!"
    )
    title: str = Field(description="Name of the meeting")
    start_time: str = Field(
        description="Start time for the meeting, should be in `2024-07-01T14:00:00` format"
    )
    end_time: str = Field(
        description="End time for the meeting, should be in `2024-07-01T14:00:00` format"
    )


# Needed to mix Pydantic with TypedDict
def convert_obj(o, m):
    if isinstance(m, dict):
        return RespondTo(**m)
    else:
        return m


class State(TypedDict):
    email: EmailData
    triage: Annotated[RespondTo, convert_obj]
    messages: Annotated[List[AnyMessage], add_messages]


email_template = """From: {author}
To: {to}
Subject: {subject}

{email_thread}"""
