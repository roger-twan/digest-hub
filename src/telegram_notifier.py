"""Telegram Bot for sending analytics notifications."""

import os
import requests
from typing import Dict
from report_formatter import ReportFormatter


class TelegramNotifier(ReportFormatter):
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
