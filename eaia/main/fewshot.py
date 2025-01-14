"""Fetches few shot examples for triage step."""

from langgraph.store.base import BaseStore
from eaia.schemas import EmailData


template = """Email Subject: {subject}
Email From: {from_email}
Email To: {to_email}
Email Content: 
```
{content}
```
> Triage Result: {result}"""


def format_similar_examples_store(examples):
    strs = ["Here are some previous examples:"]
    for eg in examples:
        strs.append(
            template.format(
                subject=eg.value["input"]["subject"],
                to_email=eg.value["input"]["to_email"],
                from_email=eg.value["input"]["from_email"],
                content=eg.value["input"]["page_content"][:400],
                result=eg.value["triage"],
            )
        )
    return "\n\n------------\n\n".join(strs)


async def get_few_shot_examples(email: EmailData, store: BaseStore, config):
    namespace = (
        config["configurable"]["langgraph_auth_user_id"],
        config["configurable"]["assistant_id"],
        "triage_examples",
    )
    result = await store.asearch(namespace, query=str({"input": email}), limit=5)
    if result is None:
        return ""
    return format_similar_examples_store(result)
