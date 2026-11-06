# 📊 Digest Hub

Scheduled workflows that fetch data from the internet and email you digest reports — currently daily and weekly web analytics from Google Analytics 4 (GA4).

## Features

- 📈 **Daily Reports**: Get yesterday's analytics delivered every morning
- 📊 **Weekly Reports**: Comprehensive weekly summaries every Monday
- 🔥 **Top Pages**: See your most popular content
- 👥 **User Metrics**: Track users, sessions, page views, and more
- ⏱️ **Engagement Stats**: Session duration and bounce rates
- 📧 **Email Delivery**: Styled HTML report plus a plain-text fallback, sent through Gmail SMTP
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

### 2. Gmail SMTP Setup

Reports are emailed through Gmail's SMTP server using a Google **App Password**.

1. Turn on **2-Step Verification** for the sending Google account:
   [myaccount.google.com/security](https://myaccount.google.com/security).
2. Create an App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   (app "Mail", device "Other"). It is 16 characters and is shown only once.
3. Set these values in your local `.env` and in GitHub Actions repository secrets:

   | Variable | Meaning |
   |----------|---------|
   | `GMAIL_USER` | Gmail address that sends the reports |
   | `GMAIL_APP_PASSWORD` | The 16-character App Password (not your normal password) |
   | `EMAIL_TO` | Recipient address; comma-separate several. Defaults to `GMAIL_USER` |

Delivery uses `smtp.gmail.com` on port 587 with STARTTLS. Set `SMTP_HOST` / `SMTP_PORT`
to use another endpoint; port 465 switches to implicit TLS.

Each report is sent as a multipart email: a styled HTML part plus a plain-text fallback.
Email is the only delivery channel; missing Gmail configuration causes an error.

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
| `GMAIL_USER` | Gmail address that sends the reports |
| `GMAIL_APP_PASSWORD` | 16-character Google App Password |
| `EMAIL_TO` | Recipient address (optional; defaults to `GMAIL_USER`) |

### 4. Test Your Setup

Run the connection test manually:

1. Go to Actions tab in your GitHub repository
2. Select "Daily Analytics Report" or "Weekly Analytics Report"
3. Click "Run workflow"
4. Check that you receive the selected analytics report in your inbox

Or run locally with [uv](https://github.com/astral-sh/uv) (requires Python 3.11+):

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set up environment variables
cp .env.sample .env
# Edit .env with your actual values from the setup steps above

# Run test (sends a test email)
uv run python src/main.py test

# Run daily report manually
uv run python src/main.py daily

# Run weekly report manually
uv run python src/main.py weekly

# Run the test suite
uv run python -m unittest discover -s tests
```

## Automation Schedule

The GitHub Actions workflows are configured to run:

- **Daily Reports**: Every day at 8:00 AM Beijing time (00:00 UTC)
- **Weekly Reports**: Every Monday at 8:00 AM Beijing time (00:00 UTC)

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
- cron: '0 0 * * *'  # 8:00 AM Beijing time (00:00 UTC) daily
- cron: '0 0 * * 1'  # 8:00 AM Beijing time (00:00 UTC) Monday
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
│   └── email_notifier.py       # Gmail SMTP integration (HTML + text)
├── tests/
│   └── test_email_notifier.py  # Email rendering and SMTP delivery tests
├── .env.sample                 # Environment variables template
├── pyproject.toml              # Project configuration (uv)
├── uv.lock                     # Locked dependencies (auto-generated)
└── README.md                   # This file
```

## Report Format

### Daily Report
- Total users, new users, sessions, page views
- Average session duration and bounce rate
- Top 5 countries and top 5 pages by views

### Weekly Report
- Weekly totals for all metrics
- Daily breakdown for the week
- Top 5 countries and top 5 pages for the week

Both reports are emailed as an HTML message with KPI cards and tables, plus a plain-text
alternative for terminal and text-only mail clients.

## Troubleshooting

### GA4 Connection Issues
- Verify the service account has access to the GA4 property
- Check that the Google Analytics Data API is enabled
- Ensure your Property ID is correct (just the number, not the full property string)

### Email Issues
- `GMAIL_APP_PASSWORD` must be a Google App Password, not the account password. 2-Step
  Verification has to be enabled before App Passwords can be created.
- Spaces in the App Password are ignored, so pasted `abcd efgh ijkl mnop` works.
- Check the spam folder, and add the sender to contacts if reports are filtered.
- Gmail limits how many messages an account can send per day; normal report volumes are far below it.
- Delivery failures are reported by error code only — credentials are never logged.
- Use the `test` command to confirm SMTP login before relying on the schedule.

### GitHub Actions Issues
- Check the Actions logs for detailed error messages
- Verify `GA4_PROPERTY_ID`, `GA4_CREDENTIALS_JSON`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`
  and `EMAIL_TO` are set as repository secrets
- Ensure the workflow files are in `.github/workflows/`

## License

MIT License - feel free to use and modify as needed.
