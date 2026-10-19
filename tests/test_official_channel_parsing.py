import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from scraper import _station_from_heading_texts, extract_broadcast_item, reconcile, validate


def test_official_channel_is_resolved_from_row_under_combined_headings():
    assert _station_from_heading_texts(["GAORA SPORTS", "J SPORTS 1/2/3/4", "WOMEN"]) is None
    assert _station_from_heading_texts(["GAORA SPORTS", "フジテレビONE/TWO/NEXT", "MEN"]) is None
    assert _station_from_heading_texts(["NHK BS", "BS10", "WOMEN"]) == "BS10"

    assert extract_broadcast_item(
        "2026/11/14（土） 13:05 SAGA久光スプリングス vs PFUブルーキャッツ石川かほく J SPORTS 1"
    ) == ("J SPORTS 1", "2026-11-14", ("SAGA久光スプリングス", "PFUブルーキャッツ石川かほく"), "13:05")
    assert extract_broadcast_item(
        "2026/12/5（土） 18:05 大阪ブルテオン vs ジェイテクトSTINGS愛知 フジテレビTWO"
    ) == ("フジテレビTWO", "2026-12-05", ("大阪ブルテオン", "ジェイテクトSTINGS愛知"), "18:05")
    assert extract_broadcast_item(
        "2026/11/7（土） 14:35 ウルフドッグス名古屋 vs ジェイテクトSTINGS愛知", "BS10"
    ) == ("BS10", "2026-11-07", ("ウルフドッグス名古屋", "ジェイテクトSTINGS愛知"), "14:35")


def test_bs10_official_facts_are_present_and_valid():
    rows = reconcile([])
    keys = {(r.station, r.broadcast_date, r.home, r.away) for r in rows}
    assert ("BS10", "2026-11-14", "SAGA久光スプリングス", "PFUブルーキャッツ石川かほく") in keys
    assert ("BS10", "2026-11-28", "NECレッドロケッツ川崎", "PFUブルーキャッツ石川かほく") in keys
    assert ("BS10", "2026-11-07", "ウルフドッグス名古屋", "ジェイテクトSTINGS愛知") in keys
    assert validate(rows, official_ok=True) == (True, "ok")
