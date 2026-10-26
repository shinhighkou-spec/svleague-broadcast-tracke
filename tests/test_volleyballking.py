import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
import json
import scraper
from scraper import (
    Broadcast,
    _extract_volleyballking_broadcast,
    _extract_volleyballking_jsonld_articles,
    _merge_volleyballking_sitemap_candidates,
    _parse_volleyballking_discovery_document,
    reconcile,
)


def test_volleyballking_article_broadcast_details_are_parsed():
    text = (
        "10月17日(土) テレビ神奈川（tvk）で生中継。"
        "18時30分から放送。NECレッドロケッツ川崎 vs ヴィクトリーナ姫路。"
        "試合開始は18時35分。"
    )
    assert _extract_volleyballking_broadcast(text) == (
        "テレビ神奈川",
        "2026-10-17",
        ("NECレッドロケッツ川崎", "ヴィクトリーナ姫路"),
        "18:30",
    )


def test_volleyballking_publication_date_is_not_used_as_broadcast_date():
    text = (
        "2026.10.11 19:55 テレビ神奈川（tvk）が生中継。"
        "18時30分から放送。NECレッドロケッツ川崎 vs ヴィクトリーナ姫路。"
    )
    assert _extract_volleyballking_broadcast(text) is None


def test_missed_volleyballking_tvk_broadcast_is_in_reconciled_rows():
    rows = reconcile([])
    keys = {(r.station, r.broadcast_date, r.home, r.away) for r in rows}
    assert (
        "テレビ神奈川",
        "2026-10-17",
        "NECレッドロケッツ川崎",
        "ヴィクトリーナ姫路",
    ) in keys
    row = next(r for r in rows if r.station == "テレビ神奈川")
    assert row.broadcast_time == "18:30"
    assert row.source == "known-volleyballking-tvk"


def test_volleyballking_sitemap_discovers_first_party_article_urls_only():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://volleyballking.jp/article/93961/?utm_source=test</loc><lastmod>2026-10-25T10:00:00+09:00</lastmod></url>
      <url><loc>https://volleyballking.jp/league/svleague/</loc><lastmod>2026-10-25</lastmod></url>
      <url><loc>https://example.com/article/12345/</loc><lastmod>2026-10-26</lastmod></url>
    </urlset>"""
    sitemaps, articles, kind = _parse_volleyballking_discovery_document(
        "https://volleyballking.jp/sitemap.xml", xml
    )
    assert kind == "sitemap-urlset"
    assert sitemaps == []
    assert articles == [
        ("https://volleyballking.jp/article/93961/", "2026-10-25T10:00:00+09:00")
    ]


def test_volleyballking_sitemap_index_discovers_child_sitemaps():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://volleyballking.jp/post-sitemap.xml</loc><lastmod>2026-10-26</lastmod></sitemap>
      <sitemap><loc>https://example.com/external.xml</loc><lastmod>2026-10-27</lastmod></sitemap>
    </sitemapindex>"""
    sitemaps, articles, kind = _parse_volleyballking_discovery_document(
        "https://volleyballking.jp/sitemap_index.xml", xml
    )
    assert kind == "sitemap-index"
    assert sitemaps == [("https://volleyballking.jp/post-sitemap.xml", "2026-10-26")]
    assert articles == []


def test_volleyballking_rss_only_supplies_candidates_not_broadcast_facts():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel>
      <item><title>SVリーグ戦のテレビ放送追加情報</title>
        <link>https://volleyballking.jp/article/93961/</link>
        <pubDate>Sun, 25 Oct 2026 10:00:00 +0900</pubDate>
      </item>
    </channel></rss>"""
    sitemaps, articles, kind = _parse_volleyballking_discovery_document(
        "https://volleyballking.jp/feed/", xml
    )
    assert kind == "feed"
    assert sitemaps == []
    assert articles == [("https://volleyballking.jp/article/93961/", "Sun, 25 Oct 2026 10:00:00 +0900")]
    # Publication time is retained only as discovery metadata; it is not a broadcast date.
    assert _extract_volleyballking_broadcast("SVリーグ戦のテレビ放送追加情報 2026.10.25 10:00") is None


def test_volleyballking_jsonld_finds_broadcast_related_article_candidates():
    scripts = [json.dumps({
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "SVリーグ戦のテレビ放送追加情報",
        "url": "https://volleyballking.jp/article/93961/?from=jsonld",
    }, ensure_ascii=False)]
    assert _extract_volleyballking_jsonld_articles(scripts) == [
        ("https://volleyballking.jp/article/93961/", "SVリーグ戦のテレビ放送追加情報")
    ]


def test_public_schedule_labels_broadcast_start_time_not_match_start(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    site_dir = tmp_path / "site"
    data_dir.mkdir()
    site_dir.mkdir()
    monkeypatch.setattr(scraper, "DATA", data_dir)
    monkeypatch.setattr(scraper, "SITE", site_dir)
    scraper.write_outputs([
        Broadcast("BS10", "2026-11-07", "ウルフドッグス名古屋",
                  "ジェイテクトSTINGS愛知", "test-source", "14:35")
    ], {})
    html = (site_dir / "index.html").read_text(encoding="utf-8")
    assert "<div>放送開始</div>" in html
    assert "<div>試合開始</div>" not in html
    assert "放送開始時刻" in html
    assert '<div class="time">14:35</div>' in html


def test_volleyballking_child_sitemaps_without_lastmod_are_not_dropped():
    target = {}
    _merge_volleyballking_sitemap_candidates(
        target,
        [
            ("https://volleyballking.jp/post-sitemap-2026-10.xml", ""),
            ("https://volleyballking.jp/post-sitemap-2026-09.xml", "2026-09-30"),
            ("https://volleyballking.jp/visited-sitemap.xml", ""),
        ],
        {"https://volleyballking.jp/visited-sitemap.xml"},
    )
    assert target == {
        "https://volleyballking.jp/post-sitemap-2026-10.xml": "",
        "https://volleyballking.jp/post-sitemap-2026-09.xml": "2026-09-30",
    }
    _merge_volleyballking_sitemap_candidates(
        target,
        [("https://volleyballking.jp/post-sitemap-2026-10.xml", "2026-10-26")],
        set(),
    )
    assert target["https://volleyballking.jp/post-sitemap-2026-10.xml"] == "2026-10-26"


def test_source_discovery_degradation_is_exposed_to_github_actions(monkeypatch, tmp_path):
    env_file = tmp_path / "github_env"
    monkeypatch.setenv("GITHUB_ENV", str(env_file))
    scraper.flag_source_discovery_degraded("Bing unavailable")
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "SV_SOURCE_DISCOVERY_DEGRADED=true"
    ]


def test_social_search_results_are_deduplicated_without_losing_distinct_urls():
    from scraper import _unique_search_results
    seen = set()
    results = [
        ("first", "https://x.com/team/status/123?s=20", "snippet one"),
        ("same page", "https://x.com/team/status/123#timeline", "snippet two"),
        ("different page", "https://x.com/team/status/124", "snippet three"),
    ]
    unique = _unique_search_results(results, seen)
    assert [item[0] for item in unique] == ["first", "different page"]
    assert _unique_search_results([results[1]], seen) == []
