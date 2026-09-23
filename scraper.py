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

OFFICIAL_NEWS_INDEX = "https://www.svleague.jp/news/sv/"
OFFICIAL_NEWS_URLS = [
    "https://www.svleague.jp/news/detail/100302/?grade=sv",
    "https://www.svleague.jp/news/detail/100414/?grade=sv",
]
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
        hint = clean_station(station_hint)
        # Some official SV.LEAGUE tables use a combined heading such as
        # "J SPORTS 1/2/3/4". In that case the actual channel is written
        # in each row, so do not inject the combined heading as a station.
        if hint in VALID_STATIONS:
            stations.append(hint)
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

def official_article_urls(page):
    """Discover official SV.LEAGUE news articles from the official news index.
    Also keep explicitly known broadcast articles so pagination/cache changes
    cannot hide them."""
    urls = set(OFFICIAL_NEWS_URLS)
    empty_pages = 0
    for n in range(1, 11):
        url = OFFICIAL_NEWS_INDEX if n == 1 else f"{OFFICIAL_NEWS_INDEX}?page={n}"
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(500)
            links = page.locator('a[href*="/news/detail/"]')
            count = links.count()
            if count == 0:
                empty_pages += 1
                if empty_pages >= 2:
                    break
                continue
            empty_pages = 0
            for i in range(count):
                link = links.nth(i)
                href = link.get_attribute("href")
                title = link.inner_text().strip()
                if href and "/news/detail/" in href:
                    if href.startswith("/"):
                        href = "https://www.svleague.jp" + href
                    clean = href.split("#")[0]
                    # Only open likely broadcast/media articles. Known broadcast
                    # articles are always retained even if their title changes.
                    keywords = ("放送", "テレビ", "NHK", "J SPORTS", "GAORA", "フジテレビ", "CS", "BS", "地上波", "メディア")
                    if clean in urls or any(k in title for k in keywords):
                        urls.add(clean)
        except Exception as e:
            print("OFFICIAL INDEX ERROR:", url, e)
    return sorted(urls)

def scrape_official_article(page, rows, url):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(700)
    body = page.locator("body").inner_text(timeout=10000)
    if not body.strip():
        raise RuntimeError(f"official article returned empty text: {url}")

    # Broadcast tables use the station name as a heading above each table.
    # Never use the article publication date as a broadcast date.
    tables = page.locator("table")
    for i in range(tables.count()):
        table = tables.nth(i)
        try:
            row_locator = table.locator("tr")
            if row_locator.count() == 0:
                continue
            # Walk backwards through headings in DOM order. This is much safer
            # than taking arbitrary page text as the broadcaster.
            station = None
            try:
                headings = table.locator("xpath=preceding::h1 | preceding::h2 | preceding::h3 | preceding::h4")
                for j in range(headings.count() - 1, -1, -1):
                    txt = clean_station(headings.nth(j).inner_text())
                    if txt in VALID_STATIONS:
                        station = txt
                        break
            except Exception:
                station = None

            if not station:
                continue

            for j in range(row_locator.count()):
                try:
                    row_text = " ".join(row_locator.nth(j).locator("th,td").all_inner_texts())
                except Exception:
                    continue
                item = extract_broadcast_item(row_text, station)
                if item:
                    _, d, match, tm = item
                    add(rows, station, d, match, url, tm)
        except Exception as e:
            print("OFFICIAL TABLE ERROR:", url, e)

def scrape_official(page, rows):
    urls = official_article_urls(page)
    if not urls:
        raise RuntimeError("SV.LEAGUE official news index returned no article URLs")

    parsed_articles = 0
    for url in urls:
        try:
            before = len(rows)
            scrape_official_article(page, rows, url)
            if len(rows) > before:
                parsed_articles += 1
        except Exception as e:
            print("OFFICIAL ARTICLE ERROR:", url, e)

    if parsed_articles == 0:
        raise RuntimeError("No broadcast records could be safely parsed from official SV.LEAGUE news articles")
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
        Broadcast("J SPORTS 4","2026-09-29","東京グレートベアーズ","ジェイテクトSTINGS愛知",src,"18:55"),
        Broadcast("J SPORTS 2","2026-10-17","NECレッドロケッツ川崎","ヴィクトリーナ姫路",src,"18:15"),
        Broadcast("J SPORTS 1","2026-10-18","NECレッドロケッツ川崎","ヴィクトリーナ姫路",src,"15:15"),
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

    html = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#071018">
<title>SV.LEAGUE | 放送スケジュール</title>
<style>
:root{
  --bg:#050b10;--panel:#09151e;--panel2:#0d1c27;--line:rgba(255,255,255,.09);
  --text:#f7f9fb;--muted:#8fa0ad;--gold:#d6ad45;--gold2:#f0ce72;
  --blue:#87c6ff;--shadow:0 20px 60px rgba(0,0,0,.28)
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:
 radial-gradient(circle at 80% 0%,rgba(214,173,69,.11),transparent 28rem),
 radial-gradient(circle at 10% 30%,rgba(38,109,156,.12),transparent 30rem),
 var(--bg);color:var(--text);font-family:Inter,"Noto Sans JP",system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:inherit}
.shell{max-width:1240px;margin:0 auto;padding:0 28px}
.topbar{height:64px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;background:rgba(3,8,12,.78);backdrop-filter:blur(14px);position:sticky;top:0;z-index:20}
.brand{display:flex;align-items:center;gap:16px;font-weight:900;letter-spacing:.04em}
.brand-mark{width:34px;height:34px;border:2px solid var(--gold);transform:skew(-18deg) rotate(8deg);position:relative;box-shadow:0 0 22px rgba(214,173,69,.18)}
.brand-mark:after{content:"";position:absolute;inset:6px;border:1px solid var(--gold2)}
.brand-name{font-size:22px}.brand-divider{width:1px;height:24px;background:#45515a}.brand-sub{font-size:14px;color:#dfe6eb}
.status{display:flex;gap:18px;color:var(--muted);font-size:12px}
.hero{min-height:310px;display:flex;align-items:center;position:relative;overflow:hidden;border-bottom:1px solid var(--line)}
.hero:before{content:"";position:absolute;inset:0;background:
 linear-gradient(90deg,rgba(4,10,14,.98) 0%,rgba(4,10,14,.82) 48%,rgba(4,10,14,.3) 100%),
 repeating-linear-gradient(135deg,transparent 0 110px,rgba(214,173,69,.08) 111px 170px,transparent 171px 250px)}
.hero:after{content:"";position:absolute;width:440px;height:440px;border:22px solid rgba(255,255,255,.08);border-radius:50%;right:8%;top:-110px;box-shadow:inset 0 0 0 7px rgba(214,173,69,.15),0 0 80px rgba(255,255,255,.04)}
.hero-inner{position:relative;z-index:1;padding:58px 0 52px}
.eyebrow{color:var(--gold2);font-weight:800;letter-spacing:.16em;font-size:15px}
.hero h1{font-size:clamp(38px,6vw,72px);line-height:.95;margin:10px 0 18px;letter-spacing:-.045em}
.hero h1 span{display:block;color:#fff}
.hero-copy{max-width:560px;color:#b7c4cd;font-size:15px;line-height:1.9}
.accent{width:42px;height:3px;background:var(--gold);margin:24px 0}
.controls{padding:22px 0 14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.filter{border:1px solid var(--line);background:linear-gradient(180deg,#10202b,#0a151e);color:#dce5eb;border-radius:999px;padding:10px 17px;cursor:pointer;font-weight:700;font-size:13px;transition:.2s}
.filter:hover{transform:translateY(-1px);border-color:rgba(214,173,69,.45)}
.filter.active{background:linear-gradient(180deg,#f1cc67,#b98924);color:#111;border-color:#e6bf57;box-shadow:0 8px 24px rgba(214,173,69,.16)}
.date-select{margin-left:auto;background:#0b1720;border:1px solid var(--line);color:#e6edf1;border-radius:999px;padding:10px 14px;min-width:150px}
.summary{display:flex;justify-content:space-between;align-items:end;padding:18px 2px 12px}
.summary h2{margin:0;font-size:18px}.summary p{margin:5px 0 0;color:var(--muted);font-size:12px}
.count{font-size:13px;color:var(--muted)}
.schedule{display:flex;flex-direction:column;gap:14px;padding-bottom:56px}
.day-card{background:linear-gradient(180deg,rgba(13,28,39,.92),rgba(7,17,24,.96));border:1px solid var(--line);border-radius:15px;overflow:hidden;box-shadow:var(--shadow)}
.day-head{padding:13px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:12px}
.day-head:before{content:"";width:4px;height:24px;background:var(--gold);border-radius:4px}
.day-date{font-size:20px;font-weight:900;letter-spacing:.02em}.day-week{color:var(--muted);font-size:13px}
.grid-head,.broadcast-row{display:grid;grid-template-columns:1.15fr 1fr 1.9fr 1.9fr .8fr;align-items:center}
.grid-head{background:rgba(255,255,255,.025);color:#80919e;font-size:11px;letter-spacing:.08em;padding:9px 18px}
.broadcast-row{min-height:66px;padding:9px 18px;border-top:1px solid var(--line);font-size:14px}
.broadcast-row:first-child{border-top:0}
.station-badge{display:inline-flex;align-items:center;width:max-content;max-width:100%;padding:9px 13px;border-radius:10px;background:linear-gradient(135deg,#c79a36,#e1be62);color:#111;font-weight:900;font-size:12px;letter-spacing:.02em;box-shadow:0 6px 16px rgba(0,0,0,.18)}
.team{font-weight:750}.team.highlight{background:var(--blue);color:#06121a;padding:7px 10px;border-radius:8px;width:max-content;max-width:100%}
.away{display:flex;align-items:center;gap:12px}.home{display:flex;align-items:center}
.vs{color:#71818d;font-size:11px;margin:0 8px}
.record-cell{display:flex;align-items:center;justify-content:center}.record-check{appearance:none;width:24px;height:24px;border:2px solid #71818d;border-radius:7px;background:#071018;cursor:pointer;position:relative;transition:.18s;box-shadow:0 4px 12px rgba(0,0,0,.18)}.record-check:hover{border-color:var(--gold2);transform:scale(1.05)}.record-check:checked{background:var(--gold);border-color:var(--gold2)}.record-check:checked:after{content:"✓";position:absolute;left:4px;top:-2px;color:#111;font-size:20px;font-weight:900}.record-label{font-size:11px;color:var(--muted);margin-left:7px}.broadcast-row.reserved{background:linear-gradient(90deg,rgba(214,173,69,.06),transparent 65%)}
.empty{padding:48px;text-align:center;color:var(--muted)}
.footer{border-top:1px solid var(--line);padding:24px 0 38px;color:#71818d;font-size:11px;line-height:1.7}
.footer strong{color:#aeb9c0}
@media(max-width:760px){
 .shell{padding:0 14px}.status{display:none}.brand-name{font-size:18px}.brand-sub{font-size:12px}
 .hero{min-height:300px}.hero-inner{padding:48px 0}.hero h1{font-size:44px}
 .controls{overflow-x:auto;flex-wrap:nowrap;padding-bottom:12px}.filter{white-space:nowrap}.date-select{margin-left:0;min-width:145px}
 .grid-head{display:none}.day-card{border-radius:12px}
 .broadcast-row{grid-template-columns:1fr 1fr;gap:8px;padding:14px}.broadcast-row>div:nth-child(3){grid-column:1/2}.broadcast-row>div:nth-child(4){grid-column:2/3}
 .station-badge{font-size:11px;padding:7px 9px}.team{font-size:13px}.day-date{font-size:18px}
 .home,.away{min-width:0}.team.highlight{white-space:normal}
}
</style>
</head>
<body>
<header class="topbar">
 <div class="shell" style="width:100%;display:flex;align-items:center;justify-content:space-between">
  <div class="brand"><div class="brand-mark"></div><div class="brand-name">SV.LEAGUE</div><div class="brand-divider"></div><div class="brand-sub">放送スケジュール</div></div>
  <div class="status"><span>最終更新 __UPDATED__</span><span>↻ 自動更新｜毎日6:00</span></div>
 </div>
</header>
<section class="hero"><div class="shell hero-inner">
 <div class="eyebrow">SV.LEAGUE 2026–27</div>
 <h1>BROADCAST<br><span>SCHEDULE</span></h1>
 <div class="accent"></div>
 <div class="hero-copy">SVリーグの試合をテレビ放送でチェック。<br>公式発表を優先し、各放送局の情報も照合して掲載しています。</div>
</div></section>
<main class="shell">
 <div class="controls">
  <button class="filter active" data-filter="all">すべて</button>
  <button class="filter" data-filter="地上波">地上波</button>
  <button class="filter" data-filter="NHK">NHK</button>
  <button class="filter" data-filter="J SPORTS">J SPORTS</button>
  <button class="filter" data-filter="GAORA">GAORA SPORTS</button>
  <button class="filter" data-filter="フジテレビ">フジテレビ</button>
  <select class="date-select" id="dateFilter"><option value="all">日付を選択</option>__DATES__</select>
 </div>
 <div class="summary"><div><h2>放送予定</h2><p>放送日順｜全件表示</p></div><div class="count" id="count"></div></div>
 <section class="schedule" id="schedule">__ROWS__</section>
 <div class="footer"><strong>※ 放送日時・対戦カードは変更になる場合があります。</strong><br>最新情報は各放送局の公式サイトおよびSV.LEAGUE公式発表をご確認ください。</div>
</main>
<script>
const cards=[...document.querySelectorAll('.day-card')];
const buttons=[...document.querySelectorAll('.filter')];
const dateFilter=document.getElementById('dateFilter');
const count=document.getElementById('count');
function apply(){
 const f=document.querySelector('.filter.active')?.dataset.filter||'all';
 const d=dateFilter.value;
 let n=0;
 cards.forEach(card=>{
  const date=card.dataset.date;
  const matchesDate=d==='all'||date===d;
  let visible=0;
  card.querySelectorAll('.broadcast-row').forEach(row=>{
   const station=row.dataset.station;
   const ok=f==='all'||station.includes(f);
   row.style.display=ok?'grid':'none';
   if(ok) visible++;
  });
  const show=matchesDate&&visible>0;
  card.style.display=show?'block':'none';
  if(show)n+=visible;
 });
 count.textContent=n+'件';
}
buttons.forEach(b=>b.addEventListener('click',()=>{buttons.forEach(x=>x.classList.remove('active'));b.classList.add('active');apply()}));
const STORAGE_KEY='svleague-recording-reservations-v1';
function rowKey(row){ const cells=row.querySelectorAll(':scope > div'); return [row.dataset.station,cells[1]?.textContent.trim(),cells[2]?.textContent.trim(),cells[3]?.textContent.trim()].join('|'); }
function loadReservations(){ document.querySelectorAll('.broadcast-row').forEach(row=>{ const box=row.querySelector('.record-check'); if(!box)return; const saved=localStorage.getItem(STORAGE_KEY+'|'+rowKey(row))==='1'; box.checked=saved; row.classList.toggle('reserved',saved); box.addEventListener('change',()=>{ const key=STORAGE_KEY+'|'+rowKey(row); if(box.checked){localStorage.setItem(key,'1');row.classList.add('reserved')} else{localStorage.removeItem(key);row.classList.remove('reserved')} }); }); }
dateFilter.addEventListener('change',apply); loadReservations(); apply();
</script>
</body></html>"""

    dates = sorted(set(r.broadcast_date for r in rows))
    date_options = "".join(f'<option value="{d}">{d.replace("-", "/")}</option>' for d in dates)

    from collections import defaultdict
    grouped = defaultdict(list)
    for r in rows:
        grouped[r.broadcast_date].append(r)

    def esc(s):
        import html as _html
        return _html.escape(s)

    day_blocks=[]
    for d, items in sorted(grouped.items()):
        dt=date.fromisoformat(d)
        weekday="月火水木金土日"[dt.weekday()]
        body=[]
        for r in items:
            hcls="highlight" if r.home in ("東レアローズ滋賀","大阪ブルテオン") else ""
            acls="highlight" if r.away in ("東レアローズ滋賀","大阪ブルテオン") else ""
            body.append(
                f'<div class="broadcast-row" data-station="{esc(r.station)}">'
                f'<div><span class="station-badge">{esc(r.station)}</span></div>'
                f'<div class="row-date">{r.broadcast_date.replace("-", "/")}</div>'
                f'<div class="home"><span class="team {hcls}">{esc(r.home)}</span></div>'
                f'<div class="away"><span class="team {acls}">{esc(r.away)}</span></div>'
                f'<div class="record-cell"><label><input class="record-check" type="checkbox" aria-label="録画予約"><span class="record-label">予約</span></label></div>'
                f'</div>'
            )
        day_blocks.append(
            f'<div class="day-card" data-date="{d}">'
            f'<div class="day-head"><span class="day-date">{d[5:].replace("-", ".")}</span><span class="day-week">（{weekday}）</span></div>'
            f'<div class="grid-head"><div>放送局</div><div>放送日</div><div>ホームチーム</div><div>アウェイチーム</div><div>録画予約</div></div>'
            f'{"".join(body)}</div>'
        )

    html = html.replace("__ROWS__", "".join(day_blocks))
    html = html.replace("__DATES__", date_options)
    html = html.replace("__UPDATED__", datetime.now().strftime("%Y.%m.%d %H:%M"))
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
