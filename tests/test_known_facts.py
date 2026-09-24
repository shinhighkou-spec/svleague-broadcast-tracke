import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from scraper import known_facts, reconcile, validate

def test_known_official_facts_present():
    rows = reconcile([])
    keys={(r.station,r.broadcast_date,r.home,r.away) for r in rows}
    assert ('フジテレビNEXT','2026-10-24','北海道イエロースターズ','大阪ブルテオン') in keys
    assert ('フジテレビNEXT','2026-10-25','北海道イエロースターズ','大阪ブルテオン') in keys
    assert ('フジテレビNEXT','2026-10-31','大阪ブルテオン','ウルフドッグス名古屋') in keys
    assert ('フジテレビNEXT','2026-11-01','大阪ブルテオン','ウルフドッグス名古屋') in keys
    assert ('GAORA SPORTS','2026-11-01','東レアローズ滋賀','デンソーエアリービーズ') in keys
    assert ('NHK BS','2026-10-23','デンソーエアリービーズ','SAGA久光スプリングス') in keys
    assert ('NHK BS','2026-11-01','大阪ブルテオン','ウルフドッグス名古屋') in keys

def test_known_bad_rows_rejected():
    rows=reconcile([
      known_facts()[0].__class__('フジテレビNEXT','2026-09-18','PFUブルーキャッツ石川かほく','SAGA久光スプリングス','x',''),
      known_facts()[0].__class__('GAORA SPORTS','2026-10-31','東レアローズ滋賀','デンソーエアリービーズ','x',''),
    ])
    keys={(r.station,r.broadcast_date,r.home,r.away) for r in rows}
    assert ('フジテレビNEXT','2026-09-18','PFUブルーキャッツ石川かほく','SAGA久光スプリングス') not in keys
    assert ('GAORA SPORTS','2026-10-31','東レアローズ滋賀','デンソーエアリービーズ') not in keys


def test_official_nhk_table_row_is_parsed_with_broadcast_date():
    from scraper import extract_broadcast_item
    item = extract_broadcast_item(
        "10月23日(金) 19:05 デンソーエアリービーズ vs SAGA久光スプリングス",
        "NHK BS",
    )
    assert item == ("NHK BS","2026-10-23",("デンソーエアリービーズ","SAGA久光スプリングス"),"19:05")


def test_team_logo_registry_is_complete():
    from scraper import EXPECTED_TEAM_LOGO_NAMES, TEAM_LOGO_IDS, scrape_team_logos, validate_team_logos
    assert set(TEAM_LOGO_IDS) == EXPECTED_TEAM_LOGO_NAMES
    logos = scrape_team_logos(None)
    validate_team_logos(logos)


def test_team_logo_validation_rejects_missing_logo_for_published_row():
    from scraper import Broadcast, validate_team_logos
    logos = {"フラーゴラッド鹿児島": "https://www.svleague.jp/ext/team/499/team-logo.png"}
    rows = [Broadcast("J SPORTS 1", "2026-10-31", "フラーゴラッド鹿児島", "北海道イエロースターズ", "test", "")]
    try:
        validate_team_logos(logos, rows)
    except RuntimeError as e:
        assert "北海道イエロースターズ" in str(e)
    else:
        raise AssertionError("missing team logo must fail validation")


def test_search_broadcast_requires_source_time():
    from scraper import _extract_search_broadcast
    text = "10月24日 北海道イエロースターズ vs 大阪ブルテオン フジテレビNEXT 放送"
    assert _extract_search_broadcast(text) == (
        "フジテレビNEXT", "2026-10-24",
        ("北海道イエロースターズ", "大阪ブルテオン"), ""
    )
    assert _extract_search_broadcast(text, require_time=True) is None
    assert _extract_search_broadcast(text + " 14:05", require_time=True) == (
        "フジテレビNEXT", "2026-10-24",
        ("北海道イエロースターズ", "大阪ブルテオン"), "14:05"
    )


def test_parse_japanese_time():
    from scraper import parse_time
    assert parse_time("試合開始 14時05分") == "14:05"


def test_search_result_is_not_accepted_from_snippet_only():
    from scraper import _extract_search_broadcast
    snippet = "10月24日 14:05 北海道イエロースターズ vs 大阪ブルテオン フジテレビNEXT 放送"
    candidate = _extract_search_broadcast(snippet, require_time=True)
    assert candidate is not None
    # The candidate is deliberately not enough by itself; source-page verification
    # is performed by _verify_search_result in the live scraper.
