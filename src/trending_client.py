"""Fetch GitHub Trending and expose it as digest rows.

GitHub has no Trending API: https://github.com/trending is server-rendered
HTML. All selector knowledge lives here so that a markup change only needs
a fix in one module.
"""

import re
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

TRENDING_URL = "https://github.com/trending"
USER_AGENT = (
    "Mozilla/5.0 (compatible; digest-hub/1.0; "
    "+https://github.com/roger-twan/digest-hub)"
)
TIMEOUT = 30
DEFAULT_LIMIT = 10
PERIODS = ("daily", "weekly")


class TrendingError(RuntimeError):
    """Raised when the Trending page cannot be turned into rows."""


def _text(node) -> str:
    """Collapse an element's text; empty string when it is missing."""
    if node is None:
        return ""
    return " ".join(node.get_text(" ", strip=True).split())


def _count(text: str) -> int:
    digits = re.sub(r"[^0-9]", "", text or "")
    return int(digits) if digits else 0


def parse_trending(html: str, since: str = "daily", limit: int = DEFAULT_LIMIT) -> List[Dict]:
    """Parse a Trending page into repositories in GitHub's trending order."""
    if since not in PERIODS:
        raise ValueError(f"since must be one of {list(PERIODS)}")

    soup = BeautifulSoup(html, "html.parser")
    rows: List[Dict] = []

    for article in soup.select("article.Box-row"):
        link = article.select_one("h2 a")
        name = (link.get("href") or "").strip().strip("/") if link else ""
        if name.count("/") != 1:
            continue

        rows.append({
            "repo": name,
            "url": f"https://github.com/{name}",
            "description": _text(article.select_one("p")),
            "language": _text(article.select_one('[itemprop="programmingLanguage"]')) or None,
            "stars": _count(_text(article.select_one('a[href$="/stargazers"]'))),
            "forks": _count(_text(article.select_one('a[href$="/forks"]'))),
        })

    if not rows:
        raise TrendingError(
            "GitHub Trending returned no repositories; the page markup may have changed."
        )
    # Keep GitHub's own trending order; it already ranks by momentum.
    return rows[:limit] if limit else rows


def fetch_trending(since: str = "daily", limit: int = DEFAULT_LIMIT,
                   timeout: int = TIMEOUT) -> List[Dict]:
    """Download and parse the Trending page for the given period."""
    if since not in PERIODS:
        raise ValueError(f"since must be one of {list(PERIODS)}")

    response = requests.get(
        TRENDING_URL,
        params={"since": since},
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        timeout=timeout,
    )
    response.raise_for_status()
    return parse_trending(response.text, since=since, limit=limit)
