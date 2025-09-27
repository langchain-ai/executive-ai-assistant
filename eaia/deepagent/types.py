from langchain.agents.middleware import AgentState
from typing_extensions import TypedDict

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