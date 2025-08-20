# Executive AI Assistant

Executive AI Assistant (EAIA) is an AI agent that attempts to do the job of an Executive Assistant (EA).

For a hosted version of EAIA, see documentation [here](https://mirror-feeling-d80.notion.site/How-to-hire-and-communicate-with-an-AI-Email-Assistant-177808527b17803289cad9e323d0be89?pvs=4).

Table of contents

- [General Setup](#general-setup)
  - [Env](#env)
  - [Credentials](#env)
  - [Configuration](#configuration)
- [Run locally](#run-locally)
  - [Setup EAIA](#set-up-eaia-locally)
  - [Ingest emails](#ingest-emails-locally)
  - [Connect to Agent Inbox](#set-up-agent-inbox-with-local-eaia)
  - [Use Agent Inbox](#use-agent-inbox)
- [Run in production (LangGraph Platform)](#run-in-production--langgraph-platform)
  - [Setup EAIA on LangGraph Platform](#set-up-eaia-on-langgraph-platform)
  - [Ingest manually](#ingest-manually)
  - [Set up cron job](#set-up-cron-job)

## General Setup

### Env

1. Fork and clone this repo. Note: make sure to fork it first, as in order to deploy this you will need your own repo.
2. Create a Python virtualenv and activate it (e.g. `pyenv virtualenv 3.11.1 eaia`, `pyenv activate eaia`)
3. Run `pip install -e .` to install dependencies and the package

### Set up your credentials

1. Export OpenAI API key (`export OPENAI_API_KEY=...`)
2. Export Anthropic API key (`export ANTHROPIC_API_KEY=...`)
3. Set up Google OAuth
   1. [Enable the API](https://developers.google.com/gmail/api/quickstart/python#enable_the_api)
      - Enable Gmail API if not already by clicking the blue button `Enable the API`
   2. [Authorize credentials for a desktop application](https://developers.google.com/gmail/api/quickstart/python#authorize_credentials_for_a_desktop_application)
  
> Note: If you're using a personal email (non-Google Workspace), select "External" as the User Type in the OAuth consent screen. With "External" selected, you must add your email as a test user in the Google Cloud Console under "OAuth consent screen" > "Test users" to avoid the "App has not completed verification" error. The "Internal" option only works for Google Workspace accounts.

5. Download the client secret. After that, run these commands:
6. `mkdir eaia/.secrets` - This will create a folder for secrets
7. `mv ${PATH-TO-CLIENT-SECRET.JSON} eaia/.secrets/secrets.json` - This will move the client secret you just created to that secrets folder
8. `python scripts/setup_gmail.py` - This will create the Google OAuth provider using LangChain Auth and handle the initial authentication flow.

**Authentication Flow**: EAIA uses LangChain Auth for OAuth management. The setup script creates a Google OAuth provider that handles token storage and refresh automatically. When you first run the application, you'll be prompted to complete OAuth authentication if needed.

### Configuration

The configuration for EAIA can be found in `eaia/main/config.yaml`. Every key in there is required. These are the configuration options:

- `email`: Email to monitor and send emails as. This should match the credentials you loaded above.
- `full_name`: Full name of user
- `name`: First name of user
- `background`: Basic info on who the user is
- `timezone`: Default timezone where the user is
- `schedule_preferences`: Any preferences for how calendar meetings are scheduled. E.g. length, name of meetings, etc
- `background_preferences`: Any background information that may be needed when responding to emails. E.g. coworkers to loop in, etc.
- `response_preferences`: Any preferences for what information to include in emails. E.g. whether to send calendly links, etc.
- `rewrite_preferences`: Any preferences for the tone of your emails
- `triage_no`: Guidelines for when emails should be ignored
- `triage_notify`: Guidelines for when user should be notified of emails (but EAIA should not attempt to draft a response)
- `triage_email`: Guidelines for when EAIA should try to draft a response to an email

## Run locally

You can run EAIA locally.
This is useful for testing it out, but when wanting to use it for real you will need to have it always running (to run the cron job to check for emails).
See [this section](#run-in-production--langgraph-platform) for instructions on how to run in production (on LangGraph Platform)

### Set up EAIA locally

1. Install development server `pip install -U "langgraph-cli[inmem]"`
2. Run development server `langgraph dev`

### Ingest Emails Locally

Let's now kick off an ingest job to ingest some emails and run them through our local EAIA.

Leave the `langgraph dev` command running, and open a new terminal. From there, get back into this directory and virtual environment. To kick off an ingest job, run:

```shell
python scripts/run_ingest.py --minutes-since 120 --rerun 1 --early 0
```

This will ingest all emails in the last 120 minutes (`--minutes-since`). It will NOT break early if it sees an email it already saw (`--early 0`) and it will
rerun ones it has seen before (`--rerun 1`). It will run against the local instance we have running.

### Set up Agent Inbox with Local EAIA

After we have [run it locally](#run-locally), we can interract with any results.

1. Go to [Agent Inbox](https://dev.agentinbox.ai/)
2. Connect this to your locally running EAIA agent:
   1. Click into `Settings`
   2. Input your LangSmith API key.
   3. Click `Add Inbox`
      1. Set `Assistant/Graph ID` to `main`
      2. Set `Deployment URL` to `http://127.0.0.1:2024`
      3. Give it a name like `Local EAIA`
      4. Press `Submit`

You can now interract with EAIA in the Agent Inbox.

## Run in production (LangGraph Platform)

These instructions will go over how to run EAIA in LangGraph Platform.
You will need a LangSmith Plus account to be able to access [LangGraph Platform](https://docs.langchain.com/langgraph-platform)

### Set up EAIA on LangGraph Platform

1. Make sure you have a LangSmith Plus account
2. Run the local setup first to create the Google OAuth provider (`python scripts/setup_gmail.py`)
3. Navigate to the deployments page in LangSmith
4. Click `New Deployment`
5. Connect it to your GitHub repo containing this code.
6. Give it a name like `Executive-AI-Assistant`
7. Add the following environment variables
   1. `OPENAI_API_KEY`
   2. `ANTHROPIC_API_KEY`  
8. Click `Submit` and watch your EAIA deploy

### Ingest manually

Let's now kick off a manual ingest job to ingest some emails and run them through our LangGraph Platform EAIA.

First, get your `LANGGRAPH_DEPLOYMENT_URL`

To kick off an ingest job, run:

```shell
python scripts/run_ingest.py --minutes-since 120 --rerun 1 --early 0 --url ${LANGGRAPH_DEPLOYMENT_URL}
```

This will ingest all emails in the last 120 minutes (`--minutes-since`). It will NOT break early if it sees an email it already saw (`--early 0`) and it will
rerun ones it has seen before (`--rerun 1`). It will run against the prod instance we have running (`--url ${LANGGRAPH_DEPLOYMENT_URL}`)

### Set up Agent Inbox with LangGraph Platform EAIA

After we have [deployed it](#set-up-eaia-on-langgraph-platform), we can interract with any results.

1. Go to [Agent Inbox](https://dev.agentinbox.ai/)
2. Connect this to your locally running EAIA agent:
   1. Click into `Settings`
   2. Click `Add Inbox`
      1. Set `Assistant/Graph ID` to `main`
      2. Set `Deployment URL` to your deployment URL
      3. Give it a name like `Prod EAIA`
      4. Press `Submit`

### Set up cron job

You probably don't want to manually run ingest all the time. Using LangGraph Platform, you can easily set up a cron job
that runs on some schedule to check for new emails. You can set this up with:

```shell
python scripts/setup_cron.py --url ${LANGGRAPH_DEPLOYMENT_URL}
```

## Advanced Options

If you want to control more of EAIA besides what the configuration allows, you can modify parts of the code base.

**Reflection Logic**
To control the prompts used for reflection (e.g. to populate memory) you can edit `eaia/reflection_graphs.py`

**Triage Logic**
To control the logic used for triaging emails you can edit `eaia/main/triage.py`

**Calendar Logic**
To control the logic used for looking at available times on the calendar you can edit `eaia/main/find_meeting_time.py`

**Tone & Style Logic**
To control the logic used for the tone and style of emails you can edit `eaia/main/rewrite.py`

**Email Draft Logic**
To control the logic used for drafting emails you can edit `eaia/main/draft_response.py`
