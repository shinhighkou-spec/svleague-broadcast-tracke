import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from scraper import _extract_volleyballking_broadcast, reconcile


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
