# Gmail AI Assistant - Setup Guide

This guide will help you set up your personal Gmail AI Assistant.

## Prerequisites

- Python 3.11 or 3.12
- A Gmail account
- OpenAI API account
- Anthropic API account (optional, for reflection features)
- LangSmith account (for monitoring)

## Step-by-Step Setup

### 1. Install Dependencies

```bash
# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package and dependencies
pip install -e .
```

### 2. Configure API Keys

Edit the `.env` file and add your API keys:

```bash
# Required API Keys:
LANGSMITH_API_KEY=your_langsmith_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Where to get API keys:**
- **LangSmith**: https://smith.langchain.com/settings
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys

Then load them:
```bash
source .env  # On Windows: use `set` command for each variable
```

### 3. Set Up Google OAuth Credentials

#### 3.1 Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Library"
4. Search for "Gmail API" and click "Enable"
5. Also enable "Google Calendar API"

#### 3.2 Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - **User Type**: Select "External" (for personal Gmail) or "Internal" (for Google Workspace)
   - **App name**: Give it a name like "Gmail AI Assistant"
   - **User support email**: Your email
   - **Developer contact**: Your email
   - Add your email as a **Test user** under "OAuth consent screen" > "Test users"
4. Back in "Create OAuth client ID":
   - **Application type**: Desktop app
   - **Name**: Gmail AI Assistant
5. Click "Create" and download the credentials JSON file

#### 3.3 Install Credentials

```bash
# Create secrets directory
mkdir -p eaia/.secrets

# Move the downloaded credentials file
mv ~/Downloads/client_secret_*.json eaia/.secrets/secrets.json

# Run the setup script (this will trigger OAuth flow)
python scripts/setup_gmail.py
```

You'll be prompted to authorize the app in your browser. Grant the necessary permissions.

### 4. Configure Your Personal Settings

Edit `eaia/main/config.yaml` with your personal information:

```yaml
email: your.email@gmail.com  # Your Gmail address
full_name: Your Full Name
name: FirstName
background: |
  Brief description of who you are and what you do.
  This helps the AI understand your context.
timezone: "PST"  # Your timezone (e.g., PST, EST, UTC)

schedule_preferences: |
  - Default meeting length: 30 minutes
  - Preferred meeting times: 10am-4pm on weekdays
  - Any other scheduling preferences

background_preferences: |
  - Key people to loop in on certain topics
  - Important context about your organization
  - Any coworkers or team members the AI should know about

response_preferences: |
  - How you prefer to handle meeting requests
  - Whether to send calendar links
  - Any standard information to include in responses

rewrite_preferences: |
  - Your preferred email tone (formal/casual/mixed)
  - Any specific phrases or styles you use
  - Guidelines for matching recipient's tone

triage_no: |
  Guidelines for emails to IGNORE:
  - Automated notifications from services
  - Cold outreach from vendors
  - Spam or marketing emails

triage_notify: |
  Guidelines for emails to NOTIFY you about (but not respond):
  - Important documents that need your review
  - Time-sensitive items requiring action
  - Technical questions about your work

triage_email: |
  Guidelines for emails the AI should DRAFT responses for:
  - Direct questions from colleagues or clients
  - Meeting scheduling requests
  - Follow-ups where you're the main contact
  - Introductions you need to make

memory: true  # Enable learning from feedback
```

### 5. Test the Setup Locally

#### 5.1 Install LangGraph CLI

```bash
pip install -U "langgraph-cli[inmem]"
```

#### 5.2 Start the Development Server

```bash
langgraph dev
```

This will start the server at http://127.0.0.1:2024

#### 5.3 Ingest Test Emails

Open a new terminal window and run:

```bash
# Ingest emails from the last 2 hours
python scripts/run_ingest.py --minutes-since 120 --rerun 1 --early 0
```

**Parameters:**
- `--minutes-since 120`: Process emails from last 120 minutes
- `--rerun 1`: Reprocess emails even if already seen (useful for testing)
- `--early 0`: Don't stop early, process all emails found

### 6. Interact with Your AI Assistant

You have two options:

#### Option A: Use Agent Inbox (Recommended)

1. Go to [Agent Inbox](https://dev.agentinbox.ai/)
2. Click "Settings" and enter your LangSmith API key
3. Click "Add Inbox":
   - **Assistant/Graph ID**: `main`
   - **Deployment URL**: `http://127.0.0.1:2024`
   - **Name**: Local Gmail AI Assistant
4. Review drafted responses, provide feedback, and approve/reject

#### Option B: Use LangSmith Directly

1. Go to [LangSmith](https://smith.langchain.com/)
2. Find your project and view the traces
3. See how emails are being processed

### 7. Deploy to Production (Optional)

For continuous operation, deploy to LangGraph Platform:

#### 7.1 Prerequisites

- LangSmith Plus account
- GitHub account (fork this repo first)

#### 7.2 Deploy

1. Run local setup first: `python scripts/setup_gmail.py`
2. Go to LangSmith > Deployments
3. Click "New Deployment"
4. Connect to your GitHub repo
5. Add environment variables:
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
6. Click "Submit" and wait for deployment

#### 7.3 Set Up Cron Job

To automatically check for new emails:

```bash
# Get your deployment URL from LangSmith
export LANGGRAPH_DEPLOYMENT_URL=your_deployment_url

# Set up a cron job to run every 15 minutes
python scripts/setup_cron.py --url $LANGGRAPH_DEPLOYMENT_URL
```

## Features

Your AI Assistant can:

- **Triage emails** automatically (ignore, notify, or draft response)
- **Draft responses** in your tone and style
- **Check your calendar** and suggest meeting times
- **Schedule meetings** with Google Calendar invites
- **Learn from feedback** to improve over time
- **Ask clarifying questions** when needed
- **Human-in-the-loop** - you review and approve all responses

## Troubleshooting

### "App has not completed verification" Error

If using a personal Gmail (non-Workspace):
1. Go to Google Cloud Console > OAuth consent screen
2. Add your email under "Test users"
3. Use "External" user type

### OAuth Errors

- Make sure you've enabled both Gmail API and Google Calendar API
- Check that credentials file is at `eaia/.secrets/secrets.json`
- Try running `python scripts/setup_gmail.py` again

### No Emails Being Processed

- Check that your email in `config.yaml` matches your OAuth credentials
- Try increasing `--minutes-since` parameter
- Check LangSmith traces for errors

### API Key Errors

- Verify all API keys are set in `.env`
- Make sure to run `source .env` or export variables manually
- Check that keys are valid and have sufficient quota

## Next Steps

1. Start with a small time window (e.g., last 2 hours) to test
2. Review how the AI triages and drafts responses
3. Provide feedback to help it learn your preferences
4. Gradually expand to longer time windows
5. Once confident, deploy to production with cron job

## Support

- Documentation: [See README.md](./README.md)
- Issues: Report on GitHub
- Advanced customization: Edit Python files in `eaia/` directory

## Security Notes

- Your OAuth credentials are stored locally in `eaia/.secrets/`
- API keys should never be committed to git (they're in `.gitignore`)
- The AI can only read and send emails after you authorize it
- You approve all responses before they're sent (in default mode)
