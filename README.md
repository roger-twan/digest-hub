# 📊 GA4 Analytics Digest

Automated daily and weekly web analytics reports from Google Analytics 4 (GA4) delivered to your Telegram.

## Features

- 📈 **Daily Reports**: Get yesterday's analytics delivered every morning
- 📊 **Weekly Reports**: Comprehensive weekly summaries every Monday
- 🔥 **Top Pages**: See your most popular content
- 👥 **User Metrics**: Track users, sessions, page views, and more
- ⏱️ **Engagement Stats**: Session duration and bounce rates
- 🤖 **Fully Automated**: GitHub Actions handles everything

## Setup Instructions

### 1. Google Analytics 4 Setup

#### Create a Service Account
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Google Analytics Data API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Analytics Data API"
   - Click "Enable"
4. Create a service account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "ga4-analytics-digest")
   - Grant "Viewer" role
   - Create and download a JSON key

#### Add Service Account to GA4
1. Go to your [Google Analytics](https://analytics.google.com/) property
2. Click the gear icon (Admin) in the bottom left
3. Under "Property" column, click "Property Access Management"
4. Click "Add users" and enter your service account email
5. Assign "Viewer" or "Analyst" role
6. Click "Add"

#### Get Your Property ID
- In GA4 Admin, look under "Property Settings"
- Your Property ID is the number (e.g., `123456789`)

### 2. Telegram Bot Setup

#### Create a Bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Save the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Get Your Chat ID
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID - save this number

Alternatively:
1. Message your new bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789` - that's your chat ID

### 3. GitHub Repository Setup

#### Fork/Create Repository
1. Create a new repository on GitHub
2. Push this code to it

#### Add Secrets
Go to Settings > Secrets and variables > Actions > Repository secrets, then add:

| Secret Name | Value |
|-------------|-------|
| `GA4_PROPERTY_ID` | Your GA4 property ID (just the number) |
| `GA4_CREDENTIALS_JSON` | Copy-paste the entire contents of your service account JSON key file |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID (can be a number or channel like `@channelname`) |

### 4. Test Your Setup

Run the connection test manually:

1. Go to Actions tab in your GitHub repository
2. Select "Daily Analytics Report" or "Weekly Analytics Report"
3. Click "Run workflow"
4. Check that you receive a test message on Telegram

Or run locally with [uv](https://github.com/astral-sh/uv) (requires Python 3.11+):

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set environment variables
export GA4_PROPERTY_ID="your_property_id"
export GA4_CREDENTIALS_JSON='{"type": "service_account", ...}'
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Run test
uv run python src/main.py test

# Run daily report manually
uv run python src/main.py daily

# Run weekly report manually
uv run python src/main.py weekly
```

## Automation Schedule

The GitHub Actions workflows are configured to run:

- **Daily Reports**: Every day at 9:00 AM UTC
- **Weekly Reports**: Every Monday at 9:00 AM UTC

You can modify the schedule in `.github/workflows/daily-report.yml` and `.github/workflows/weekly-report.yml`.

### Cron Schedule Format

```yaml
# ┌───────────── minute (0 - 59)
# │ ┌───────────── hour (0 - 23)
# │ │ ┌───────────── day of the month (1 - 31)
# │ │ │ ┌───────────── month (1 - 12)
# │ │ │ │ ┌───────────── day of the week (0 - 6)
# │ │ │ │ │
# │ │ │ │ │
# │ │ │ │ │
- cron: '0 9 * * *'  # 9:00 AM UTC daily
- cron: '0 9 * * 1'  # 9:00 AM UTC Monday
```

## Project Structure

```
.
├── .github/
│   └── workflows/
│       ├── daily-report.yml    # Daily report automation
│       └── weekly-report.yml   # Weekly report automation
├── src/
│   ├── main.py                 # Entry point and CLI
│   ├── ga4_client.py           # GA4 API client
│   └── telegram_notifier.py    # Telegram bot integration
├── pyproject.toml              # Project configuration (uv)
├── uv.lock                     # Locked dependencies (auto-generated)
└── README.md                   # This file
```

## Report Format

### Daily Report
- Total users, new users, sessions, page views
- Average session duration and bounce rate
- Top 5 pages by views

### Weekly Report
- Weekly totals for all metrics
- Daily breakdown for the week
- Top 5 pages for the week

## Troubleshooting

### GA4 Connection Issues
- Verify the service account has access to the GA4 property
- Check that the Google Analytics Data API is enabled
- Ensure your Property ID is correct (just the number, not the full property string)

### Telegram Issues
- Verify bot token is correct
- Make sure you've messaged the bot first (bots can't initiate conversations)
- Check that the chat ID is correct (use @userinfobot to verify)

### GitHub Actions Issues
- Check the Actions logs for detailed error messages
- Verify all secrets are set correctly
- Ensure the workflow files are in `.github/workflows/`

## License

MIT License - feel free to use and modify as needed.
