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
                href = links.nth(i).get_attribute("href")
                if href and "/news/detail/" in href:
                    if href.startswith("/"):
                        href = "https://www.svleague.jp" + href
                    urls.add(href.split("#")[0])
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

