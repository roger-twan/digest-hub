"""Telegram Bot for sending analytics notifications."""

import os
import requests
from typing import Dict
from datetime import datetime


class TelegramNotifier:
    """Telegram bot for sending analytics reports."""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        """Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is required")
        
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, text: str, parse_mode: str = 'Markdown') -> bool:
        """Send a text message to Telegram.
        
        Args:
            text: Message text
            parse_mode: Parse mode (Markdown, HTML, or None)
            
        Returns:
            True if sent successfully
        """
        url = f"{self.api_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to send Telegram message: {e}")
            return False

    def format_daily_report(self, data: Dict) -> str:
        """Format daily analytics data as Telegram message.
        
        Args:
            data: Daily analytics data dictionary
            
        Returns:
            Formatted message string
        """
        date = data.get('date', 'Unknown')
        
        # Format duration
        avg_duration = data.get('avg_session_duration', 0)
        minutes = int(avg_duration // 60)
        seconds = int(avg_duration % 60)
        duration_str = f"{minutes}m {seconds}s"
        
        # Format bounce rate
        bounce_rate = data.get('bounce_rate', 0)
        bounce_rate_str = f"{bounce_rate * 100:.1f}%"
        
        message = f"""📊 *Daily Analytics Report - {date}*

*📈 Overview*
• Total Users: `{data.get('total_users', 0):,}`
• New Users: `{data.get('new_users', 0):,}`
• Sessions: `{data.get('total_sessions', 0):,}`
• Page Views: `{data.get('total_page_views', 0):,}`

*🔍 Engagement*
• Avg Session Duration: `{duration_str}`
• Bounce Rate: `{bounce_rate_str}`

*🌍 Top Countries*"""

        for i, country in enumerate(data.get('top_countries', [])[:5], 1):
            country_name = country.get('country', 'Unknown')[:20]
            users = country.get('users', 0)
            message += f"\n{i}. {country_name} - `{users:,}` users"
        
        message += "\n\n*🔥 Top Pages*"
        
        for i, page in enumerate(data.get('top_pages', [])[:5], 1):
            title = page.get('title', 'Unknown')[:30]
            views = page.get('views', 0)
            message += f"\n{i}. {title}... - `{views:,}` views"
        
        return message

    def format_weekly_report(self, data: Dict) -> str:
        """Format weekly analytics data as Telegram message.
        
        Args:
            data: Weekly analytics data dictionary
            
        Returns:
            Formatted message string
        """
        start_date = data.get('start_date', 'Unknown')
        end_date = data.get('end_date', 'Unknown')
        
        # Format duration
        avg_duration = data.get('avg_session_duration', 0)
        minutes = int(avg_duration // 60)
        seconds = int(avg_duration % 60)
        duration_str = f"{minutes}m {seconds}s"
        
        # Format bounce rate
        bounce_rate = data.get('bounce_rate', 0)
        bounce_rate_str = f"{bounce_rate * 100:.1f}%"
        
        message = f"""📊 *Weekly Analytics Report*
*{start_date} - {end_date}*

*📈 Overview*
• Total Users: `{data.get('total_users', 0):,}`
• New Users: `{data.get('new_users', 0):,}`
• Sessions: `{data.get('total_sessions', 0):,}`
• Page Views: `{data.get('total_page_views', 0):,}`

*🔍 Engagement*
• Avg Session Duration: `{duration_str}`
• Bounce Rate: `{bounce_rate_str}`

*📅 Daily Breakdown*"""

        # Sort daily breakdown by date
        daily = data.get('daily_breakdown', {})
        for date in sorted(daily.keys()):
            day_data = daily[date]
            formatted_date = datetime.strptime(date, '%Y%m%d').strftime('%a %m/%d')
            message += f"\n• {formatted_date}: `{day_data['users']:,}` users, `{day_data['page_views']:,}` views"
        
        message += "\n\n*🌍 Top Countries This Week*"
        for i, country in enumerate(data.get('top_countries', [])[:5], 1):
            country_name = country.get('country', 'Unknown')[:20]
            users = country.get('users', 0)
            message += f"\n{i}. {country_name} - `{users:,}` users"
        
        message += "\n\n*🔥 Top Pages This Week*"
        for i, page in enumerate(data.get('top_pages', [])[:5], 1):
            title = page.get('title', 'Unknown')[:30]
            views = page.get('views', 0)
            message += f"\n{i}. {title}... - `{views:,}` views"
        
        return message

    def send_daily_report(self, data: Dict) -> bool:
        """Send daily analytics report to Telegram.
        
        Args:
            data: Daily analytics data
            
        Returns:
            True if sent successfully
        """
        message = self.format_daily_report(data)
        return self.send_message(message)

    def send_weekly_report(self, data: Dict) -> bool:
        """Send weekly analytics report to Telegram.
        
        Args:
            data: Weekly analytics data
            
        Returns:
            True if sent successfully
        """
        message = self.format_weekly_report(data)
        return self.send_message(message)
