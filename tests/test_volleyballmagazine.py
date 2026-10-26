import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from scraper import (
    Broadcast,
    VALID_STATIONS,
    _parse_volleyballmagazine_tv_schedule,
    _volleyballmagazine_station,
    reconcile,
)


SAMPLE_TITLE = "2026年10月のバレーボール番組"
SAMPLE_ARTICLE = """
2026年10月のバレーボール番組
2026-10-02
期間： 2026.10.01 ～ 2026.10.31
〖大同生命SVリーグ2026-2027〗
＜地上波＞
10/24（土）[生]13:00～15:00 群馬テレビ
女子 群馬vsA秋田庄内
＜ＢＳ＞
10/17（土）[生]18:15～21:30 JSPORTS 2HD
女子 NEC川崎vs姫路[実況]中田浩光
10/23（金）[生]時間未定 NHK BS
女子 デンソーvsSAGA久光
＜ＣＳ＞
10/24（土）[生]14:00～17:30 フジテレビNEXT
男子 北海道YSvs大阪Ｂ
＜JSPORTSオンデマンド・Amazon Prime Video J SPORTSチャンネル＞
10/24（土）13:55～18:15
群馬vsA秋田庄内
"""


def test_volleyballmagazine_parser_accepts_only_explicit_tv_schedule_rows():
    rows = _parse_volleyballmagazine_tv_schedule(SAMPLE_TITLE, SAMPLE_ARTICLE)
    keys = {(station, date, home, away, airtime)
            for station, date, (home, away), airtime in rows}

    assert (
        "群馬テレビ", "2026-10-24", "群馬グリーンウイングス",
        "アランマーレ秋田庄内", "13:00"
    ) in keys
    assert (
        "J SPORTS 2", "2026-10-17", "NECレッドロケッツ川崎",
        "ヴィクトリーナ姫路", "18:15"
    ) in keys
    assert (
        "NHK BS", "2026-10-23", "デンソーエアリービーズ",
        "SAGA久光スプリングス", ""
    ) in keys
    assert (
        "フジテレビNEXT", "2026-10-24", "北海道イエロースターズ",
        "大阪ブルテオン", "14:00"
    ) in keys
    assert len(rows) == 4


def test_volleyballmagazine_publication_date_is_not_broadcast_date():
    rows = _parse_volleyballmagazine_tv_schedule(SAMPLE_TITLE, SAMPLE_ARTICLE)
    dates = {date for _, date, _, _ in rows}
    assert "2026-10-02" not in dates
    assert dates == {"2026-10-17", "2026-10-23", "2026-10-24"}


def test_volleyballmagazine_does_not_parse_streaming_only_section():
    rows = _parse_volleyballmagazine_tv_schedule(SAMPLE_TITLE, SAMPLE_ARTICLE)
    assert not any("オンデマンド" in station or "配信" in station
                   for station, _, _, _ in rows)
    assert all(station in VALID_STATIONS for station, _, _, _ in rows)


def test_volleyballmagazine_station_aliases_are_normalized():
    assert _volleyballmagazine_station("10/17（土）[生]18:15～21:30 JSPORTS 2HD") == "J SPORTS 2"
    assert _volleyballmagazine_station("10/17（土）[生]14:00～17:00 GAORA SPORTS HD") == "GAORA SPORTS"
    assert _volleyballmagazine_station("10/24（土）[生]13:00～15:00 サンテレビ") == "サンテレビジョン"
    assert _volleyballmagazine_station("10/24（土）[生]13:00～15:00 福島テレビ") == "福島テレビ"


def test_direct_broadcaster_airtime_outranks_magazine_cross_check():
    identity = (
        "J SPORTS 2", "2026-10-17",
        "NECレッドロケッツ川崎", "ヴィクトリーナ姫路"
    )
    magazine = Broadcast(*identity, "https://volleyballmagazine.jp/702000/", "18:15")
    broadcaster = Broadcast(
        *identity,
        "https://www.jsports.co.jp/program_guide/channel/japanese/two/261017/",
        "18:20",
    )
    rows = reconcile([magazine, broadcaster])
    matching = [row for row in rows if (
        row.station, row.broadcast_date, row.home, row.away
    ) == identity]
    assert len(matching) == 1
    assert matching[0].broadcast_time == "18:20"
    assert matching[0].source == broadcaster.source
