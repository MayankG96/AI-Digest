# AI News Digest

A fully automated Python pipeline that fetches the latest AI news every morning, ranks the top 7 stories using Gemini, emails you a formatted digest, saves the stories to Supabase, and sends a Telegram notification — hands-free, every day at 6:00 AM PDT via GitHub Actions.

---

## What It Does

1. **Fetches** AI news published in the last 24 hours from 6 sources: Hacker News, ArXiv (cs.AI / cs.LG / cs.CL), VentureBeat, TechCrunch, The Batch, and Import AI.
2. **Deduplicates** across sources by URL and title similarity.
3. **Ranks** the top 7 stories using Gemini 2.5 Flash via LangChain, scoring each on technical novelty and real-world impact.
4. **Formats** a polished dark-header HTML email with summaries and "Why This Matters" sections for each story.
5. **Sends** the digest via Gmail SMTP to any recipient you specify.
6. **Pings** you on Telegram so you know the digest is in your inbox.
7. **Saves** the ranked stories to Supabase for use by the post-creator-bot.

---

## Setup

### 1. Get a Gemini API Key

1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) and sign in with your Google account.
2. Click **Create API Key**.
3. Copy the key — you'll add it as `GEMINI_API_KEY`.

### 2. Create a Gmail App Password

Gmail requires an App Password (not your account password) for SMTP access:

1. Go to your [Google Account](https://myaccount.google.com).
2. Navigate to **Security**.
3. Under "How you sign in to Google", ensure **2-Step Verification** is enabled.
4. Search for **App Passwords** (or go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)).
5. Select app: **Mail**, device: **Other** (type "AI Digest"), then click **Generate**.
6. Copy the 16-character password — you'll add it as `GMAIL_APP_PASSWORD`.

### 3. Set Up Supabase

1. Create a free account at [supabase.com](https://supabase.com).
2. Create a new project.
3. Go to the **SQL Editor** and run:

```sql
create table digest_items (
  id uuid default gen_random_uuid() primary key,
  date date not null,
  rank integer not null,
  title text not null,
  url text,
  summary text,
  why_it_matters text,
  score float,
  source text,
  created_at timestamptz default now(),
  unique(date, rank)
);
```

4. Go to **Settings → API** and copy your Project URL and `anon` public key.

### 4. Set Up Telegram Notifications

1. Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, and follow the prompts to create a bot. Copy the token.
2. Message your bot on Telegram, then use the [getUpdates API](https://api.telegram.org/bot<TOKEN>/getUpdates) to retrieve your chat ID.

### 5. Add Secrets to GitHub

In your GitHub repository go to **Settings → Secrets and variables → Actions** and add:

| Secret Name           | Value                                          |
|-----------------------|------------------------------------------------|
| `GEMINI_API_KEY`      | Your Google Gemini API key                     |
| `GMAIL_ADDRESS`       | Your Gmail address (e.g. `you@gmail.com`)      |
| `GMAIL_APP_PASSWORD`  | The 16-character App Password from step 2      |
| `RECIPIENT_EMAIL`     | Where to deliver the digest (can be the same)  |
| `TELEGRAM_BOT_TOKEN`  | Your Telegram bot token from @BotFather        |
| `TELEGRAM_CHAT_ID`    | Your personal Telegram chat ID                 |
| `SUPABASE_URL`        | Your Supabase project URL                      |
| `SUPABASE_KEY`        | The `anon` public key from Supabase            |

---

## Local Development

1. **Clone the repo** and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create a `.env` file** in the project root (never commit this file):
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GMAIL_ADDRESS=you@gmail.com
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
   RECIPIENT_EMAIL=recipient@example.com
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_anon_key
   ```

3. **Run the pipeline**:
   ```bash
   python src/main.py
   ```

   You'll see structured log output for each step and receive the email and Telegram ping within seconds of the pipeline finishing.

---

## Triggering the Workflow Manually

You don't have to wait for the 6:00 AM schedule. To run it immediately:

1. Go to your repository on GitHub.
2. Click the **Actions** tab.
3. Select **Daily AI Digest** from the left sidebar.
4. Click the **Run workflow** button (top right of the workflow list).
5. Click the green **Run workflow** confirmation button.

The job will start within a few seconds and you'll receive your digest email and Telegram notification shortly after.

---

## Swapping the LLM

The LLM is configured in **`src/ranker.py`**. To switch providers, change the `_get_llm()` function:

### Switch to Anthropic Claude

```python
# pip install langchain-anthropic
from langchain_anthropic import ChatAnthropic

def _get_llm():
    return ChatAnthropic(
        model="claude-opus-4-5",
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        temperature=0.3,
    )
```

Remember to add the corresponding API key to your `.env` file and GitHub Secrets.

---

## Project Structure

```
ai-digest/
├── .github/
│   └── workflows/
│       └── daily.yml       # GitHub Actions schedule (6 AM PDT daily)
├── src/
│   ├── fetcher.py          # Pulls news from HN, ArXiv, and 4 RSS feeds
│   ├── ranker.py           # Gemini ranking + summarisation via LangChain
│   ├── formatter.py        # Builds the HTML email (inline CSS)
│   ├── sender.py           # Gmail SMTP sender
│   ├── storage.py          # Saves ranked stories to Supabase
│   ├── notifier.py         # Sends Telegram ping after email
│   └── main.py             # Pipeline orchestrator
├── requirements.txt
└── README.md
```

---

## Notes

- All secrets are injected via environment variables — nothing is hardcoded.
- If a single news source is unavailable, the pipeline logs a warning and continues with the remaining sources.
- Telegram and Supabase steps are non-fatal — if either fails, the email has already been sent.
- The `.env` file is for local development only. It is never read in CI (GitHub Actions injects secrets directly into the environment).
- Compatible with Python 3.11+.
