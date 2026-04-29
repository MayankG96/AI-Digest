# AI News Digest

A fully automated Python pipeline that fetches the latest AI news every morning, ranks the top 7 stories using an LLM, and emails you a beautifully formatted digest — hands-free, every day at 6:00 AM PST via GitHub Actions.

---

## What It Does

1. **Fetches** AI news published in the last 24 hours from 6 sources: Hacker News, ArXiv (cs.AI / cs.LG / cs.CL), VentureBeat, TechCrunch, The Batch, and Import AI.
2. **Deduplicates** across sources by URL and title similarity.
3. **Ranks** the top 7 stories using Grok-3-mini (via the xAI API), scoring each on technical novelty and real-world impact.
4. **Formats** a polished dark-header HTML email with summaries and "Why This Matters" sections for each story.
5. **Sends** the digest via Gmail SMTP to any recipient you specify.

---

## Setup

### 1. Get a Grok API Key

1. Go to [https://console.x.ai](https://console.x.ai) and sign in with your X (Twitter) account.
2. Navigate to **API Keys** and click **Create API Key**.
3. Copy the key — you'll add it as `GROK_API_KEY`.

### 2. Create a Gmail App Password

Gmail requires an App Password (not your account password) for SMTP access:

1. Go to your [Google Account](https://myaccount.google.com).
2. Navigate to **Security**.
3. Under "How you sign in to Google", ensure **2-Step Verification** is enabled.
4. Search for **App Passwords** (or go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)).
5. Select app: **Mail**, device: **Other** (type "AI Digest"), then click **Generate**.
6. Copy the 16-character password — you'll add it as `GMAIL_APP_PASSWORD`.

### 3. Add Secrets to GitHub

In your GitHub repository:

1. Go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret** for each of the following:

| Secret Name         | Value                                         |
|---------------------|-----------------------------------------------|
| `GROK_API_KEY`      | Your xAI API key                              |
| `GMAIL_ADDRESS`     | Your Gmail address (e.g. `you@gmail.com`)     |
| `GMAIL_APP_PASSWORD`| The 16-character App Password from step 2     |
| `RECIPIENT_EMAIL`   | Where to deliver the digest (can be the same) |

---

## Local Development

1. **Clone the repo** and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create a `.env` file** in the project root (never commit this file):
   ```env
   GROK_API_KEY=your_xai_api_key_here
   GMAIL_ADDRESS=you@gmail.com
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
   RECIPIENT_EMAIL=recipient@example.com
   ```

3. **Run the pipeline**:
   ```bash
   python src/main.py
   ```

   You'll see structured log output for each step and receive the email within seconds of the pipeline finishing.

---

## Triggering the Workflow Manually

You don't have to wait for the 6:00 AM schedule. To run it immediately:

1. Go to your repository on GitHub.
2. Click the **Actions** tab.
3. Select **Daily AI Digest** from the left sidebar.
4. Click the **Run workflow** button (top right of the workflow list).
5. Click the green **Run workflow** confirmation button.

The job will start within a few seconds and you'll receive your digest email shortly after.

---

## Swapping the LLM

The LLM is configured in **`src/ranker.py`**. To switch providers, change these three lines:

### Switch to Google Gemini

```python
# pip install langchain-google-genai
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",          # ← line 1: model name
    google_api_key=os.environ["GOOGLE_API_KEY"],  # ← line 2: env var + key
    temperature=0.3,
)
# ← line 3: remove openai_api_base (not needed for Gemini)
```

### Switch to Anthropic Claude

```python
# pip install langchain-anthropic
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-opus-4-6",         # ← line 1: model name
    anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],  # ← line 2: env var + key
    temperature=0.3,
)
# ← line 3: remove openai_api_base (not needed for Anthropic)
```

Remember to add the corresponding API key (`GOOGLE_API_KEY` or `ANTHROPIC_API_KEY`) to your `.env` file and GitHub Secrets.

---

## Project Structure

```
ai-digest/
├── .github/
│   └── workflows/
│       └── daily.yml       # GitHub Actions schedule (6 AM PST daily)
├── src/
│   ├── fetcher.py          # Pulls news from HN, ArXiv, and 4 RSS feeds
│   ├── ranker.py           # LLM ranking + summarisation via LangChain
│   ├── formatter.py        # Builds the HTML email (inline CSS)
│   ├── sender.py           # Gmail SMTP sender
│   └── main.py             # Pipeline orchestrator
├── requirements.txt
└── README.md
```

---

## Notes

- All secrets are injected via environment variables — nothing is hardcoded.
- If a single news source is unavailable, the pipeline logs a warning and continues with the remaining sources.
- The `.env` file is for local development only. It is never read in CI (GitHub Actions injects secrets directly into the environment).
- Compatible with Python 3.11+.
