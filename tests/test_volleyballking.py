import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from scraper import (
    Broadcast, VOLLEYBALLKING_LISTING_URLS, _extract_typed_times,
    _extract_volleyballking_broadcast, _should_inspect_volleyballking_article, reconcile,
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
        "18:35",
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
    assert row.match_time == "18:35"
    assert row.source == "known-volleyballking-tvk"


def test_real_news_pagination_is_scanned_even_without_tv_in_title():
    assert "https://volleyballking.jp/news/page/2/" in VOLLEYBALLKING_LISTING_URLS
    assert "https://volleyballking.jp/news/page/3/" in VOLLEYBALLKING_LISTING_URLS
    assert _should_inspect_volleyballking_article(
        "SVリーグ男子 チーム紹介",
        "https://volleyballking.jp/news/page/2/",
    )
    assert not _should_inspect_volleyballking_article(
        "一般記事",
        "https://volleyballking.jp/league/svleague/",
    )


def test_reconcile_merges_broadcast_and_match_times_and_blocks_wrong_bs10_channel():
    rows = reconcile([
        Broadcast(
            "J SPORTS 2", "2026-10-17", "NECレッドロケッツ川崎",
            "ヴィクトリーナ姫路", "j-sports-guide", "", "18:15",
        ),
        Broadcast(
            "NHK BS", "2026-11-07", "ウルフドッグス名古屋",
            "ジェイテクトSTINGS愛知", "bad-heading", "14:35",
        ),
    ])
    js = next(r for r in rows if r.station == "J SPORTS 2" and r.broadcast_date == "2026-10-17")
    assert js.broadcast_time == "18:15"
    assert js.match_time == "18:35"
    assert not any(
        r.station == "NHK BS" and r.broadcast_date == "2026-11-07"
        and r.home == "ウルフドッグス名古屋"
        and r.away == "ジェイテクトSTINGS愛知"
        for r in rows
    )


def test_colon_format_broadcast_start_is_distinct_from_match_start():
    assert _extract_typed_times(
        "テレビ神奈川で18:30から放送。NECレッドロケッツ川崎 vs ヴィクトリーナ姫路。試合開始は18時35分。"
    ) == ("18:30", "18:35")


def test_preseason_j_sports_row_does_not_invent_match_start_time():
    rows = reconcile([])
    row = next(
        r for r in rows
        if r.station == "J SPORTS 4" and r.broadcast_date == "2026-09-29"
    )
    assert row.broadcast_time == "18:55"
    assert row.match_time == ""


def test_j_sports_1101_broadcast_start_precedes_match_start():
    rows = reconcile([])
    row = next(
        r for r in rows
        if r.station == "J SPORTS 2" and r.broadcast_date == "2026-11-01"
    )
    assert row.broadcast_time == "12:45"
    assert row.match_time == "13:05"
