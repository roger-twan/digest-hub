import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from trending_client import TrendingError, parse_trending

FIXTURES = Path(__file__).resolve().parent / 'fixtures'

MINIMAL_ROW = """
<article class="Box-row">
  <h2><a href="/acme/widget">acme / widget</a></h2>
  <p class="col-9 color-fg-muted my-1 pr-4">A tiny widget.</p>
  <div>
    <a href="/acme/widget/stargazers">1,234</a>
    <a href="/acme/widget/forks">56</a>
  </div>
  <div><span class="d-inline-block float-sm-right">10 stars today</span></div>
</article>
"""


def load(name: str) -> str:
    return (FIXTURES / name).read_text()


class ParseTests(unittest.TestCase):
    def test_daily_rows(self):
        repos = parse_trending(load('trending_daily.html'))
        self.assertEqual(len(repos), 3)

        first = repos[0]
        self.assertEqual(first['repo'], 'zed-industries/zed')
        self.assertEqual(first['url'], 'https://github.com/zed-industries/zed')
        self.assertEqual(first['language'], 'Rust')
        self.assertTrue(first['description'])
        self.assertGreater(first['stars'], 0)

    def test_rows_are_sorted_by_total_stars(self):
        for since, fixture in (('daily', 'trending_daily.html'),
                               ('weekly', 'trending_weekly.html')):
            stars = [repo['stars'] for repo in parse_trending(load(fixture), since=since)]
            self.assertEqual(stars, sorted(stars, reverse=True), since)
            self.assertEqual(stars[0], max(stars), since)

    def test_rows_carry_only_star_totals(self):
        repo = parse_trending(load('trending_daily.html'))[0]
        self.assertNotIn('period', repo)
        self.assertNotIn('period_stars', repo)

    def test_limit_keeps_trending_selection_then_sorts(self):
        repos = parse_trending(load('trending_daily.html'), limit=2)
        self.assertEqual(len(repos), 2)
        self.assertEqual([r['repo'] for r in repos], ['zed-industries/zed', 'NVIDIA/auto-ontology'])
        self.assertEqual(len(parse_trending(load('trending_daily.html'), limit=0)), 3)

    def test_missing_language_is_none(self):
        repo = parse_trending(MINIMAL_ROW)[0]
        self.assertIsNone(repo['language'])
        self.assertEqual(repo['repo'], 'acme/widget')
        self.assertEqual(repo['stars'], 1234)
        self.assertEqual(repo['forks'], 56)

    def test_empty_page_raises(self):
        with self.assertRaisesRegex(TrendingError, 'markup may have changed'):
            parse_trending('<html><body><p>nothing here</p></body></html>')

    def test_invalid_period_raises(self):
        with self.assertRaises(ValueError):
            parse_trending(load('trending_daily.html'), since='monthly')


if __name__ == '__main__':
    unittest.main()
