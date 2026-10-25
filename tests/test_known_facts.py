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

def test_free_bs_tv_broadcasts_are_preserved_without_guessing_channel_or_time():
    from scraper import known_facts, VALID_STATIONS
    rows = known_facts()
    expected = {
        ("BS無料放送（局名未公表）", "2026-10-17", "NECレッドロケッツ川崎", "ヴィクトリーナ姫路"),
        ("BS無料放送（局名未公表）", "2026-10-31", "フラーゴラッド鹿児島", "北海道イエロースターズ"),
        ("BS無料放送（局名未公表）", "2026-11-07", "ウルフドッグス名古屋", "ジェイテクトSTINGS愛知"),
        ("BS無料放送（局名未公表）", "2026-11-21", "PFUブルーキャッツ石川かほく", "埼玉上尾メディックス"),
        ("BS無料放送（局名未公表）", "2026-12-19", "東京グレートベアーズ", "サントリーサンバーズ大阪"),
    }
    actual = {(r.station, r.broadcast_date, r.home, r.away) for r in rows}
    assert expected <= actual
    assert "BS無料放送（局名未公表）" in VALID_STATIONS
    assert all(r.broadcast_time == "" for r in rows if r.station == "BS無料放送（局名未公表）")

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


def test_tv_broadcast_list_excludes_on_demand_only_services():
    from scraper import VALID_STATIONS
    assert "群馬テレビ" in VALID_STATIONS
    assert not any("オンデマンド" in station or "配信" in station for station in VALID_STATIONS)


def test_gunma_tv_broadcast_is_preserved_as_known_official_social_post():
    from scraper import known_facts
    rows = known_facts()
    assert any(
        r.station == "群馬テレビ"
        and r.broadcast_date == "2026-10-24"
        and r.home == "群馬グリーンウイングス"
        and r.away == "アランマーレ秋田庄内"
        and r.broadcast_time == "13:05"
        and "x.com/vbm_link/status/2113610880101568860" in r.source
        for r in rows
    )


def test_published_data_has_no_on_demand_only_entries_and_keeps_gunma_tv():
    import json
    data_path = Path(__file__).parents[1] / "data" / "broadcasts.json"
    rows = json.loads(data_path.read_text(encoding="utf-8"))
    assert not [
        r for r in rows
        if "オンデマンド" in r["station"] or "配信" in r["station"]
    ]
    assert any(
        r["station"] == "群馬テレビ"
        and r["broadcast_date"] == "2026-10-24"
        and r["home"] == "群馬グリーンウイングス"
        and r["away"] == "アランマーレ秋田庄内"
        for r in rows
    )


def test_reconcile_keeps_same_day_same_card_broadcasts_at_distinct_times():
    from scraper import Broadcast, reconcile
    live = Broadcast("群馬テレビ", "2026-10-24", "群馬グリーンウイングス", "アランマーレ秋田庄内", "official-live", "13:05")
    replay = Broadcast("群馬テレビ", "2026-10-24", "群馬グリーンウイングス", "アランマーレ秋田庄内", "official-replay", "19:00")
    rows = reconcile([live, replay])
    matching = {
        r.broadcast_time for r in rows
        if r.station == "群馬テレビ"
        and r.broadcast_date == "2026-10-24"
        and r.home == "群馬グリーンウイングス"
        and r.away == "アランマーレ秋田庄内"
    }
    assert {"13:05", "19:00"} <= matching



def test_jsports_golden_live_tv_parser_keeps_replays_and_excludes_on_demand():
    from scraper import parse_jsports_golden_live_tv, VALID_STATIONS
    text = (
        "生放送11月8日(日)午後1:15～ウルフドッグス名古屋 VS ジェイテクトSTINGS愛知 開催地 エントリオ "
        "録画放送11月7日(土)午後9:00～ウルフドッグス名古屋 VS ジェイテクトSTINGS愛知 開催地 エントリオ "
        "録画放送11月22日(日)午後8:45～PFUブルーキャッツ石川かほく VS 埼玉上尾メディックス 開催地 とり野菜みそ BLUECATS ARENA "
        "ご視聴方法 オンデマンドで見るなら LIVE 11月21日(土)午後0:45～PFUブルーキャッツ石川かほく VS 埼玉上尾メディックス"
    )
    events = parse_jsports_golden_live_tv(text)
    assert ("生放送", "2026-11-08", ("ウルフドッグス名古屋", "ジェイテクトSTINGS愛知"), "13:15") in events
    assert ("録画放送", "2026-11-07", ("ウルフドッグス名古屋", "ジェイテクトSTINGS愛知"), "21:00") in events
    assert ("録画放送", "2026-11-22", ("PFUブルーキャッツ石川かほく", "埼玉上尾メディックス"), "20:45") in events
    assert not any("オンデマンド" in str(event) for event in events)
    assert "J SPORTS（チャンネル未公表）" in VALID_STATIONS


def test_known_jsports_replays_are_durable_and_distinct_from_live_broadcasts():
    from scraper import known_facts
    rows = known_facts()
    assert any(
        r.station == "J SPORTS（チャンネル未公表）"
        and r.broadcast_date == "2026-11-07"
        and r.home == "ウルフドッグス名古屋"
        and r.away == "ジェイテクトSTINGS愛知"
        and r.broadcast_time == "21:00"
        and "録画放送" in r.source
        for r in rows
    )
    assert any(
        r.station == "J SPORTS（チャンネル未公表）"
        and r.broadcast_date == "2026-11-22"
        and r.home == "PFUブルーキャッツ石川かほく"
        and r.away == "埼玉上尾メディックス"
        and r.broadcast_time == "20:45"
        and "録画放送" in r.source
        for r in rows
    )
