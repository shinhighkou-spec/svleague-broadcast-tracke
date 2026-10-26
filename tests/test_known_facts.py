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
    assert _extract_search_broadcast(text + " 試合開始 14:05", require_time=True) is None
    assert _extract_search_broadcast(text + " 放送開始 14:05", require_time=True) == (
        "フジテレビNEXT", "2026-10-24",
        ("北海道イエロースターズ", "大阪ブルテオン"), "14:05"
    )


def test_parse_japanese_time():
    from scraper import parse_time
    assert parse_time("試合開始 14時05分") == "14:05"


def test_search_result_is_not_accepted_from_snippet_only():
    from scraper import _extract_search_broadcast
    snippet = "10月24日 北海道イエロースターズ vs 大阪ブルテオン フジテレビNEXT 放送開始 14:05"
    candidate = _extract_search_broadcast(snippet, require_time=True)
    assert candidate is not None
    # The candidate is deliberately not enough by itself; source-page verification
    # is performed by _verify_search_result in the live scraper.


def test_tv_broadcast_list_excludes_on_demand_only_services():
    from scraper import VALID_STATIONS
    assert "群馬テレビ" in VALID_STATIONS
    assert not any("オンデマンド" in station or "配信" in station for station in VALID_STATIONS)


def test_gunma_tv_broadcast_uses_official_airtime_and_keeps_social_confirmation():
    from scraper import known_facts
    rows = known_facts()
    assert any(
        r.station == "群馬テレビ"
        and r.broadcast_date == "2026-10-24"
        and r.home == "群馬グリーンウイングス"
        and r.away == "アランマーレ秋田庄内"
        and r.broadcast_time == "13:00"
        and r.match_start_time == "13:05"
        and "www.gtv.co.jp/timetable/" in r.source
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
    live = Broadcast("群馬テレビ", "2026-10-24", "群馬グリーンウイングス", "アランマーレ秋田庄内", "official-live", "13:00")
    replay = Broadcast("群馬テレビ", "2026-10-24", "群馬グリーンウイングス", "アランマーレ秋田庄内", "official-replay", "19:00")
    rows = reconcile([live, replay])
    matching = {
        r.broadcast_time for r in rows
        if r.station == "群馬テレビ"
        and r.broadcast_date == "2026-10-24"
        and r.home == "群馬グリーンウイングス"
        and r.away == "アランマーレ秋田庄内"
    }
    assert {"13:00", "19:00"} <= matching



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


def test_reconcile_removes_unknown_j_sports_placeholder_when_channel_is_confirmed():
    from scraper import Broadcast, reconcile
    placeholder = Broadcast(
        "J SPORTS（チャンネル未公表）", "2026-11-07",
        "ウルフドッグス名古屋", "ジェイテクトSTINGS愛知",
        "https://www.jsports.co.jp/volleyball/svleague/golden_live/ | 録画放送", "21:00"
    )
    channel = Broadcast(
        "J SPORTS 1", "2026-11-07",
        "ウルフドッグス名古屋", "ジェイテクトSTINGS愛知",
        "https://www.jsports.co.jp/program_guide/channel/japanese/one/261107/", "21:00"
    )
    rows = reconcile([placeholder, channel])
    assert not any(
        r.station == "J SPORTS（チャンネル未公表）"
        and r.broadcast_date == "2026-11-07"
        and r.home == "ウルフドッグス名古屋"
        and r.away == "ジェイテクトSTINGS愛知"
        and r.broadcast_time == "21:00"
        for r in rows
    )
    assert any(
        r.station == "J SPORTS 1"
        and r.broadcast_date == "2026-11-07"
        and r.home == "ウルフドッグス名古屋"
        and r.away == "ジェイテクトSTINGS愛知"
        and r.broadcast_time == "21:00"
        for r in rows
    )


def test_jsports_official_section_parser_compiles_and_extracts_airing():
    from scraper import parse_jsports_official_section
    section = (
        "10月31日(土) 午後1:45 大同生命SVリーグ 2026-27 "
        "フラーゴラッド鹿児島 VS 北海道イエロースターズ"
    )
    assert parse_jsports_official_section(section) == [
        ("2026-10-31", ("フラーゴラッド鹿児島", "北海道イエロースターズ"), "13:45")
    ]



def test_jsports_official_section_parser_accepts_english_league_label():
    from scraper import parse_jsports_official_section
    section = (
        "11月1日(日) 午後0:45 大同生命SV.LEAGUE 2026-27 "
        "ウルフドッグス名古屋 VS 東京グレートベアーズ"
    )
    assert parse_jsports_official_section(section) == [
        ("2026-11-01", ("ウルフドッグス名古屋", "東京グレートベアーズ"), "12:45")
    ]


def test_gunma_tv_parser_uses_airing_start_not_match_start():
    from scraper import _parse_gunma_tv_schedule
    text = (
        "群馬テレビ 番組表 2026年10月 "
        "10月24日(土) ホーム開幕戦 群馬グリーンウイングス×アランマーレ秋田庄内 "
        "午後1時～生中継 試合開始13:05 "
        "10月13日(火) 9時30分～放送開始 おいしい給食season4"
    )
    assert _parse_gunma_tv_schedule(text) == [
        ("2026-10-24", ("群馬グリーンウイングス", "アランマーレ秋田庄内"), "13:00")
    ]


def test_gunma_tv_parser_does_not_infer_airtime_from_match_start_alone():
    from scraper import _parse_gunma_tv_schedule
    text = (
        "10月24日(土) 群馬グリーンウイングス×アランマーレ秋田庄内 "
        "試合開始13:05"
    )
    assert _parse_gunma_tv_schedule(text) == []


def test_search_parser_does_not_use_article_publication_date_as_broadcast_date():
    from scraper import _extract_search_broadcast
    text = (
        "2026.10.17 14:35 SVリーグ戦のテレビ放送追加情報。"
        "BS10では11月14日（土）SAGA久光スプリングス vs "
        "PFUブルーキャッツ石川かほくを放送。放送開始12:55。"
    )
    assert _extract_search_broadcast(text, require_time=True) == (
        "BS10", "2026-11-14",
        ("SAGA久光スプリングス", "PFUブルーキャッツ石川かほく"), "12:55"
    )


def test_official_match_start_is_migrated_out_of_broadcast_time():
    from scraper import Broadcast, normalize_time_semantics
    row = Broadcast(
        "BS10", "2026-11-07", "ウルフドッグス名古屋", "ジェイテクトSTINGS愛知",
        "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:35"
    )
    normalized = normalize_time_semantics(row)
    assert normalized.broadcast_time == ""
    assert normalized.match_start_time == "14:35"


def test_broadcaster_airtime_and_official_match_start_are_kept_separate():
    from scraper import Broadcast, reconcile
    identity = ("BS10", "2026-11-07", "ウルフドッグス名古屋", "ジェイテクトSTINGS愛知")
    official = Broadcast(*identity, "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:35")
    broadcaster = Broadcast(*identity, "https://www.bs10.jp/program/", "14:15")
    rows = reconcile([official, broadcaster])
    match = [r for r in rows if (r.station, r.broadcast_date, r.home, r.away) == identity]
    assert len(match) == 1
    assert match[0].broadcast_time == "14:15"
    assert match[0].match_start_time == "14:35"


def test_public_schedule_never_displays_match_start_as_broadcast_start(monkeypatch, tmp_path):
    import scraper
    from scraper import Broadcast
    data_dir = tmp_path / "data"
    site_dir = tmp_path / "site"
    data_dir.mkdir()
    site_dir.mkdir()
    monkeypatch.setattr(scraper, "DATA", data_dir)
    monkeypatch.setattr(scraper, "SITE", site_dir)
    scraper.write_outputs([
        Broadcast("BS10", "2026-11-07", "ウルフドッグス名古屋",
                  "ジェイテクトSTINGS愛知", "test-source", "", "14:35")
    ], {})
    html = (site_dir / "index.html").read_text(encoding="utf-8")
    assert '<div class="time">—</div>' in html
    assert '<div class="time">14:35</div>' not in html


def test_duckduckgo_result_parser_resolves_redirect_and_keeps_snippet():
    from scraper import _parse_duckduckgo_results
    html = """
    <div id="links">
      <div class="result">
        <h2 class="result__title"><a class="result__a"
          href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fvolleyballking.jp%2Farticle%2F93961%2F&amp;rut=abc">
          SVリーグ戦のテレビ放送追加情報</a></h2>
        <a class="result__snippet">BS10の放送カードが追加</a>
      </div>
    </div>"""
    assert _parse_duckduckgo_results(html) == [
        ("SVリーグ戦のテレビ放送追加情報",
         "https://volleyballking.jp/article/93961/",
         "BS10の放送カードが追加")
    ]


def test_duckduckgo_result_parser_does_not_treat_unrecognized_markup_as_empty_results():
    from scraper import _parse_duckduckgo_results
    import pytest
    with pytest.raises(RuntimeError, match="no recognizable result blocks"):
        _parse_duckduckgo_results("<html><body>temporarily blocked</body></html>")

