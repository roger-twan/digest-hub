"""Gmail SMTP delivery for analytics reports.

The report is sent as a multipart message: a plain-text part for clients that
prefer it, plus a styled HTML part. No third-party mail library is needed.
"""

import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import escape
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_TIMEOUT = 30


def _num(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _duration(seconds) -> str:
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        total = 0
    return f"{total // 60}m {total % 60}s"


def _percent(rate) -> str:
    try:
        return f"{float(rate) * 100:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def _truncate(text, limit: int) -> str:
    text = " ".join(str(text).split()) or "Unknown"
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _kpis(title: str, items: Sequence[Tuple[str, str]]) -> Dict:
    return {"type": "kpis", "title": title, "items": list(items)}


def _ranked(title: str, rows: Sequence[Tuple[str, str]], unit: str) -> Optional[Dict]:
    if not rows:
        return None
    return {"type": "ranked", "title": title, "rows": list(rows), "unit": unit}


def _daily(title: str, rows: Sequence[Tuple[str, str, str]]) -> Optional[Dict]:
    if not rows:
        return None
    return {"type": "daily", "title": title, "rows": list(rows)}


def _countries(data: Dict) -> List[Tuple[str, str]]:
    rows = []
    for country in data.get("top_countries", [])[:5]:
        rows.append((_truncate(country.get("country", "Unknown"), 32), _num(country.get("users"))))
    return rows


def _pages(data: Dict) -> List[Tuple[str, str]]:
    rows = []
    for page in data.get("top_pages", [])[:5]:
        rows.append((_truncate(page.get("title", "Untitled"), 48), _num(page.get("views"))))
    return rows


class EmailNotifier:
    """Send analytics reports to an inbox through Gmail's SMTP server."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        recipient: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.username = (username if username is not None else os.getenv("GMAIL_USER", "")).strip()
        raw_password = password if password is not None else os.getenv("GMAIL_APP_PASSWORD", "")
        # Google shows app passwords in groups of four; the spaces are cosmetic.
        self.password = "".join(str(raw_password).split())
        if not self.username:
            raise ValueError("GMAIL_USER is required")
        if not self.password:
            raise ValueError("GMAIL_APP_PASSWORD is required")

        raw_recipient = recipient if recipient is not None else os.getenv("EMAIL_TO", "")
        addresses = [part.strip() for part in raw_recipient.split(",") if part.strip()]
        self.recipients = addresses or [self.username]
        self.recipient = ", ".join(self.recipients)

        self.host = (host or os.getenv("SMTP_HOST") or DEFAULT_SMTP_HOST).strip()
        self.port = int(port or os.getenv("SMTP_PORT") or DEFAULT_SMTP_PORT)
        self.timeout = timeout

    # -- delivery ---------------------------------------------------------
    def send_message(self, subject: str, text: str, html: Optional[str] = None) -> bool:
        """Send one email. Returns True only when the server accepts it."""
        message = EmailMessage()
        message["From"] = f"GA4 Analytics Digest <{self.username}>"
        message["To"] = self.recipient
        message["Subject"] = subject
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid()
        message["X-Mailer"] = "analytics-digest"
        message.set_content(text)
        if html:
            message.add_alternative(html, subtype="html")
        return self._deliver(message)

    def _deliver(self, message: EmailMessage) -> bool:
        try:
            context = ssl.create_default_context()
            if self.port == 465:
                client = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout, context=context)
            else:
                client = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            with client:
                client.ehlo()
                if self.port != 465:
                    client.starttls(context=context)
                    client.ehlo()
                client.login(self.username, self.password)
                client.send_message(message)
            return True
        except smtplib.SMTPAuthenticationError as exc:
            # Never echo the password or the full server transcript.
            print(
                f"Email delivery failed: Gmail rejected the credentials "
                f"(code {exc.smtp_code}). Use a 16-character app password, not your account password."
            )
            return False
        except smtplib.SMTPResponseException as exc:
            print(f"Email delivery failed: SMTP error {exc.smtp_code}.")
            return False
        except (smtplib.SMTPException, OSError) as exc:
            print(f"Email delivery failed: {type(exc).__name__}.")
            return False

    # -- report models ----------------------------------------------------
    def build_daily(self, data: Dict) -> Dict:
        date = str(data.get("date", "Unknown"))
        blocks = [
            _kpis("📈 Overview", [
                ("Total Users", _num(data.get("total_users"))),
                ("New Users", _num(data.get("new_users"))),
                ("Sessions", _num(data.get("total_sessions"))),
                ("Page Views", _num(data.get("total_page_views"))),
            ]),
            _kpis("🔍 Engagement", [
                ("Avg Session Duration", _duration(data.get("avg_session_duration"))),
                ("Bounce Rate", _percent(data.get("bounce_rate"))),
            ]),
            _ranked("🌍 Top Countries", _countries(data), "users"),
            _ranked("🔥 Top Pages", _pages(data), "views"),
        ]
        return {
            "subject": f"📊 Daily Analytics Report - {date}",
            "heading": "Daily Analytics Report",
            "subheading": date,
            "blocks": [block for block in blocks if block],
        }

    def build_weekly(self, data: Dict) -> Dict:
        start_date = str(data.get("start_date", "Unknown"))
        end_date = str(data.get("end_date", "Unknown"))

        breakdown = []
        for raw_date in sorted(data.get("daily_breakdown", {})):
            day = data["daily_breakdown"][raw_date]
            try:
                label = datetime.strptime(raw_date, "%Y%m%d").strftime("%a %m/%d")
            except ValueError:
                label = raw_date
            breakdown.append((label, _num(day.get("users")), _num(day.get("page_views"))))

        blocks = [
            _kpis("📈 Overview", [
                ("Total Users", _num(data.get("total_users"))),
                ("New Users", _num(data.get("new_users"))),
                ("Sessions", _num(data.get("total_sessions"))),
                ("Page Views", _num(data.get("total_page_views"))),
            ]),
            _kpis("🔍 Engagement", [
                ("Avg Session Duration", _duration(data.get("avg_session_duration"))),
                ("Bounce Rate", _percent(data.get("bounce_rate"))),
            ]),
            _daily("📅 Daily Breakdown", breakdown),
            _ranked("🌍 Top Countries This Week", _countries(data), "users"),
            _ranked("🔥 Top Pages This Week", _pages(data), "views"),
        ]
        return {
            "subject": f"📊 Weekly Analytics Report - {start_date} to {end_date}",
            "heading": "Weekly Analytics Report",
            "subheading": f"{start_date} to {end_date}",
            "blocks": [block for block in blocks if block],
        }

    # -- rendering --------------------------------------------------------
    def render_text(self, doc: Dict) -> str:
        heading = doc["heading"]
        lines = [heading, "=" * len(heading), ""]
        subheading = doc.get("subheading")
        if subheading:
            lines.extend([subheading, ""])

        for block in doc["blocks"]:
            lines.append(block["title"])
            if block["type"] == "kpis":
                width = max(len(label) for label, _ in block["items"])
                lines.extend(f"  {label.ljust(width)}  {value}" for label, value in block["items"])
            elif block["type"] == "ranked":
                lines.extend(
                    f"  {index}. {name} - {value} {block['unit']}"
                    for index, (name, value) in enumerate(block["rows"], 1)
                )
            elif block["type"] == "daily":
                lines.extend(
                    f"  {day}: {users} users, {views} views"
                    for day, users, views in block["rows"]
                )
            lines.append("")

        lines.extend(["--", f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · Google Analytics 4"])
        return "\n".join(lines)

    def render_html(self, doc: Dict) -> str:
        sections = []
        for block in doc["blocks"]:
            if block["type"] == "kpis":
                sections.append(self._html_kpis(block))
            elif block["type"] == "ranked":
                sections.append(self._html_ranked(block))
            elif block["type"] == "daily":
                sections.append(self._html_daily(block))
        return self._html_shell(doc, "".join(sections))

    @staticmethod
    def _html_shell(doc: Dict, body: str) -> str:
        heading = escape(doc["heading"])
        subheading = escape(doc.get("subheading") or "")
        generated = escape(datetime.now().strftime("%Y-%m-%d %H:%M"))
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{heading}</title>
</head>
<body style="margin:0;padding:0;background-color:#eef0f4;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#eef0f4;padding:24px 12px;">
  <tr>
    <td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%;background-color:#ffffff;border-radius:14px;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1f2933;">
        <tr>
          <td style="background-color:#111827;padding:26px 30px;">
            <div style="font-size:12px;letter-spacing:1.6px;text-transform:uppercase;color:#9ca3af;">GA4 Analytics Digest</div>
            <div style="font-size:24px;font-weight:600;color:#ffffff;margin-top:6px;">{heading}</div>
            <div style="font-size:14px;color:#cbd5e1;margin-top:4px;">{subheading}</div>
          </td>
        </tr>
        <tr>
          <td style="padding:26px 30px 6px;">{body}</td>
        </tr>
        <tr>
          <td style="padding:18px 30px;background-color:#f9fafb;font-size:12px;color:#6b7280;border-top:1px solid #e5e7eb;">
            Generated {generated} · Google Analytics 4
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""

    @staticmethod
    def _section_title(title: str) -> str:
        return (
            f'<div style="font-size:16px;font-weight:600;color:#111827;margin:0 0 12px;">'
            f"{escape(title)}</div>"
        )

    @classmethod
    def _html_kpis(cls, block: Dict) -> str:
        items = block["items"]
        rows = []
        for index in range(0, len(items), 2):
            cells = []
            for label, value in items[index:index + 2]:
                cells.append(
                    '<td width="50%" style="padding:6px;vertical-align:top;">'
                    '<div style="border:1px solid #e5e7eb;border-radius:10px;padding:14px 16px;">'
                    f'<div style="font-size:11px;letter-spacing:.9px;text-transform:uppercase;color:#6b7280;">{escape(label)}</div>'
                    f'<div style="font-size:22px;font-weight:600;color:#111827;margin-top:6px;">{escape(value)}</div>'
                    "</div></td>"
                )
            if len(items[index:index + 2]) == 1:
                cells.append('<td width="50%"></td>')
            rows.append(f"<tr>{''.join(cells)}</tr>")
        return (
            '<div style="margin-bottom:26px;">'
            + cls._section_title(block["title"])
            + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
              'style="border-collapse:separate;">'
            + "".join(rows)
            + "</table></div>"
        )

    @classmethod
    def _html_ranked(cls, block: Dict) -> str:
        rows = []
        for index, (name, value) in enumerate(block["rows"], 1):
            border = "" if index == len(block["rows"]) else "border-bottom:1px solid #f1f3f5;"
            rows.append(
                "<tr>"
                f'<td style="padding:9px 0;{border}width:26px;color:#9ca3af;font-size:13px;">{index}</td>'
                f'<td style="padding:9px 0;{border}font-size:14px;color:#1f2933;">{escape(name)}</td>'
                f'<td align="right" style="padding:9px 0;{border}font-size:14px;font-weight:600;color:#111827;white-space:nowrap;">'
                f"{escape(value)} <span style=\"font-weight:400;color:#6b7280;\">{escape(block['unit'])}</span></td>"
                "</tr>"
            )
        return (
            '<div style="margin-bottom:26px;">'
            + cls._section_title(block["title"])
            + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
            + "".join(rows)
            + "</table></div>"
        )

    @classmethod
    def _html_daily(cls, block: Dict) -> str:
        rows = []
        for index, (day, users, views) in enumerate(block["rows"]):
            border = "" if index == len(block["rows"]) - 1 else "border-bottom:1px solid #f1f3f5;"
            rows.append(
                "<tr>"
                f'<td style="padding:9px 0;{border}font-size:14px;color:#1f2933;">{escape(day)}</td>'
                f'<td align="right" style="padding:9px 0;{border}font-size:14px;color:#1f2933;">{escape(users)} users</td>'
                f'<td align="right" style="padding:9px 0;{border}font-size:14px;font-weight:600;color:#111827;">{escape(views)} views</td>'
                "</tr>"
            )
        return (
            '<div style="margin-bottom:26px;">'
            + cls._section_title(block["title"])
            + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
            + "".join(rows)
            + "</table></div>"
        )

    # -- public senders ---------------------------------------------------
    def send_daily_report(self, data: Dict) -> bool:
        doc = self.build_daily(data)
        return self.send_message(doc["subject"], self.render_text(doc), self.render_html(doc))

    def send_weekly_report(self, data: Dict) -> bool:
        doc = self.build_weekly(data)
        return self.send_message(doc["subject"], self.render_text(doc), self.render_html(doc))
