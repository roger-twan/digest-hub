import contextlib
import io
import os
from pathlib import Path
import smtplib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from email_notifier import EmailNotifier

DAILY = {
    'date': '2026-09-19',
    'total_users': 1234,
    'new_users': 200,
    'total_sessions': 1500,
    'total_page_views': 2345,
    'avg_session_duration': 125,
    'bounce_rate': .125,
    'top_countries': [{'country': 'United States', 'users': 900}],
    'top_pages': [{'title': 'Home', 'views': 1111}],
}

WEEKLY = {
    'start_date': '2026-09-13',
    'end_date': '2026-09-19',
    'total_users': 5000,
    'new_users': 800,
    'total_sessions': 6000,
    'total_page_views': 9000,
    'avg_session_duration': 130,
    'bounce_rate': .2,
    'daily_breakdown': {'20260919': {'users': 1234, 'page_views': 2000}},
    'top_countries': [],
    'top_pages': [],
}


def fake_client():
    client = MagicMock()
    client.__enter__.return_value = client
    return client


class ConfigTests(unittest.TestCase):
    def test_missing_credentials_name_the_variable(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'GMAIL_USER'):
                EmailNotifier()
            with self.assertRaisesRegex(ValueError, 'GMAIL_APP_PASSWORD'):
                EmailNotifier(username='sender@example.com')

    def test_defaults_and_app_password_normalisation(self):
        env = {'GMAIL_USER': 'sender@example.com', 'GMAIL_APP_PASSWORD': 'abcd efgh ijkl mnop'}
        with patch.dict(os.environ, env, clear=True):
            notifier = EmailNotifier()
        self.assertEqual(notifier.password, 'abcdefghijklmnop')
        self.assertEqual(notifier.recipient, 'sender@example.com')
        self.assertEqual(notifier.host, 'smtp.gmail.com')
        self.assertEqual(notifier.port, 587)

    def test_recipient_list_and_override(self):
        notifier = EmailNotifier(username='sender@example.com', password='x',
                                 recipient='a@example.com, b@example.com')
        self.assertEqual(notifier.recipients, ['a@example.com', 'b@example.com'])
        self.assertEqual(notifier.recipient, 'a@example.com, b@example.com')


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.notifier = EmailNotifier(username='sender@example.com', password='letmein app')

    @patch('email_notifier.smtplib.SMTP')
    def test_starttls_delivery_builds_multipart_message(self, smtp):
        client = smtp.return_value = fake_client()
        self.assertTrue(self.notifier.send_daily_report(DAILY))

        client.starttls.assert_called_once()
        client.login.assert_called_once_with('sender@example.com', 'letmeinapp')
        message = client.send_message.call_args.args[0]
        self.assertEqual(message['To'], 'sender@example.com')
        self.assertIn('Daily Analytics Report', message['Subject'])
        self.assertIn('2026-09-19', message['Subject'])
        self.assertIsNotNone(message.get_body(('plain',)))
        self.assertIsNotNone(message.get_body(('html',)))

    @patch('email_notifier.smtplib.SMTP_SSL')
    @patch('email_notifier.smtplib.SMTP')
    def test_port_465_uses_implicit_tls(self, smtp, smtp_ssl):
        client = smtp_ssl.return_value = fake_client()
        notifier = EmailNotifier(username='sender@example.com', password='x', port=465)
        self.assertTrue(notifier.send_weekly_report(WEEKLY))
        smtp.assert_not_called()
        client.starttls.assert_not_called()
        self.assertIn('Weekly Analytics Report', client.send_message.call_args.args[0]['Subject'])

    @patch('email_notifier.smtplib.SMTP')
    def test_auth_failure_is_reported_without_leaking_the_password(self, smtp):
        client = smtp.return_value = fake_client()
        client.login.side_effect = smtplib.SMTPAuthenticationError(535, b'bad credentials')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertFalse(self.notifier.send_daily_report(DAILY))
        self.assertIn('rejected the credentials', output.getvalue())
        self.assertNotIn('letmeinapp', output.getvalue())
        self.assertNotIn('letmein app', output.getvalue())

    @patch('email_notifier.smtplib.SMTP')
    def test_connection_errors_return_false(self, smtp):
        for failure in (smtplib.SMTPServerDisconnected('secret'), OSError('secret'),
                        smtplib.SMTPRecipientsRefused({'secret@example.com': (550, b'no')})):
            client = smtp.return_value = fake_client()
            client.send_message.side_effect = failure
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertFalse(self.notifier.send_message('subject', 'body'))
            self.assertNotIn('secret', output.getvalue())


class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.notifier = EmailNotifier(username='sender@example.com', password='x')

    def test_daily_text_and_html_metrics(self):
        doc = self.notifier.build_daily(DAILY)
        text = self.notifier.render_text(doc)
        html = self.notifier.render_html(doc)
        for value in ('1,234', '12.5%', '2m 5s', 'United States', 'Home'):
            self.assertIn(value, text)
            self.assertIn(value, html)
        self.assertIn('<!DOCTYPE html>', html)

    def test_weekly_includes_daily_breakdown(self):
        doc = self.notifier.build_weekly(WEEKLY)
        self.assertIn('Sat 09/19', self.notifier.render_text(doc))
        self.assertIn('Sat 09/19', self.notifier.render_html(doc))
        self.assertEqual(doc['subheading'], '2026-09-13 to 2026-09-19')

    def test_html_escapes_page_titles(self):
        data = dict(DAILY, top_pages=[{'title': '<script>alert("x")</script>', 'views': 1}])
        html = self.notifier.render_html(self.notifier.build_daily(data))
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_empty_sections_are_dropped(self):
        data = dict(DAILY, top_pages=[], top_countries=[])
        doc = self.notifier.build_daily(data)
        self.assertNotIn('Top Pages', self.notifier.render_text(doc))


if __name__ == '__main__':
    unittest.main()
