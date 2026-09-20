import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from discord_notifier import DiscordNotifier


class DiscordTests(unittest.TestCase):
    def setUp(self):
        self.notifier = DiscordNotifier('https://discord.com/api/webhooks/123/secret?wait=false&thread_id=456')

    def test_missing_config_fails_without_telegram_fallback(self):
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'old', 'TELEGRAM_CHAT_ID': 'old'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'DISCORD_WEBHOOK_URL'):
                DiscordNotifier()

    @patch('discord_notifier.requests.post')
    def test_split_preserves_content_and_disables_mentions(self, post):
        post.return_value = Mock(json=Mock(return_value={'id': '123'}))
        text = ('中文 @everyone\n' * 400) + 'x' * 2500
        self.assertTrue(self.notifier.send_message(text))
        payloads = [call.kwargs['json'] for call in post.call_args_list]
        self.assertEqual(''.join(p['content'] for p in payloads), text)
        self.assertTrue(all(0 < len(p['content']) <= 2000 for p in payloads))
        self.assertTrue(all(p['allowed_mentions'] == {'parse': []} for p in payloads))
        self.assertIn('wait=true', post.call_args.args[0])
        self.assertIn('thread_id=456', post.call_args.args[0])

    @patch('discord_notifier.requests.post')
    def test_failures_stop_without_retry_or_secret_logging(self, post):
        for failure in (requests.Timeout('secret'), requests.HTTPError('secret')):
            post.reset_mock()
            post.side_effect = failure
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertFalse(self.notifier.send_message('x' * 4001))
            post.assert_called_once()
            self.assertNotIn('secret', output.getvalue())

    @patch('discord_notifier.requests.post')
    def test_missing_confirmation_is_failure(self, post):
        for result in ({}, [], None):
            post.return_value = Mock(json=Mock(return_value=result))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(self.notifier.send_message('report'))

    def test_daily_and_weekly_formatting(self):
        data = {'date': '2026-09-19', 'total_users': 1234, 'bounce_rate': .125,
                'avg_session_duration': 125,
                'daily_breakdown': {'20260919': {'users': 1234, 'page_views': 2000}}}
        for formatter in (self.notifier.format_daily_report, self.notifier.format_weekly_report):
            result = formatter(data)
            self.assertIn('**📈 Overview**', result)
            self.assertIn('`1,234`', result)
            self.assertIn('`12.5%`', result)
            self.assertIn('`2m 5s`', result)
        self.assertIn('Sat 09/19', self.notifier.format_weekly_report(data))


if __name__ == '__main__':
    unittest.main()
