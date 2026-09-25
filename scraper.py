from __future__ import annotations
import csv, json, re, urllib.parse
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
    "アランマーレ山形": "アランマーレ秋田庄内",
    "アランマーレ秋田庄内": "アランマーレ秋田庄内",
    "ＫＵＲＯＢＥアクアフェアリーズ富山": "ＫＵＲＯＢＥアクアフェアリーズ富山",
    "アリーザ愛知": "アリーザ愛知",
    "KUROBE": "ＫＵＲＯＢＥアクアフェアリーズ",
    "ＫＵＲＯＢＥアクアフェアリーズ": "ＫＵＲＯＢＥアクアフェアリーズ富山",
    "ＫＵＲＯＢＥアクアフェアリーズ富山": "ＫＵＲＯＢＥアクアフェアリーズ富山",
    "KUROBEアクアフェアリーズ富山": "ＫＵＲＯＢＥアクアフェアリーズ富山",
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
# Search aliases used by broadcasters and team media. These are only used for
# discovery/matching; the published dataset keeps the canonical SV.LEAGUE names.
SEARCH_TEAM_ALIASES = {
    "アランマーレ山形": ["アランマーレ山形", "アランマーレ秋田庄内"],
    "ＫＵＲＯＢＥアクアフェアリーズ": ["ＫＵＲＯＢＥアクアフェリーズ", "ＫＵＲＯＢＥアクアフェリーズ富山"],
    "クインシーズ刈谷": ["クインシーズ刈谷", "アリーザ愛知"],
    "VC長野トライデンツ": ["VC長野トライデンツ", "信州松本トライデンツ"],
}

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
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    m = re.search(r"(?<!\d)(\d{1,2})時(\d{1,2})?分?", s)
    if m:
        return f"{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}"
    return ""

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
def parse_jsports_time(text: str) -> str:
    m = re.search(r"(?:午前|午後|深夜)\s*(\d{1,2}):(\d{2})", text)
    if not m:
        return ""
    hour = int(m.group(1))
    minute = m.group(2)
    if "午後" in text and hour < 12:
        hour += 12
    if "深夜" in text and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute}"

def scrape_jsports_official(page, rows):
    """Authoritative supplemental source for J SPORTS TV broadcasts.
    J SPORTS official pages are checked independently of SV.LEAGUE. When a
    match is published there first, it is eligible immediately. Channel names
    are resolved from J SPORTS' own channel program guides (1-4)."""
    urls = (
        "https://www.jsports.co.jp/volleyball/",
        "https://www.jsports.co.jp/volleyball/svleague_men/",
        "https://www.jsports.co.jp/volleyball/svleague_women/",
        "https://www.jsports.co.jp/volleyball/preseason/",
    )
    candidates = []
    for url in urls:
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(700)
            text = re.sub(r"\s+", " ", page.locator("body").inner_text(timeout=10000)).strip()
            m = re.search(r"放送予定(.*?)(?:番組表のアイコン|無料動画|新着記事|テーマ曲|$)", text)
            section = m.group(1) if m else ""
            if not section:
                continue
            for mm in re.finditer(
                r"(\d{1,2})月(\d{1,2})日(?:（[^）]+）)?(.{0,260}?)(大同生命SVリーグ[^。]{0,180}?"
                r"((?:東京グレートベアーズ|北海道イエロースターズ|ウルフドッグス名古屋|フラーゴラッド鹿児島|大阪ブルテオン|サントリーサンバーズ大阪|日本製鉄堺ブレイザーズ|広島サンダーズ|信州松本トライデンツ|東レアローズ静岡|ジェイテクトSTINGS愛知|ヴォレアス北海道|NECレッドロケッツ川崎|ヴィクトリーナ姫路|デンソーエアリービーズ|SAGA久光スプリングス|大阪マーヴェラス|岡山シーガルズ|PFUブルーキャッツ石川かほく|東レアローズ滋賀|埼玉上尾メディックス|Astemoリヴァーレ茨城|群馬グリーンウイングス|クインシーズ刈谷|ＫＵＲＯＢＥアクアフェアリーズ|アランマーレ山形)\s*(?:vs\.?|VS|対)\s*(?:東京グレートベアーズ|北海道イエロースターズ|ウルフドッグス名古屋|フラーゴラッド鹿児島|大阪ブルテオン|サントリーサンバーズ大阪|日本製鉄堺ブレイザーズ|広島サンダーズ|信州松本トライデンツ|東レアローズ静岡|ジェイテクトSTINGS愛知|ヴォレアス北海道|NECレッドロケッツ川崎|ヴィクトリーナ姫路|デンソーエアリービーズ|SAGA久光スプリングス|大阪マーヴェラス|岡山シーガルズ|PFUブルーキャッツ石川かほく|東レアローズ滋賀|埼玉上尾メディックス|Astemoリヴァーレ茨城|群馬グリーンウイングス|クインシーズ刈谷|ＫＵＲＯＢＥアクアフェアリーズ|アランマーレ山形))",
                section,
            ):
                month, day = int(mm.group(1)), int(mm.group(2))
                d = f"{2026 if month >= 9 else 2027:04d}-{month:02d}-{day:02d}"
                match = parse_match(mm.group(0))
                if match:
                    candidates.append((d, match, parse_jsports_time(mm.group(0)), url))
        except Exception as e:
            print("J SPORTS OFFICIAL ERROR:", url, e)

    unique = {}
    for d, match, tm, source in candidates:
        unique[(d, match[0], match[1])] = (tm, source)

    for (d, home, away), (tm, source) in unique.items():
        ymd = d.replace("-", "")[2:]
        for ch, slug in ((1, "one"), (2, "two"), (3, "three"), (4, "four")):
            url = f"https://www.jsports.co.jp/program_guide/channel/japanese/{slug}/{ymd}/"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(350)
                body = re.sub(r"\s+", " ", page.locator("body").inner_text(timeout=8000))
                if home in body and away in body and f"({d[5:7]}/{d[8:10]})" in body:
                    add(rows, f"J SPORTS {ch}", d, (home, away), url, tm)
                    break
            except Exception as e:
                print("J SPORTS CHANNEL ERROR:", url, e)
    print("J SPORTS OFFICIAL CANDIDATES:", len(unique))

def scrape_jcom(page, rows):
    """Supplemental TV/CS source. Only accept an explicit J SPORTS channel
    together with broadcast date, time, and both teams in one small DOM block.
    J SPORTS on-demand-only entries are intentionally ignored."""
    url = "https://www2.myjcom.jp/special/tv/sports/volleyball/svleague/schedule.php"
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)
    labels = page.locator("text=/J SPORTS [1-4] HD/")
    for i in range(labels.count()):
        try:
            el = labels.nth(i)
            block = el.locator("xpath=ancestor::*[self::div or self::li or self::article][1]").inner_text(timeout=3000)
        except Exception:
            continue
        item = extract_broadcast_item(block)
        if item:
            station, d, match, tm = item
            add(rows, station, d, match, url, tm)

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

# Regional TV/SNS discovery is intentionally broad. Search engines are used
# only to discover candidate pages/posts; a row is accepted only when the same
# result block contains a recognized TV station, a broadcast date, and both
# teams. This prevents generic search hits and on-demand-only mentions from
# becoming false broadcasts.
REGIONAL_STATIONS = {
    "北海道": ["札幌テレビ", "北海道テレビ", "北海道放送", "テレビ北海道", "北海道文化放送"],
    "山形": ["山形テレビ", "山形放送", "さくらんぼテレビ"],
    "茨城": ["NHK水戸", "茨城放送"],
    "群馬": ["群馬テレビ"],
    "埼玉": ["テレビ埼玉"],
    "東京": ["TOKYO MX", "東京MX", "日本テレビ", "TBSテレビ", "テレビ朝日", "フジテレビ", "テレビ東京"],
    "神奈川": ["テレビ神奈川"],
    "富山": ["北日本放送", "富山テレビ", "チューリップテレビ"],
    "石川": ["テレビ金沢", "北陸朝日放送", "MRO北陸放送", "石川テレビ"],
    "長野": ["テレビ信州", "長野朝日放送", "信越放送", "長野放送"],
    "静岡": ["静岡第一テレビ", "静岡朝日テレビ", "静岡放送", "テレビ静岡"],
    "愛知": ["中京テレビ", "メ～テレ", "CBCテレビ", "テレビ愛知", "東海テレビ"],
    "滋賀": ["びわ湖放送", "BBC", "NHK大津"],
    "大阪": ["読売テレビ", "毎日放送", "朝日放送テレビ", "関西テレビ", "テレビ大阪"],
    "兵庫": ["サンテレビ", "読売テレビ", "毎日放送", "朝日放送テレビ", "関西テレビ"],
    "岡山": ["RSK山陽放送", "岡山放送", "テレビせとうち", "西日本放送"],
    "広島": ["広島テレビ", "広島ホームテレビ", "中国放送", "テレビ新広島"],
    "鹿児島": ["鹿児島テレビ", "鹿児島読売テレビ", "南日本放送", "鹿児島放送"],
    "佐賀": ["サガテレビ", "NHK佐賀"],
}
BROADCAST_WORDS = ("テレビ", "TV", "放送", "中継", "生中継", "録画", "地上波", "BS", "CS")
VALID_STATIONS |= {station for stations in REGIONAL_STATIONS.values() for station in stations}

def _bing_results(page, query, limit=8):
    """Return search-result candidates. Search snippets are NEVER broadcast evidence."""
    url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query) + "&count=10"
    last_error = None
    for attempt in range(2):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(700)
            out = []
            items = page.locator("li.b_algo")
            for i in range(min(items.count(), limit)):
                try:
                    item = items.nth(i)
                    title = item.locator("h2").inner_text(timeout=1500)
                    href = item.locator("h2 a").get_attribute("href")
                    snippet = item.locator(".b_caption").inner_text(timeout=1500)
                    out.append((title, href or "", snippet))
                except Exception:
                    continue
            return out
        except Exception as e:
            last_error = e
            if attempt == 0:
                page.wait_for_timeout(1000)
    raise RuntimeError(f"Bing search failed after retry: {last_error}")

def _extract_search_broadcast(text, require_time=False):
    """Extract a candidate from text. This is only a candidate until its URL is opened."""
    d = parse_date(text)
    match = parse_match(text)
    if not d or not match:
        return None
    station = None
    for st in sorted(VALID_STATIONS, key=len, reverse=True):
        if st in text:
            station = st
            break
    if not station or not any(w in text for w in BROADCAST_WORDS):
        return None
    tm = parse_time(text)
    if require_time and not tm:
        return None
    return station, d, match, tm

def _page_evidence_text(page):
    """Collect visible text plus useful metadata from the opened source page."""
    parts = []
    try:
        parts.append(page.locator("body").inner_text(timeout=10000))
    except Exception:
        pass
    for selector in (
        'meta[property="og:title"]',
        'meta[property="og:description"]',
        'meta[name="description"]',
        'meta[property="article:published_time"]',
    ):
        try:
            loc = page.locator(selector)
            for i in range(loc.count()):
                content = loc.nth(i).get_attribute("content")
                if content:
                    parts.append(content)
        except Exception:
            pass
    return re.sub(r"\s+", " ", " ".join(parts)).strip()

def _verify_search_result(page, title, href, snippet):
    """Open a search result and require the source page itself to confirm the broadcast.
    Required evidence: station + broadcast date + start time + both teams."""
    candidate = _extract_search_broadcast(" ".join((title, snippet)), require_time=False)
    if not candidate or not href:
        return None
    try:
        page.goto(href, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(700)
        evidence = _page_evidence_text(page)
        verified = _extract_search_broadcast(evidence, require_time=True)
        if not verified:
            return None
        if verified[:3] != candidate[:3]:
            return None
        return verified
    except Exception as e:
        print("SEARCH RESULT VERIFY ERROR:", href, e)
        return None

def scrape_social_and_regional(page, rows):
    """Daily discovery across team X/Instagram and regional TV sources.
    Search results are candidates only. A result enters the dataset only after
    opening its source URL and confirming station, date, start time and both teams."""
    team_items = []
    seen_team = set()
    for canonical in sorted(SEARCH_TEAM_ALIASES):
        team_items.append((canonical, SEARCH_TEAM_ALIASES[canonical]))
        seen_team.add(canonical)
    for canonical in TEAM_NAMES:
        if canonical not in seen_team:
            team_items.append((canonical, [canonical]))

    seen = set()
    candidate_count = 0
    verified_count = 0
    accepted = 0
    search_failures = 0

    def process_results(results):
        nonlocal candidate_count, verified_count, accepted
        for title, href, snippet in results:
            candidate_count += 1
            item = _verify_search_result(page, title, href, snippet)
            if not item:
                continue
            verified_count += 1
            station, d, match, tm = item
            key = (station, d, match[0], match[1])
            if key in seen:
                continue
            seen.add(key)
            add(rows, station, d, match, href, tm)
            accepted += 1

    def search_and_process(query, error_label):
        nonlocal search_failures
        try:
            process_results(_bing_results(page, query))
        except Exception as e:
            search_failures += 1
            print(error_label, query, e)

    for canonical, aliases in team_items:
        team_query = " OR ".join('"' + a + '"' for a in aliases)
        search_and_process(
            f"({team_query}) (放送 OR テレビ OR 中継 OR 生中継) site:x.com",
            "SOCIAL X SEARCH ERROR:",
        )
        search_and_process(
            f"({team_query}) (放送 OR テレビ OR 中継 OR 生中継) site:instagram.com",
            "SOCIAL INSTAGRAM SEARCH ERROR:",
        )
        search_and_process(
            f"({team_query}) (放送 OR テレビ OR 中継 OR 生中継) (テレビ局 OR CS OR BS)",
            "TEAM WEB SEARCH ERROR:",
        )

    region_terms = {
        "北海道": ["ヴォレアス北海道", "北海道イエロースターズ"],
        "東京": ["東京グレートベアーズ"],
        "長野": ["信州松本トライデンツ"],
        "静岡": ["東レアローズ静岡"],
        "愛知": ["ジェイテクトSTINGS愛知", "ウルフドッグス名古屋", "クインシーズ刈谷", "アリーザ愛知", "デンソーエアリービーズ"],
        "大阪": ["大阪ブルテオン", "サントリーサンバーズ大阪", "日本製鉄堺ブレイザーズ", "大阪マーヴェラス"],
        "広島": ["広島サンダーズ"],
        "鹿児島": ["フラーゴラッド鹿児島"],
        "山形": ["アランマーレ山形", "アランマーレ秋田庄内"],
        "茨城": ["Astemoリヴァーレ茨城"],
        "群馬": ["群馬グリーンウイングス"],
        "埼玉": ["埼玉上尾メディックス"],
        "神奈川": ["NECレッドロケッツ川崎"],
        "富山": ["ＫＵＲＯＢＥアクアフェアリーズ", "ＫＵＲＯＢＥアクアフェアリーズ富山"],
        "石川": ["PFUブルーキャッツ石川かほく"],
        "滋賀": ["東レアローズ滋賀"],
        "兵庫": ["ヴィクトリーナ姫路"],
        "岡山": ["岡山シーガルズ"],
        "佐賀": ["SAGA久光スプリングス"],
    }
    for region, teams in region_terms.items():
        stations = REGIONAL_STATIONS.get(region, [])
        station_query = " OR ".join('"' + st + '"' for st in stations)
        for team in teams:
            search_and_process(
                f'"{team}" ({station_query}) (放送 OR テレビ OR 中継 OR 生中継)',
                f"REGIONAL WEB SEARCH ERROR {region}:",
            )
            search_and_process(
                f'"{team}" ({station_query}) (放送 OR テレビ OR 中継) site:x.com',
                f"REGIONAL X SEARCH ERROR {region}:",
            )
            search_and_process(
                f'"{team}" ({station_query}) (放送 OR テレビ OR 中継) site:instagram.com',
                f"REGIONAL INSTAGRAM SEARCH ERROR {region}:",
            )

        # Station-level searches catch announcements that name the match on
        # the broadcaster page rather than in the search snippet.
        for station in stations:
            search_and_process(
                f'"{station}" (SVリーグ OR バレーボール) (放送 OR 中継)',
                f"STATION WEB SEARCH ERROR {region}:",
            )
            search_and_process(
                f'"{station}" (SVリーグ OR バレーボール) (放送 OR 中継) site:x.com',
                f"STATION X SEARCH ERROR {region}:",
            )
            search_and_process(
                f'"{station}" (SVリーグ OR バレーボール) (放送 OR 中継) site:instagram.com',
                f"STATION INSTAGRAM SEARCH ERROR {region}:",
            )

    print("SOCIAL/REGIONAL DISCOVERY CANDIDATES:", candidate_count)
    print("SOCIAL/REGIONAL DISCOVERY VERIFIED:", verified_count)
    print("SOCIAL/REGIONAL DISCOVERY ACCEPTED:", accepted)
    print("SOCIAL/REGIONAL DISCOVERY SEARCH FAILURES:", search_failures)


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
        Broadcast("J SPORTS 2","2026-10-24","ウルフドッグス名古屋","東京グレートベアーズ",src,"16:25"),
        Broadcast("J SPORTS 2","2026-10-25","ウルフドッグス名古屋","東京グレートベアーズ",src,"15:25"),
        Broadcast("J SPORTS 4","2026-10-31","フラーゴラッド鹿児島","北海道イエロースターズ",src,"13:45"),
        Broadcast("J SPORTS 2","2026-11-01","フラーゴラッド鹿児島","北海道イエロースターズ",src,"13:05"),
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

TEAM_LOGO_IDS = {
    "アランマーレ山形": "457",
    "デンソーエアリービーズ": "265",
    "Astemoリヴァーレ茨城": "264",
    "群馬グリーンウイングス": "458",
    "埼玉上尾メディックス": "281",
    "NECレッドロケッツ川崎": "284",
    "ＫＵＲＯＢＥアクアフェアリーズ富山": "277",
    "PFUブルーキャッツ石川かほく": "275",
    "クインシーズ刈谷": "266",
    "東レアローズ滋賀": "283",
    "大阪マーヴェラス": "285",
    "ヴィクトリーナ姫路": "481",
    "岡山シーガルズ": "263",
    "SAGA久光スプリングス": "261",
    "ヴォレアス北海道": "479",
    "北海道イエロースターズ": "483",
    "東京グレートベアーズ": "495",
    "VC長野トライデンツ": "461",
    "東レアローズ静岡": "257",
    "ジェイテクトSTINGS愛知": "268",
    "ウルフドッグス名古屋": "258",
    "大阪ブルテオン": "256",
    "サントリーサンバーズ大阪": "252",
    "日本製鉄堺ブレイザーズ": "251",
    "広島サンダーズ": "255",
    "フラーゴラッド鹿児島": "499",
}

EXPECTED_TEAM_LOGO_NAMES = {
    "アランマーレ山形", "デンソーエアリービーズ", "Astemoリヴァーレ茨城", "群馬グリーンウイングス",
    "埼玉上尾メディックス", "NECレッドロケッツ川崎", "ＫＵＲＯＢＥアクアフェアリーズ富山", "PFUブルーキャッツ石川かほく",
    "クインシーズ刈谷", "東レアローズ滋賀", "大阪マーヴェラス", "ヴィクトリーナ姫路", "岡山シーガルズ", "SAGA久光スプリングス",
    "ヴォレアス北海道", "北海道イエロースターズ", "東京グレートベアーズ", "VC長野トライデンツ", "東レアローズ静岡",
    "ジェイテクトSTINGS愛知", "ウルフドッグス名古屋", "大阪ブルテオン", "サントリーサンバーズ大阪", "日本製鉄堺ブレイザーズ",
    "広島サンダーズ", "フラーゴラッド鹿児島",
}

def validate_team_logos(team_logos, rows=None):
    missing = sorted(EXPECTED_TEAM_LOGO_NAMES - set(team_logos))
    if missing:
        raise RuntimeError("TEAM LOGO COVERAGE FAILED: missing expected teams: " + ", ".join(missing))
    if rows is not None:
        row_teams = {r.home for r in rows} | {r.away for r in rows}
        missing_rows = sorted(row_teams - set(team_logos))
        if missing_rows:
            raise RuntimeError("TEAM LOGO COVERAGE FAILED: published rows have no logo: " + ", ".join(missing_rows))
    bad_urls = sorted(
        name for name, team_id in TEAM_LOGO_IDS.items()
        if team_logos.get(name) != f"https://www.svleague.jp/ext/team/{team_id}/team-logo.png"
    )
    if bad_urls:
        raise RuntimeError("TEAM LOGO URL FAILED: " + ", ".join(bad_urls))

def scrape_team_logos(page):
    """Use fixed official team-detail IDs so logo harvesting does not depend on
    the dynamically rendered team-list pages. The raw team-logo.png contains
    the badge itself; the UI does not add a circular background.
    """
    logos = {
        name: f"https://www.svleague.jp/ext/team/{team_id}/team-logo.png"
        for name, team_id in TEAM_LOGO_IDS.items()
    }
    # Broadcaster pages may use the alternate current media name for Aranmare.
    # Keep the same official badge available under both names so a published row
    # can never lose its logo merely because the source used an alias.
    logos["アランマーレ秋田庄内"] = logos["アランマーレ山形"]
    validate_team_logos(logos)
    print("TEAM LOGOS FOUND:", len(logos))
    print("TEAM LOGO TEAMS:", ", ".join(sorted(logos)))
    return logos

def write_outputs(rows, team_logos=None):
    team_logos = team_logos or {}
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
<meta name="theme-color" content="#07111b">
<title>SV.LEAGUE | TV BROADCAST</title>
<style>
:root{
  --bg:#06101a;--panel:#0b1824;--panel2:#101f2c;--line:rgba(255,255,255,.10);
  --text:#f7fafc;--muted:#8e9eaa;--gold:#d5ad47;--gold2:#f3cf70;
  --blue:#87c6ff;--shadow:0 18px 45px rgba(0,0,0,.24)
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,"Noto Sans JP",system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.shell{max-width:1180px;margin:auto;padding:0 20px}
.topbar{height:58px;border-bottom:1px solid var(--line);display:flex;align-items:center;background:#06101a;position:sticky;top:0;z-index:20}
.brand{display:flex;align-items:center;gap:12px;font-weight:900}.brand-mark{width:27px;height:27px;border:2px solid var(--gold);transform:skew(-16deg) rotate(8deg);position:relative}.brand-mark:after{content:"";position:absolute;inset:5px;border:1px solid var(--gold2)}
.brand-name{font-size:19px;letter-spacing:.04em}.brand-divider{width:1px;height:21px;background:#40505d}.brand-sub{font-size:12px;color:#c8d1d8}
.top-status{margin-left:auto;color:var(--muted);font-size:11px}
.hero{padding:30px 0 24px;border-bottom:1px solid var(--line);background:
 radial-gradient(circle at 85% 10%,rgba(213,173,71,.12),transparent 23rem),
 linear-gradient(180deg,#081522,#06101a)}
.eyebrow{color:var(--gold2);font-size:12px;font-weight:800;letter-spacing:.18em}
.hero h1{margin:7px 0 6px;font-size:clamp(30px,5vw,50px);line-height:.95;letter-spacing:-.04em}
.hero p{margin:0;color:#9eabb5;font-size:13px}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:18px 0 12px}
.filter{border:1px solid var(--line);background:#0c1a27;color:#cdd7dd;border-radius:999px;padding:8px 13px;cursor:pointer;font-size:12px;font-weight:800}
.filter.active{background:var(--gold);border-color:var(--gold);color:#111}
.date-select{margin-left:auto;background:#0c1a27;border:1px solid var(--line);color:#e6edf1;border-radius:999px;padding:8px 12px}
.summary{display:flex;justify-content:space-between;align-items:end;padding:7px 2px 12px}
.summary h2{margin:0;font-size:17px}.summary p{margin:3px 0 0;color:var(--muted);font-size:11px}.count{font-size:12px;color:var(--muted)}
.schedule{padding-bottom:42px}
.day-card{margin:0 0 16px;background:var(--panel);border:1px solid var(--line);border-radius:13px;overflow:hidden;box-shadow:var(--shadow)}
.day-head{display:flex;align-items:baseline;gap:8px;padding:12px 16px;background:#0e1e2b;border-bottom:1px solid var(--line)}
.day-date{font-size:22px;font-weight:950;letter-spacing:.02em}.day-week{font-size:12px;color:#a3b0b9}
.grid-head,.broadcast-row{display:grid;grid-template-columns:1.25fr .85fr 1.75fr 1.75fr .62fr;align-items:center}
.grid-head{padding:9px 16px;background:#0b1722;color:#82929e;font-size:10px;font-weight:800;letter-spacing:.08em}
.broadcast-row{min-height:72px;padding:9px 16px;border-top:1px solid var(--line);font-size:13px}
.station{display:flex;align-items:center;gap:9px;min-width:0}
.station-logo{width:74px;height:42px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex:0 0 74px;background:#fff;box-shadow:0 4px 12px rgba(0,0,0,.18);padding:7px 8px;overflow:hidden}
.station-logo img{display:block;max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain}
.station-logo.js{background:#fff}.station-logo.js img{width:58px}
.station-logo.gaora{background:#111;border:1px solid #37424a}.station-logo.gaora img{width:61px}
.station-logo.fuji{background:#fff;padding:3px 4px}.station-logo.fuji img{width:100%;height:100%;max-width:none;max-height:none;object-fit:contain}.station-logo.fuji.next img{transform:scale(1.08)}
.station-logo.nhk{background:#fff}.station-logo.nhk img{width:57px}
.station-channel{font-size:9px;font-weight:900;letter-spacing:.02em;color:#c9d4db;margin-left:-3px;white-space:nowrap}
.station-lockup{display:flex;align-items:center;gap:5px;min-width:0}
.station-name{font-weight:800;white-space:nowrap}
.time{font-size:19px;font-weight:900;letter-spacing:.02em;color:#fff}
.team-wrap{display:flex;align-items:center;gap:9px;min-width:0}
.team-logo{width:44px;height:44px;object-fit:contain;flex:0 0 44px;display:block;filter:none;background:transparent}
.team{font-weight:800;line-height:1.35}
.team.highlight{background:var(--blue);color:#06121a;padding:6px 9px;border-radius:7px;width:max-content;max-width:100%}
.away{display:flex;align-items:center}.home{display:flex;align-items:center}
.record-cell{display:flex;justify-content:center;align-items:center}
.record-check{appearance:none;width:23px;height:23px;border:2px solid #6f808d;border-radius:6px;background:#07111a;cursor:pointer;position:relative}
.record-check:checked{background:var(--gold);border-color:var(--gold2)}
.record-check:checked:after{content:"✓";position:absolute;left:3px;top:-3px;color:#111;font-size:19px;font-weight:950}
.broadcast-row.reserved{background:linear-gradient(90deg,rgba(213,173,71,.09),transparent 70%)}
.footer{border-top:1px solid var(--line);padding:20px 0 32px;color:#72828d;font-size:10px;line-height:1.7}
@media(max-width:760px){
 .shell{padding:0 12px}.top-status{display:none}.brand-name{font-size:17px}.brand-sub{font-size:11px}
 .hero{padding:24px 0 20px}.hero h1{font-size:34px}
 .controls{overflow-x:auto;flex-wrap:nowrap}.filter{white-space:nowrap}.date-select{margin-left:0;min-width:140px}
 .grid-head{display:none}.day-card{border-radius:11px}
 .broadcast-row{grid-template-columns:82px 1fr;gap:9px 10px;padding:13px 12px;min-height:0}
 .broadcast-row>div:nth-child(1){grid-column:1}.broadcast-row>div:nth-child(2){grid-column:2}
 .broadcast-row>div:nth-child(3){grid-column:1/3}.broadcast-row>div:nth-child(4){grid-column:1/3}.broadcast-row>div:nth-child(5){position:absolute;right:13px;top:13px}
 .broadcast-row{position:relative;padding-right:48px}
 .station-name{display:none}.station-logo{width:58px}.time{font-size:18px}
 .team-logo{width:40px;height:40px;flex-basis:40px}.team{font-size:12px}
}
</style>
</head>
<body>
<header class="topbar"><div class="shell" style="width:100%;display:flex;align-items:center">
 <div class="brand"><div class="brand-mark"></div><div class="brand-name">SV.LEAGUE</div><div class="brand-divider"></div><div class="brand-sub">TV BROADCAST</div></div>
 <div class="top-status">最終更新 __UPDATED__</div>
</div></header>
<section class="hero"><div class="shell">
 <div class="eyebrow">SV.LEAGUE 2026–27</div>
 <h1>テレビ放送スケジュール</h1>
 <p>放送日・放送局・試合開始時刻・対戦カードをひと目で確認</p>
</div></section>
<main class="shell">
 <div class="controls">
  <button class="filter active" data-filter="all">すべて</button>
  <button class="filter" data-filter="地上波">地上波</button>
  <button class="filter" data-filter="NHK">NHK</button>
  <button class="filter" data-filter="J SPORTS">J SPORTS</button>
  <button class="filter" data-filter="GAORA">GAORA</button>
  <button class="filter" data-filter="フジテレビ">フジテレビ</button>
  <select class="date-select" id="dateFilter"><option value="all">日付を選択</option>__DATES__</select>
 </div>
 <div class="summary"><div><h2>放送予定</h2><p>放送日順</p></div><div class="count" id="count"></div></div>
 <section class="schedule" id="schedule">__ROWS__</section>
 <div class="footer"><strong>※ 放送日時・対戦カードは変更になる場合があります。</strong><br>最新情報は各放送局の公式サイトおよびSV.LEAGUE公式発表をご確認ください。</div>
</main>
<script>
const cards=[...document.querySelectorAll('.day-card')];
const buttons=[...document.querySelectorAll('.filter')];
const dateFilter=document.getElementById('dateFilter');
const count=document.getElementById('count');
function apply(){
 const f=document.querySelector('.filter.active')?.dataset.filter||'all', d=dateFilter.value;
 let n=0;
 cards.forEach(card=>{
  const okDate=d==='all'||card.dataset.date===d; let visible=0;
  card.querySelectorAll('.broadcast-row').forEach(row=>{
   const ok=f==='all'||row.dataset.station.includes(f);
   row.style.display=ok?'grid':'none'; if(ok)visible++;
  });
  card.style.display=okDate&&visible?'block':'none'; if(okDate)n+=visible;
 });
 count.textContent=n+'件';
}
buttons.forEach(b=>b.addEventListener('click',()=>{buttons.forEach(x=>x.classList.remove('active'));b.classList.add('active');apply()}));
const STORAGE_KEY='svleague-recording-reservations-v1';
function rowKey(row){const t=row.querySelectorAll('.team');return [row.dataset.station,row.dataset.date||'',t[0]?.textContent.trim(),t[1]?.textContent.trim()].join('|')}
function loadReservations(){
 document.querySelectorAll('.broadcast-row').forEach(row=>{
  const box=row.querySelector('.record-check'); if(!box)return;
  const key=STORAGE_KEY+'|'+rowKey(row); const saved=localStorage.getItem(key)==='1';
  box.checked=saved; row.classList.toggle('reserved',saved);
  box.addEventListener('change',()=>{if(box.checked){localStorage.setItem(key,'1');row.classList.add('reserved')}else{localStorage.removeItem(key);row.classList.remove('reserved')}})
 })
}
dateFilter.addEventListener('change',apply);loadReservations();apply();
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

    def station_logo(station):
        # Use the actual broadcaster marks rather than CSS-drawn approximations.
        # The files are official broadcaster logos mirrored on Wikimedia Commons.
        if station.startswith("J SPORTS"):
            ch = station.replace("J SPORTS ", "")
            return (
                '<span class="station-lockup">'
                '<span class="station-logo js"><img src="https://commons.wikimedia.org/wiki/Special:Redirect/file/J_Sports_Logo.svg" alt="J SPORTS" loading="lazy"></span>'
                f'<span class="station-channel">{esc(ch)}</span></span>'
            )
        if station == "GAORA SPORTS":
            return '<span class="station-logo gaora"><img src="https://commons.wikimedia.org/wiki/Special:Redirect/file/GAORA_SPORTS_logo.svg" alt="GAORA SPORTS" loading="lazy"></span>'
        if station == "フジテレビNEXT":
            # Use the channel-specific Fuji TV NEXT Live Premium mark.
            return '<span class="station-logo fuji next"><img src="assets/fuji_next.png" alt="フジテレビNEXT ライブ・プレミアム" loading="lazy"></span>'
        if station == "フジテレビONE":
            return '<span class="station-logo fuji"><img src="assets/fuji_one.png" alt="フジテレビONE スポーツ・バラエティ" loading="lazy"></span>'
        if station == "フジテレビTWO":
            return '<span class="station-logo fuji"><img src="assets/fuji_two.png" alt="フジテレビTWO ドラマ・アニメ" loading="lazy"></span>'
        if station == "NHK BS":
            return '<span class="station-logo nhk"><img src="https://commons.wikimedia.org/wiki/Special:Redirect/file/NHK_BS_2023_logo.svg" alt="NHK BS" loading="lazy"></span>'
        return '<span class="station-logo">TV</span>'

    day_blocks=[]
    for d, items in sorted(grouped.items()):
        dt=date.fromisoformat(d)
        weekday="月火水木金土日"[dt.weekday()]
        body=[]
        for r in items:
            hcls="highlight" if r.home in ("東レアローズ滋賀","大阪ブルテオン") else ""
            acls="highlight" if r.away in ("東レアローズ滋賀","大阪ブルテオン") else ""
            hlogo = team_logos.get(r.home, "")
            alogo = team_logos.get(r.away, "")
            hlogo_html = f'<img class="team-logo" src="{esc(hlogo)}" alt="" loading="lazy">' if hlogo else ''
            alogo_html = f'<img class="team-logo" src="{esc(alogo)}" alt="" loading="lazy">' if alogo else ''
            body.append(
                f'<div class="broadcast-row" data-station="{esc(r.station)}" data-date="{d}">'
                f'<div class="station">{station_logo(r.station)}<span class="station-name">{esc(r.station)}</span></div>'
                f'<div class="time">{esc(r.broadcast_time or "—")}</div>'
                f'<div class="home"><span class="team-wrap">{hlogo_html}<span class="team {hcls}">{esc(r.home)}</span></span></div>'
                f'<div class="away"><span class="team-wrap">{alogo_html}<span class="team {acls}">{esc(r.away)}</span></span></div>'
                f'<div class="record-cell"><input class="record-check" type="checkbox" aria-label="録画予約"></div>'
                f'</div>'
            )
        day_blocks.append(
            f'<div class="day-card" data-date="{d}">'
            f'<div class="day-head"><span class="day-date">{d[5:].replace("-", ".")}</span><span class="day-week">（{weekday}）</span></div>'
            f'<div class="grid-head"><div>放送局</div><div>試合開始</div><div>ホームチーム</div><div>アウェイチーム</div><div>録画予約</div></div>'
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
        try:
            scrape_jsports_official(page, rows)
        except Exception as e:
            print("J SPORTS ERROR:", e)
        try:
            scrape_jcom(page, rows)
        except Exception as e:
            print("J:COM ERROR:", e)
        try:
            scrape_social_and_regional(page, rows)
        except Exception as e:
            print("SOCIAL/REGIONAL ERROR:", e)
        team_logos = scrape_team_logos(page)
        browser.close()

    rows = reconcile(rows)
    try:
        validate_team_logos(team_logos, rows)
    except Exception as e:
        print("VALIDATION FAILED:", e)
        prev = load_previous()
        if prev:
            write_outputs(prev, team_logos if "team_logos" in locals() else {})
        raise SystemExit(2)
    ok, msg = validate(rows, official_ok)
    if not ok:
        print("VALIDATION FAILED:", msg)
        prev = load_previous()
        if prev:
            write_outputs(prev, team_logos if "team_logos" in locals() else {})
        raise SystemExit(2)

    write_outputs(rows, team_logos)
    print(f"OK: {len(rows)} rows")

if __name__ == "__main__":
    main()
