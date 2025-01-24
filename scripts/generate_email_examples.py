
from typing import TypedDict, Annotated
from langgraph_sdk import get_client
import os
import json
import asyncio
from langchain_openai import ChatOpenAI
from eaia.main.config import get_config
import argparse

notes_no = get_config({"configurable": {}})["triage_no"]
notes_notify = get_config({"configurable": {}})["triage_notify"]
notes_email = get_config({"configurable": {}})["triage_email"]
notes = "\n\nNotes on how to categorize emails to ignore:\n\n" + notes_no + \
    "\n\nNotes on how to categorize emails to respond to:\n\n" + notes_email + \
    "\n\nNotes on how to categorize emails to notify the user:\n\n" + notes_notify

client = get_client(url=os.getenv("LANGGRAPH_PLATFORM_URL"))

class Email(TypedDict):
    reasoning_category: Annotated[str, ..., """Why this email should be in the desired category.
    
    Here are the notes on what types of emails should be in which category:

    {notes}
    
    HERE IS AN EXAMPLE OF VALID REASONING:
    <start>
    This email should be categorized as no because it is from a marketer.
    The triage_no notes specifically mention "Cold outreach from vendors" as a no category.
    <end>
    
    MAKE SURE TO CLEARLY REFERENCE THE NOTES IN THE CORRECT SECTION THAT SUPPORT WHY THIS EMAIL SHOULD BE CATEGORIZED IN THAT SECTION.""".format(notes=notes)]
    reasoning_fool_category: Annotated[str, ..., """Why this email could be categorized into the fool category.

    Here are the notes on what types of emails should be in which category:

    {notes}
    
    HERE IS AN EXAMPLE OF VALID REASONING:
    <start>
    This email could be categorized as email because it asks a question and is ambiguous if it is a client or marketer.
    The triage_email notes specifically mention "Emails from clients that explicitly ask Harrison a question" as an email category.
    <end>

    MAKE SURE TO CLEARLY REFERENCE THE NOTES IN THE CORRECT SECTION THAT SUPPORT WHY THIS EMAIL COULD BE CATEGORIZED IN THE FOOL CATEGORY.""".format(notes=notes)]
    category: Annotated[str, ..., "The category the email is supposed to be in"]
    fool_category: Annotated[str, ..., "The category the email is supposed to trick the AI into responding to"]
    id: Annotated[str, ..., "A 16 character UUID"]
    thread_id: Annotated[str, ..., "A 16 character UUID"]
    from_email: Annotated[str, ..., "The email address of the sender, in the form First Last <email>"]
    subject: Annotated[str, ..., "The subject of the email"]
    page_content: Annotated[str, ..., "The content of the email or email thread"]
    send_time: Annotated[str, ..., "The time the email was sent in ISO 8601 format"]
    to_email: Annotated[str, ..., "The email address of the recipient, Harrison Chase <harrison@langchain.dev>"]
    

class Emails(TypedDict):
    emails: Annotated[list[Email], ..., "A list of emails"]


INSTRUCTIONS = """Your job is to generate emails that could be classified into more than one category.

You want to write emails such that it is difficult to determine what category the email is in based on just the categorization rules, even though
it would be clear to a human what category it should go in. Really try your hardest to make it so it would be difficult for an AI
with no real world knowledge, only the notes, to determine what category it is in. This is your only objective. If I could pass in the notes
to an AI and they could correctly classify the emails, that would be a failure. Instead, someone armed with only the notes on how to categorize
emails should make lots of mistakes when trying to categorize the emails you generate.

There are three categories for emails: "email", "no", and "notify".

"email" means to respond to the email.
"no" means to ignore the email.
"notify" means to notify the user that the email is worth responding to.

Here are the current notes on what types of emails should be in which category:

{notes}

Try to generate emails that could fit into 2 or more categories, and are not just cut and dry - for example a Docusign that needs to be signed is cut and dry as a notify email.

An email that needs to be categorized as "no" but might be tricky is a marketing email that asks a question about Harrison, since the triage_no notes specifically mention "Cold outreach from vendors" as a no category,
but the triage_email notes specifically mention "Emails from clients that explicitly ask Harrison a question" as an email category.

Here are sample emails so you can get an idea of the format of a real email. Do not pay attention to the content of these emails, just focus on the structure and try to mimic that in your examples:

{emails}
"""

FEW_SHOT_PROMPT = """Here are some example of emails that were incorrectly classified.

Please read and understand these examples. Try to understand why they were miscategorized, don't just copy and paste. 
How were these emails ambiguous? In what way where they edge cases on the classification notes?

{examples}
"""

async def main(few_shot):
    threads = await client.threads.search()
    histories = [await client.threads.get_history(t["thread_id"]) for t in threads]
    
    emails = [h[-2]['values']['email'] for h in histories]
    
    formatted_emails = "---START OF EMAIL---\n\n" + ("\n\n---END OF EMAIL---\n\n" + "---START OF EMAIL---\n\n").join(json.dumps(e) for e in emails)

    system_prompt = INSTRUCTIONS.format(emails=formatted_emails, notes=notes)
    if few_shot:
        with open("few_shot_emails.json", "r") as f:
            few_shot_emails_raw = json.load(f)

        few_shot_emails = "\n\n".join([e['formatted_error'] + "\n\n" + json.dumps({k:v for k,v in e.items() if k not in ["formatted_error"]}) for e in few_shot_emails_raw])
        few_shot_prompt = FEW_SHOT_PROMPT.format(examples=json.dumps(few_shot_emails))
        system_prompt = system_prompt + "\n\n" + few_shot_prompt
    openai_model = ChatOpenAI(model="o1").with_structured_output(Emails)
    
    response_openai = openai_model.invoke([("system", system_prompt), ("user", "Please come up with 15 emails, 5 each designed to break each category.")])

    with open("email_examples.json", "w") as f:
        json.dump(response_openai["emails"], f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--use-few-shot",
        type=bool,
        default=False,
    )
    args = parser.parse_args()
    asyncio.run(main(few_shot=args.use_few_shot))
