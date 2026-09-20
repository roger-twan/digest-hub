"""Discord webhook delivery for analytics reports."""

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from report_formatter import ReportFormatter


class DiscordNotifier(ReportFormatter):
    bold = "**"

    def __init__(self, webhook_url: str = None):
        webhook_url = (webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")).strip()
        if not webhook_url:
            raise ValueError("DISCORD_WEBHOOK_URL is required")
        parts = urlsplit(webhook_url)
        query = dict(parse_qsl(parts.query))
        query["wait"] = "true"
        self.webhook_url = urlunsplit(parts._replace(query=urlencode(query)))

    def send_message(self, text: str) -> bool:
        if not text.strip():
            return False
        # Prefer line boundaries so report rows stay readable.
        chunks = []
        while len(text) > 2000:
            boundary = text.rfind("\n", 0, 2001)
            boundary = boundary if boundary > 0 else 2000
            chunks.append(text[:boundary])
            text = text[boundary:]
        if text:
            chunks.append(text)

        for chunk in chunks:
            try:
                response = requests.post(
                    self.webhook_url,
                    json={"content": chunk, "allowed_mentions": {"parse": []}},
                    timeout=30,
                )
                response.raise_for_status()
                message = response.json()
                if not isinstance(message, dict) or not message.get("id"):
                    print("Discord delivery was not confirmed; stopping without retry.")
                    return False
            except (requests.exceptions.RequestException, ValueError):
                # Request exceptions can contain the secret webhook URL.
                print("Discord delivery failed or was not confirmed; stopping without retry.")
                return False
        return True

    def send_daily_report(self, data: dict) -> bool:
        return self.send_message(self.format_daily_report(data))

    def send_weekly_report(self, data: dict) -> bool:
        return self.send_message(self.format_weekly_report(data))
