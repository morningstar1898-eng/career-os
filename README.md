# Career OS — AI Agent System
### Automated job search + daily learning + portfolio building

Runs every weekday at 7am. You wake up to a Notion briefing. That's it.

---

## What it does each day

| Time | Agent | Action |
|------|-------|--------|
| 7:00am | Skills Scout | Scans job boards, extracts top skill gaps |
| 7:15am | Job Applicant | Tailors resume + sends up to 5 applications, logs to Sheets |
| 7:30am | Tutor | Writes your 30-min lesson based on skill gaps |
| 8:00am | Data Analyst | Downloads a Kaggle dataset, builds 3 charts, uploads to Azure |
| 8:15am | Orchestrator | Compiles everything into one Notion briefing page |

**Your daily input: zero.**

---

## Setup (one-time, ~2 hours)

### Step 1 — Clone & install

```bash
git clone https://github.com/YOURUSERNAME/career-os.git
cd career-os
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.template .env
```

---

### Step 2 — Get your API keys

#### Anthropic (Claude) — Required
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. API Keys → Create Key
3. Paste into `.env` as `ANTHROPIC_API_KEY`
4. Add $5 credit (Settings → Billing)

#### Serper (web search) — Required, free
1. Go to [serper.dev](https://serper.dev)
2. Sign up → copy API key
3. Paste into `.env` as `SERPER_API_KEY`
4. Free tier = 2,500 searches/month (plenty)

#### Notion — Required
1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. New integration → name it "Career OS" → Submit
3. Copy the Internal Integration Token → paste as `NOTION_API_KEY`
4. Create a Notion page called "Career OS"
5. On that page: click `...` → Connections → Add your integration
6. Run setup: `python config/setup_notion.py` — paste the page ID when prompted
7. Copy the printed Database ID → paste as `NOTION_DATABASE_ID`

**How to find the Notion page ID:** Open the page in browser.
The URL looks like: `notion.so/Career-OS-abc123def456` — the ID is `abc123def456`

#### Google (Sheets + service account) — Required
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project → "Career OS"
3. Enable APIs: search and enable both **Google Sheets API** and **Google Drive API**
4. IAM & Admin → Service Accounts → Create Service Account → name it "career-os"
5. Click the service account → Keys → Add Key → JSON → download file
6. Rename it `google_credentials.json` → move to `config/` folder
7. Run setup: `python config/setup_sheets.py`
8. Copy the printed Sheet ID → paste as `GOOGLE_SHEET_ID`

#### Kaggle — Required for data pipeline
1. Go to [kaggle.com](https://www.kaggle.com) → your profile → Account
2. Scroll to API → Create New Token → downloads `kaggle.json`
3. Copy username and key into `.env`

#### Azure — Optional (charts still save locally if skipped)
1. Go to [portal.azure.com](https://portal.azure.com) → free account
2. Create a Storage Account → Containers → new container named `portfolio-charts`
3. Set public access to "Blob" (so URLs are shareable)
4. Storage Account → Access Keys → copy connection string → paste as `AZURE_STORAGE_CONNECTION_STRING`

---

### Step 3 — Fill in your profile

Edit `.env` — the bottom section:

```
YOUR_NAME=Meagan Smith
TARGET_ROLES=Data Analyst,BI Analyst,Analytics Engineer
TARGET_CITIES=Remote,Oklahoma City OK
DEGREE=MBA in Data Analytics
SKILLS_CURRENT=Excel,Basic SQL,PowerPoint
```

Edit `config/resume.txt` with your actual experience.

---

### Step 4 — Test it locally

```bash
python main.py
```

Watch it run. First run takes ~15 minutes. Check your Notion when done.

---

### Step 5 — Push to GitHub + add secrets

```bash
git init
git add .
git commit -m "Initial Career OS setup"
# Create a new PRIVATE repo on github.com, then:
git remote add origin https://github.com/YOURUSERNAME/career-os.git
git push -u origin main
```

Add secrets at: **GitHub repo → Settings → Secrets and variables → Actions → New repository secret**

Add one secret for every value in your `.env` file:
- `ANTHROPIC_API_KEY`
- `SERPER_API_KEY`
- `NOTION_API_KEY`
- `NOTION_DATABASE_ID`
- `GOOGLE_CREDENTIALS_JSON` ← paste the entire contents of `config/google_credentials.json`
- `GOOGLE_SHEET_ID`
- `GMAIL_SENDER`
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_STORAGE_CONTAINER`
- `KAGGLE_USERNAME`
- `KAGGLE_KEY`
- `YOUR_NAME`
- `TARGET_ROLES`
- `TARGET_CITIES`
- `DEGREE`
- `SKILLS_CURRENT`

**That's it.** GitHub Actions runs at 7am every weekday automatically.

---

### Manual trigger (run anytime)
Go to: GitHub repo → Actions → Daily Career OS → Run workflow → Run workflow

---

## Estimated monthly cost

| Service | Cost |
|---------|------|
| Claude API | ~$3–8/month |
| Serper search | Free (2,500/mo) |
| GitHub Actions | Free (2,000 min/mo) |
| Azure Blob | Free (5GB) |
| Kaggle | Free |
| Notion | Free |
| **Total** | **< $10/month** |

---

## File structure

```
career-os/
├── main.py                          # Entry point
├── requirements.txt
├── .env.template                    # Copy to .env and fill in
├── .github/
│   └── workflows/
│       └── daily_career_os.yml      # Cron automation
├── agents/
│   ├── crew_agents.py               # All 5 agent definitions
│   └── crew_tasks.py                # Daily task definitions
├── tools/
│   ├── shared_tools.py              # Web search, Notion, Sheets, Azure tools
│   └── data_pipeline.py             # Kaggle → clean → chart → upload
├── config/
│   ├── resume.txt                   # YOUR resume (fill this in)
│   ├── setup_notion.py              # Run once to create Notion DB
│   └── setup_sheets.py             # Run once to create Google Sheet
└── outputs/                         # Charts saved here locally
```

---

## Troubleshooting

**"Missing env vars" error** → Check your `.env` file has all keys filled in.

**Notion write fails** → Make sure you shared the Notion page with your integration (Step 2, Notion section).

**Google Sheets fails** → Confirm `config/google_credentials.json` exists and has correct content.

**Kaggle download slow** → First run downloads the dataset file. Subsequent runs reuse cached files.

**GitHub Actions fails** → Go to Actions tab → click the failed run → read the error log. 99% of failures are a missing secret.
