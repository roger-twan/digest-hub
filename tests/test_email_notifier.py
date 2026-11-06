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


TRENDING = [
    {
        'repo': 'zed-industries/zed',
        'description': 'Code at the speed of thought',
        'language': 'Rust',
        'stars': 93138,
    },
    {
        'repo': 'acme/widget',
        'description': '',
        'language': None,
        'stars': 5,
    },
]


class TrendingRenderingTests(unittest.TestCase):
    def setUp(self):
        self.notifier = EmailNotifier(username='sender@example.com', password='x')

    def test_text_and_html_include_repo_details(self):
        doc = self.notifier.build_trending(TRENDING, 'daily')
        text = self.notifier.render_text(doc)
        html = self.notifier.render_html(doc)

        self.assertIn('GitHub Trending Daily', doc['subject'])
        self.assertIn('zed-industries/zed', text)
        self.assertIn('93,138 total', text)
        self.assertIn('Rust', text)
        self.assertNotIn('stars today', text)
        self.assertNotIn('+292', text)
        self.assertIn('https://github.com/zed-industries/zed', html)
        self.assertIn('GitHub Trending', html)
        self.assertNotIn('Google Analytics 4', html)
        self.assertNotIn('GA4', html)

    def test_repo_rows_do_not_carry_a_raw_url(self):
        doc = self.notifier.build_trending(TRENDING, 'daily')
        row = doc['blocks'][0]['rows'][0]
        self.assertNotIn('url', row)
        self.assertEqual(row['name'], 'zed-industries/zed')

    def test_html_links_repo_name_to_github(self):
        html = self.notifier.render_html(self.notifier.build_trending(TRENDING, 'daily'))
        self.assertIn('href="https://github.com/zed-industries/zed"', html)
        self.assertIn('>zed-industries/zed</a>', html)

    def test_repos_keep_input_order(self):
        doc = self.notifier.build_trending([TRENDING[1], TRENDING[0]], 'daily')
        names = [row['name'] for row in doc['blocks'][0]['rows']]
        self.assertEqual(names, ['acme/widget', 'zed-industries/zed'])

        text = self.notifier.render_text(doc)
        self.assertLess(text.index('acme/widget'), text.index('zed-industries/zed'))

    def test_weekly_subject_and_source(self):
        doc = self.notifier.build_trending(TRENDING, 'weekly')
        self.assertIn('Weekly', doc['subject'])
        self.assertEqual(doc['source'], 'GitHub Trending')
        self.assertIn('Trending This Week', self.notifier.render_text(doc))

    def test_digest_headers_follow_the_source(self):
        with patch('email_notifier.smtplib.SMTP') as smtp:
            client = smtp.return_value = fake_client()
            self.assertTrue(self.notifier.send_trending_report(TRENDING, 'daily'))

        message = client.send_message.call_args.args[0]
        self.assertEqual(message['From'], 'GitHub Trending Digest <sender@example.com>')
        self.assertEqual(message['X-Mailer'], 'digest-hub')


class ResponsiveMarkupTests(unittest.TestCase):
    def setUp(self):
        self.notifier = EmailNotifier(username='sender@example.com', password='x')

    def render(self, doc):
        return self.notifier.render_html(doc)

    def test_viewport_and_color_scheme_meta(self):
        html = self.render(self.notifier.build_trending(TRENDING, 'daily'))
        self.assertIn('name="viewport" content="width=device-width, initial-scale=1"', html)
        self.assertIn('name="color-scheme" content="light dark"', html)

    def test_mobile_media_query_stacks_kpis(self):
        html = self.render(self.notifier.build_daily(DAILY))
        self.assertIn('@media (max-width: 480px)', html)
        self.assertIn('.kpi { display: block', html)
        self.assertIn('.pad { padding-left: 18px', html)
        self.assertIn('.kpi-value { font-size: 20px', html)

    def test_card_is_fluid_up_to_600px(self):
        html = self.render(self.notifier.build_daily(DAILY))
        self.assertIn('width:100%;max-width:600px', html)

    def test_long_tokens_can_wrap(self):
        long_name = 'owner/' + 'a' * 80
        html = self.render(self.notifier.build_trending(
            [dict(TRENDING[0], repo=long_name)], 'daily'))
        self.assertIn('word-break:break-word', html)
        self.assertIn('overflow-wrap:anywhere', html)

    def test_links_are_visually_distinct(self):
        html = self.render(self.notifier.build_trending(TRENDING, 'daily'))
        self.assertIn('color:#2563eb', html)
        self.assertIn('text-decoration:underline', html)


if __name__ == '__main__':
    unittest.main()
