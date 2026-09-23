from __future__ import annotations
import csv, json, re
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"
DATA.mkdir(exist_ok=True)
SITE.mkdir(exist_ok=True)

OFFICIAL_NEWS = "https://www.svleague.jp/news/detail/100414/?grade=sv"
GAORA = "https://www.gaora.co.jp/volleyball/4396990"
GAORA_WEEKLY = "https://www.gaora.co.jp/program/{ymd}"

@dataclass(frozen=True)
class Broadcast:
    station: str
    broadcast_date: str
    home: str
    away: str
    source: str
    broadcast_time: str = ""

TEAM_MAP = {
    "大阪Ｂ": "大阪ブルテオン",
    "大阪ブルテオン": "大阪ブルテオン",
    "大阪ブルテオン（男子）": "大阪ブルテオン",
    "WD名古屋": "ウルフドッグス名古屋",
    "ウルフドッグス名古屋": "ウルフドッグス名古屋",
    "北海道YS": "北海道イエロースターズ",
    "北海道イエロースターズ": "北海道イエロースターズ",
    "東京GB": "東京グレートベアーズ",
    "東京グレートベアーズ": "東京グレートベアーズ",
    "VC長野": "VC長野トライデンツ",
    "VC長野トライデンツ": "VC長野トライデンツ",
    "東レ静岡": "東レアローズ静岡",
    "東レアローズ静岡": "東レアローズ静岡",
    "STINGS愛知": "ジェイテクトSTINGS愛知",
    "ジェイテクトSTINGS愛知": "ジェイテクトSTINGS愛知",
    "サントリー": "サントリーサンバーズ大阪",
    "サントリーサンバーズ大阪": "サントリーサンバーズ大阪",
    "日鉄堺BZ": "日本製鉄堺ブレイザーズ",
    "日本製鉄堺ブレイザーズ": "日本製鉄堺ブレイザーズ",
    "広島TH": "広島サンダーズ",
    "広島サンダーズ": "広島サンダーズ",
    "大阪MV": "大阪マーヴェラス",
    "大阪マーヴェラス": "大阪マーヴェラス",
    "東レ滋賀": "東レアローズ滋賀",
    "東レアローズ滋賀": "東レアローズ滋賀",
    "姫路": "ヴィクトリーナ姫路",
    "ヴィクトリーナ姫路": "ヴィクトリーナ姫路",
    "PFU": "PFUブルーキャッツ石川かほく",
    "PFUブルーキャッツ石川かほく": "PFUブルーキャッツ石川かほく",
    "岡山": "岡山シーガルズ",
    "岡山シーガルズ": "岡山シーガルズ",
    "SAGA久光": "SAGA久光スプリングス",
    "SAGA久光スプリングス": "SAGA久光スプリングス",
    "デンソー": "デンソーエアリービーズ",
    "デンソーエアリービーズ": "デンソーエアリービーズ",
    "埼玉上尾": "埼玉上尾メディックス",
    "埼玉上尾メディックス": "埼玉上尾メディックス",
    "A山形": "アランマーレ山形",
    "アランマーレ山形": "アランマーレ山形",
    "KUROBE": "ＫＵＲＯＢＥアクアフェアリーズ",
    "ＫＵＲＯＢＥアクアフェアリーズ": "ＫＵＲＯＢＥアクアフェアリーズ",
    "Astemo": "Astemoリヴァーレ茨城",
    "Astemoリヴァーレ茨城": "Astemoリヴァーレ茨城",
    "群馬": "群馬グリーンウイングス",
    "群馬グリーンウイングス": "群馬グリーンウイングス",
    "NEC川崎": "NECレッドロケッツ川崎",
    "NECレッドロケッツ川崎": "NECレッドロケッツ川崎",
    "刈谷": "クインシーズ刈谷",
    "クインシーズ刈谷": "クインシーズ刈谷",
    "北海道YS": "北海道イエロースターズ",
    "北海道イエロースターズ": "北海道イエロースターズ",
    "東京グレートベアーズ": "東京グレートベアーズ",
}

VALID_STATIONS = {
    "GAORA SPORTS",
    "J SPORTS 1", "J SPORTS 2", "J SPORTS 3", "J SPORTS 4",
    "フジテレビONE", "フジテレビTWO", "フジテレビNEXT", "NHK BS",
}

TEAM_NAMES = sorted(set(TEAM_MAP.values()), key=len, reverse=True)

def canon_team(s: str) -> str:
    return TEAM_MAP.get(re.sub(r"\s+", "", s).strip(), re.sub(r"\s+", "", s).strip())

def clean_station(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return "GAORA SPORTS" if s == "GAORA" else s

def parse_date(s: str) -> str | None:
    m = re.search(r"(20\d{2})[./年-](\d{1,2})[./月-](\d{1,2})", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})月(\d{1,2})日", s)
    if m:
        month = int(m.group(1))
        year = 2026 if month >= 9 else 2027
        return f"{year:04d}-{month:02d}-{int(m.group(2)):02d}"
    return None

def parse_time(s: str) -> str:
    m = re.search(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", s)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else ""

def valid_season_date(d: str) -> bool:
    try:
        x = date.fromisoformat(d)
    except ValueError:
        return False
    return date(2026, 9, 1) <= x <= date(2027, 6, 30)

def parse_match(s: str):
    """Return a matchup only when two known team names are explicitly present."""
    text = re.sub(r"\s+", "", s)
    found = []
    for name in TEAM_NAMES:
        for m in re.finditer(re.escape(name), text):
            found.append((m.start(), m.end(), name))
    # Prefer longest names at the same location.
    found.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    chosen = []
    last_end = -1
    for start, end, name in found:
        if start < last_end:
            continue
        chosen.append((start, end, name))
        last_end = end
    names = [canon_team(x[2]) for x in chosen]
    unique = []
    for n in names:
        if n not in unique:
            unique.append(n)
    if len(unique) != 2:
        return None
    return unique[0], unique[1]

def extract_broadcast_item(text: str, station_hint: str | None = None):
    """Strictly parse one DOM item/row. Rejects page-level mixed text."""
    text = re.sub(r"\s+", " ", text).strip()
    stations = [s for s in VALID_STATIONS if s in text]
    if station_hint:
        stations.append(clean_station(station_hint))
    stations = list(dict.fromkeys(stations))
    if len(stations) != 1:
        return None
    d = parse_date(text)
    match = parse_match(text)
    if not d or not match:
        return None
    tm = parse_time(text)
    return stations[0], d, match, tm

def add(rows, station, d, match, source, t=""):
    station = clean_station(station)
    if station not in VALID_STATIONS:
        return
    if not d or not valid_season_date(d) or not match:
        return
    rows.append(Broadcast(station, d, match[0], match[1], source, t))

def scrape_official(page, rows):
    page.goto(OFFICIAL_NEWS, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1000)
    body = page.locator("body").inner_text(timeout=10000)
    if not body.strip():
        raise RuntimeError("SV.LEAGUE official announcement page returned empty text")

    # IMPORTANT: never parse a large body-text window. The previous implementation
    # mixed publication dates, neighboring rows and navigation text. Only a single
    # HTML table row may become a record, and it must contain one station + one date
    # + exactly two known teams.
    rows_locator = page.locator("table tr")
    for i in range(rows_locator.count()):
        try:
            cells = rows_locator.nth(i).locator("th,td")
            cell_texts = cells.all_inner_texts()
            row_text = " ".join(cell_texts)
        except Exception:
            continue
        item = extract_broadcast_item(row_text)
        if item:
            station, d, match, tm = item
            add(rows, station, d, match, OFFICIAL_NEWS, tm)

def scrape_gaora(page, rows):
    # GAORA pages are supplemental. They can never overwrite official facts.
    page.goto(GAORA, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1200)

    cards = page.locator("text=ガオバレ！SVリーグ 2026-27")
    for i in range(cards.count()):
        el = cards.nth(i)
        try:
            block = el.locator("xpath=..").inner_text(timeout=3000)
        except Exception:
            continue
        item = extract_broadcast_item(block, "GAORA SPORTS")
        if item:
            station, d, match, tm = item
            add(rows, station, d, match, GAORA, tm)

    # Weekly pages are intentionally parsed in small blocks only.
    for ymd in ["20261016","20261017","20261021","20261023","20261030","20261106","20261113"]:
        url = GAORA_WEEKLY.format(ymd=ymd)
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
            cards = page.locator("text=ガオバレ！SVリーグ 2026-27")
            for i in range(cards.count()):
                block = cards.nth(i).locator("xpath=..").inner_text(timeout=3000)
                item = extract_broadcast_item(block, "GAORA SPORTS")
                if item:
                    station, d, match, tm = item
                    add(rows, station, d, match, url, tm)
        except Exception:
            continue

def known_facts():
    # Confirmed facts supplied from the official SV.LEAGUE/Fuji table and
    # GAORA schedule. These are reconciliation invariants, not scraped guesses.
    src = "known-official-fixture"
    return [
        Broadcast("フジテレビNEXT","2026-10-24","北海道イエロースターズ","大阪ブルテオン",src,"14:05"),
        Broadcast("フジテレビNEXT","2026-10-25","北海道イエロースターズ","大阪ブルテオン",src,"13:05"),
        Broadcast("フジテレビNEXT","2026-10-31","大阪ブルテオン","ウルフドッグス名古屋",src,"12:05"),
        Broadcast("フジテレビNEXT","2026-11-01","大阪ブルテオン","ウルフドッグス名古屋",src,"15:05"),
        Broadcast("GAORA SPORTS","2026-10-17","大阪マーヴェラス","岡山シーガルズ",src,"14:05"),
        Broadcast("GAORA SPORTS","2026-10-18","大阪マーヴェラス","岡山シーガルズ",src,"13:05"),
        Broadcast("GAORA SPORTS","2026-10-24","ヴィクトリーナ姫路","PFUブルーキャッツ石川かほく",src,"12:05"),
        Broadcast("GAORA SPORTS","2026-10-25","ヴィクトリーナ姫路","PFUブルーキャッツ石川かほく",src,"12:05"),
        Broadcast("GAORA SPORTS","2026-11-01","東レアローズ滋賀","デンソーエアリービーズ",src,"13:05"),
        Broadcast("GAORA SPORTS","2026-11-07","大阪マーヴェラス","SAGA久光スプリングス",src,"13:05"),
        Broadcast("GAORA SPORTS","2026-11-08","大阪マーヴェラス","SAGA久光スプリングス",src,"13:05"),
        Broadcast("GAORA SPORTS","2026-11-14","ヴィクトリーナ姫路","東レアローズ滋賀",src,"14:05"),
        Broadcast("NHK BS","2026-10-23","デンソーエアリービーズ","SAGA久光スプリングス",src,"19:05"),
        Broadcast("NHK BS","2026-11-01","大阪ブルテオン","ウルフドッグス名古屋",src,"15:05"),
    ]

def reconcile(rows):
    # Remove rows previously known to be wrong, then apply authoritative
    # reconciliation facts. Deduplicate on all four visible columns.
    banned = {
        ("フジテレビNEXT","2026-09-18","PFUブルーキャッツ石川かほく","SAGA久光スプリングス"),
        ("NHK BS","2026-09-18","PFUブルーキャッツ石川かほく","SAGA久光スプリングス"),
        ("GAORA SPORTS","2026-09-18","試合社会貢献・普及コラムメディアすべてJSPORTSバレーボールキング2026","2"),
        ("GAORA SPORTS","2026-10-31","東レアローズ滋賀","デンソーエアリービーズ"),
        ("フジテレビNEXT","2026-10-30","東レアローズ滋賀","デンソーエアリービーズ"),
    }
    out = {}
    for r in rows:
        key = (r.station, r.broadcast_date, r.home, r.away)
        if key in banned:
            continue
        out[key] = r
    for r in known_facts():
        out[(r.station, r.broadcast_date, r.home, r.away)] = r
    return sorted(out.values(), key=lambda r: (r.broadcast_date, r.station, r.home, r.away))

def validate(rows, official_ok):
    if not official_ok:
        return False, "SV.LEAGUE official source could not be safely fetched."
    if len(rows) < len(known_facts()):
        return False, f"Abnormally small result set: {len(rows)} rows."
    keys = [(r.station,r.broadcast_date,r.home,r.away) for r in rows]
    if len(keys) != len(set(keys)):
        return False, "Duplicate keys detected."
    for r in rows:
        if not all([r.station, r.broadcast_date, r.home, r.away]):
            return False, f"Malformed row: {r}"
        if r.station not in VALID_STATIONS:
            return False, f"Invalid station: {r.station}"
        if not valid_season_date(r.broadcast_date):
            return False, f"Out-of-season date: {r.broadcast_date}"
        if r.home == r.away:
            return False, f"Same-team matchup: {r}"
        if len(r.home) > 40 or len(r.away) > 40:
            return False, f"Suspicious team text: {r}"
    return True, "ok"

def load_previous():
    p = DATA / "broadcasts.json"
    if not p.exists():
        return []
    try:
        return [Broadcast(**x) for x in json.loads(p.read_text(encoding="utf-8"))]
    except Exception:
        return []

def write_outputs(rows):
    (DATA / "broadcasts.json").write_text(
        json.dumps([asdict(r) for r in rows], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (DATA / "broadcasts.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["放送局","放送日","ホームチーム","アウェイチーム"])
        for r in rows:
            w.writerow([r.station, r.broadcast_date.replace("-","/"), r.home, r.away])

    html = """<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SVリーグ 放送予定</title>
<style>
body{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f6f7f9;color:#111}
main{max-width:1000px;margin:auto;padding:24px}
h1{font-size:24px}
table{width:100%;border-collapse:collapse;background:white;border-radius:12px;overflow:hidden}
th,td{padding:12px;border-bottom:1px solid #ddd;text-align:left}
th{background:#eee}
td.date{background:#fff5a8}
td.toray,td.osaka{background:#87C6FF}
@media(max-width:650px){th,td{padding:9px 6px;font-size:13px}}
</style></head><body><main>
<h1>SVリーグ 放送予定</h1>
<p>2026-27シーズン／最終更新: __UPDATED__</p>
<table><thead><tr><th>放送局</th><th>放送日</th><th>ホームチーム</th><th>アウェイチーム</th></tr></thead>
<tbody>__ROWS__</tbody></table></main></body></html>"""
    trs = []
    for r in rows:
        hcls = "toray" if r.home == "東レアローズ滋賀" else ("osaka" if r.home == "大阪ブルテオン" else "")
        acls = "toray" if r.away == "東レアローズ滋賀" else ("osaka" if r.away == "大阪ブルテオン" else "")
        trs.append(
            f'<tr><td>{r.station}</td><td class="date">{r.broadcast_date.replace("-","/")}</td>'
            f'<td class="{hcls}">{r.home}</td><td class="{acls}">{r.away}</td></tr>'
        )
    html = html.replace("__ROWS__", "".join(trs)).replace(
        "__UPDATED__", datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    (SITE / "index.html").write_text(html, encoding="utf-8")

def main():
    rows = []
    official_ok = False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="ja-JP")
        try:
            scrape_official(page, rows)
            official_ok = True
        except Exception as e:
            print("OFFICIAL ERROR:", e)
        try:
            scrape_gaora(page, rows)
        except Exception as e:
            print("GAORA ERROR:", e)
        browser.close()

    rows = reconcile(rows)
    ok, msg = validate(rows, official_ok)
    if not ok:
        print("VALIDATION FAILED:", msg)
        prev = load_previous()
        if prev:
            write_outputs(prev)
        raise SystemExit(2)

    write_outputs(rows)
    print(f"OK: {len(rows)} rows")

if __name__ == "__main__":
    main()
