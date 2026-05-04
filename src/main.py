#!/usr/bin/env python3
"""Main entry point for GA4 Analytics Digest."""

import os
import sys
import argparse
from datetime import datetime, timedelta
from ga4_client import GA4Client
from telegram_notifier import TelegramNotifier


def run_daily_report():
    """Run daily analytics report and send to Telegram."""
    print("📊 Generating daily analytics report...")
    
    try:
        # Initialize clients
        ga4 = GA4Client()
        telegram = TelegramNotifier()
        
        # Fetch yesterday's data
        data = ga4.get_daily_report()
        
        # Send to Telegram
        success = telegram.send_daily_report(data)
        
        if success:
            print(f"✅ Daily report sent successfully for {data['date']}")
            print(f"   Users: {data['total_users']:,}, Page Views: {data['total_page_views']:,}")
        else:
            print("❌ Failed to send daily report")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error running daily report: {e}")
        sys.exit(1)


def run_weekly_report():
    """Run weekly analytics report and send to Telegram."""
    print("📊 Generating weekly analytics report...")
    
    try:
        # Initialize clients
        ga4 = GA4Client()
        telegram = TelegramNotifier()
        
        # Fetch last 7 days data
        data = ga4.get_weekly_report()
        
        # Send to Telegram
        success = telegram.send_weekly_report(data)
        
        if success:
            print(f"✅ Weekly report sent successfully")
            print(f"   Period: {data['start_date']} to {data['end_date']}")
            print(f"   Users: {data['total_users']:,}, Page Views: {data['total_page_views']:,}")
        else:
            print("❌ Failed to send weekly report")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error running weekly report: {e}")
        sys.exit(1)


def test_connection():
    """Test GA4 and Telegram connections."""
    print("🧪 Testing connections...")
    
    try:
        # Test GA4
        print("\n1. Testing GA4 connection...")
        ga4 = GA4Client()
        test_data = ga4.get_daily_report(datetime.now() - timedelta(days=1))
        print(f"   ✅ GA4 connection successful!")
        print(f"   Found {test_data['total_users']} users, {test_data['total_page_views']} page views")
        
        # Test Telegram
        print("\n2. Testing Telegram connection...")
        telegram = TelegramNotifier()
        test_msg = "🔧 *Connection Test*\nYour GA4 Analytics Digest is configured correctly!"
        success = telegram.send_message(test_msg)
        
        if success:
            print("   ✅ Telegram connection successful!")
        else:
            print("   ❌ Telegram connection failed")
            
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
