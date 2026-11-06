#!/usr/bin/env python3
"""Main entry point for GA4 Analytics Digest."""

import sys
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

from ga4_client import GA4Client
from email_notifier import EmailNotifier


def _build_notifier() -> EmailNotifier:
    """Create the notifier first so config errors surface before API calls."""
    return EmailNotifier()


def run_daily_report():
    """Run daily analytics report and send it by email."""
    print("📊 Generating daily analytics report...")

    try:
        # Initialize clients
        notifier = _build_notifier()
        ga4 = GA4Client()

        # Fetch yesterday's data
        data = ga4.get_daily_report()

        # Send by email
        success = notifier.send_daily_report(data)

        if success:
            print(f"✅ Daily report emailed to {notifier.recipient} for {data['date']}")
            print(f"   Users: {data['total_users']:,}, Page Views: {data['total_page_views']:,}")
        else:
            print("❌ Failed to send daily report")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error running daily report: {e}")
        sys.exit(1)


def run_weekly_report():
    """Run weekly analytics report and send it by email."""
    print("📊 Generating weekly analytics report...")

    try:
        # Initialize clients
        notifier = _build_notifier()
        ga4 = GA4Client()

        # Fetch last 7 days data
        data = ga4.get_weekly_report()

        # Send by email
        success = notifier.send_weekly_report(data)

        if success:
            print(f"✅ Weekly report emailed to {notifier.recipient}")
            print(f"   Period: {data['start_date']} to {data['end_date']}")
            print(f"   Users: {data['total_users']:,}, Page Views: {data['total_page_views']:,}")
        else:
            print("❌ Failed to send weekly report")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error running weekly report: {e}")
        sys.exit(1)


def test_connection():
    """Test GA4 access and Gmail SMTP delivery."""
    print("🧪 Testing connections...")

    try:
        # Test GA4
        print("\n1. Testing GA4 connection...")
        ga4 = GA4Client()
        test_data = ga4.get_daily_report(datetime.now() - timedelta(days=1))
        print(f"   ✅ GA4 connection successful!")
        print(f"   Found {test_data['total_users']} users, {test_data['total_page_views']} page views")

        # Test email
        print("\n2. Testing Gmail SMTP connection...")
        notifier = _build_notifier()
        success = notifier.send_message(
            "🔧 GA4 Analytics Digest - connection test",
            "Your GA4 Analytics Digest is configured correctly.\n\n"
            f"This test was sent to {notifier.recipient} at "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}.",
        )

        if success:
            print(f"   ✅ Email sent to {notifier.recipient}")
        else:
            print("   ❌ Email delivery failed")
            sys.exit(1)

        print("\n✨ All tests completed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='GA4 Analytics Digest')
    parser.add_argument(
        'command',
        choices=['daily', 'weekly', 'test'],
        help='Command to run: daily (yesterday\'s report), weekly (last 7 days report), or test (connection test)'
    )

    args = parser.parse_args()

    if args.command == 'daily':
        run_daily_report()
    elif args.command == 'weekly':
        run_weekly_report()
    elif args.command == 'test':
        test_connection()


if __name__ == '__main__':
    main()
