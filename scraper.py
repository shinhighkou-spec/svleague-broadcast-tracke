from __future__ import annotations
import csv, json, os, re, urllib.parse
import xml.etree.ElementTree as ET

def flag_source_discovery_degraded(reason):
    """Surface incomplete optional-source discovery to GitHub Actions without discarding verified rows."""
    message = re.sub(r"\s+", " ", str(reason)).strip()
    print("::warning::SOURCE DISCOVERY DEGRADED:", message)
    env_file = os.environ.get("GITHUB_ENV")
    if env_file:
        try:
            with open(env_file, "a", encoding="utf-8") as handle:
                handle.write("SV_SOURCE_DISCOVERY_DEGRADED=true\n")
        except OSError as e:
            print("SOURCE DISCOVERY STATUS FLAG ERROR:", e)

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
    "https://www.svleague.jp/news/detail/100609/?grade=sv",
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
    match_start_time: str = ""

TEAM_MAP = {
    "大阪Ｂ": "大阪ブルテオン",
    "大阪ブルテオン": "大阪ブルテオン",
    "大阪ブルテオン（男子）": "大阪ブルテオン",
    "WD名古屋": "ウルフドッグス名古屋",
    "ウルフドッグス名古屋": "ウルフドッグス名古屋",
    "北海道YS": "北海道イエロースターズ",
    "北海道イエロースターズ": "北海道イエロースターズ",
    "フラーゴラッド鹿児島": "フラーゴラッド鹿児島",
    "信州松本トライデンツ": "信州松本トライデンツ",
    "ヴォレアス北海道": "ヴォレアス北海道",
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
    "フジテレビONE", "フジテレビTWO", "フジテレビNEXT", "NHK BS", "BS10", "BS無料放送（局名未公表）", "J SPORTS（チャンネル未公表）", "サンテレビジョン", "群馬テレビ",
}

TEAM_NAMES = sorted(set(TEAM_MAP.values()), key=len, reverse=True)
# Search aliases used by broadcasters and team media. These are only used for
# discovery/matching; the published dataset keeps the canonical SV.LEAGUE names.
SEARCH_TEAM_ALIASES = {
    "アランマーレ山形": ["アランマーレ山形", "アランマーレ秋田庄内"],
    "ＫＵＲＯＢＥアクアフェアリーズ": ["ＫＵＲＯＢＥアクアフェリーズ", "ＫＵＲＯＢＥアクアフェアリーズ富山"],
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

def add(rows, station, d, match, source, t="", match_start_time=""):
    station = clean_station(station)
    if station not in VALID_STATIONS:
        return
    if not d or not valid_season_date(d) or not match:
        return
    rows.append(Broadcast(station, d, match[0], match[1], source, t, match_start_time))

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

            combined_heading = False
            if not station:
                try:
                    headings = table.locator("xpath=preceding::h1 | preceding::h2 | preceding::h3 | preceding::h4")
                    if headings.count():
                        last_heading = re.sub(r"\\s+", "", headings.nth(headings.count()-1).inner_text())
                        combined_heading = any(token in last_heading for token in (
                            "フジテレビONE/TWO/NEXT", "フジテレビONE／TWO／NEXT",
                            "JSPORTS1/2/3/4", "JSPORTS1／2／3／4"
                        ))
                except Exception:
                    pass
                if not combined_heading:
                    continue

            for j in range(row_locator.count()):
                try:
                    row_text = " ".join(row_locator.nth(j).locator("th,td").all_inner_texts())
                except Exception:
                    continue
                row_station = next((st for st in sorted(VALID_STATIONS, key=len, reverse=True) if st in row_text), None)
                station_for_row = row_station or station
                if not station_for_row:
                    continue
                item = extract_broadcast_item(row_text, station_for_row)
                if item:
                    parsed_station, d, match, tm = item
                    # SV.LEAGUE's table column is explicitly labelled "試合開始".
                    # Keep this time separately; it is not the TV programme start.
                    add(rows, parsed_station, d, match, url, "", tm)
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

def parse_jsports_golden_live_tv(text: str):
    """Parse explicit J SPORTS Golden Live TV airings, including replay times.
    This parser intentionally excludes LIVE/on-demand-only entries."""
    text = re.sub(r"\s+", " ", text).strip()
    pattern = re.compile(
        r"(?P<kind>生放送|録画放送)\s*(?P<month>\d{1,2})月(?P<day>\d{1,2})日"
        r"(?:[（(][^）)]*[）)])?\s*(?:午前|午後|深夜)\s*\d{1,2}:\d{2}\s*[～〜~]\s*"
        r"(?P<event>.*?)(?=(?:生放送|録画放送)\s*\d{1,2}月\d{1,2}日|ご視聴方法|$)"
    )
    events = []
    for m in pattern.finditer(text):
        month, day = int(m.group("month")), int(m.group("day"))
        d = f"{2026 if month >= 9 else 2027:04d}-{month:02d}-{day:02d}"
        match = parse_match(m.group(0))
        tm = parse_jsports_time(m.group(0))
        if match and tm and valid_season_date(d):
            events.append((m.group("kind"), d, match, tm))
    return events


def scrape_jsports_golden_live(page, rows):
    """Collect J SPORTS' explicit TV schedule, including distinct recorded replays.
    Channel is left unspecified when the official page does not identify it."""
    url = "https://www.jsports.co.jp/volleyball/svleague/golden_live/"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(900)
    body = page.locator("body").text_content(timeout=10000) or ""
    events = parse_jsports_golden_live_tv(body)
    facts = known_facts()
    accepted = 0
    for kind, d, match, tm in events:
        home, away = match
        if kind == "生放送":
            # The official SV.LEAGUE article already supplies the authoritative
            # channel/time for known live broadcasts. Do not add a duplicate
            # generic J SPORTS row for the same airing.
            channel_known = any(
                r.station in {"J SPORTS 1", "J SPORTS 2", "J SPORTS 3", "J SPORTS 4"}
                and r.broadcast_date == d and r.home == home and r.away == away
                for r in rows + facts
            )
            if channel_known:
                continue
        channel_airing_known = any(
            r.station in {"J SPORTS 1", "J SPORTS 2", "J SPORTS 3", "J SPORTS 4"}
            and r.broadcast_date == d and r.home == home and r.away == away
            and r.broadcast_time == tm
            for r in rows + facts
        )
        if channel_airing_known:
            continue
        source = f"{url} | {kind}"
        station = "J SPORTS（チャンネル未公表）"
        if any(
            r.station == station and r.broadcast_date == d
            and r.home == home and r.away == away and r.broadcast_time == tm
            for r in rows + facts
        ):
            continue
        add(rows, station, d, match, source, tm)
        accepted += 1
    print("J SPORTS GOLDEN LIVE TV EVENTS:", len(events))
    print("J SPORTS GOLDEN LIVE TV ADDED:", accepted)


def parse_jsports_official_section(section: str):
    """Extract dated match candidates from a J SPORTS official TV schedule section."""
    team_pattern = "(?:" + "|".join(re.escape(name) for name in TEAM_NAMES) + ")"
    pattern = re.compile(
        r"(\d{1,2})月(\d{1,2})日(?:（[^）]+）)?.{0,260}?"
        r"(?:大同生命)?SV(?:\.LEAGUE|リーグ)[^。]{0,180}?"
        + team_pattern + r"\s*(?:vs\.?|VS|対)\s*" + team_pattern
    )
    out = []
    for m in pattern.finditer(section):
        month, day = int(m.group(1)), int(m.group(2))
        d = f"{2026 if month >= 9 else 2027:04d}-{month:02d}-{day:02d}"
        match = parse_match(m.group(0))
        if match and valid_season_date(d):
            out.append((d, match, parse_jsports_time(m.group(0))))
    return out


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
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(700)
            text = re.sub(r"\s+", " ", page.locator("body").inner_text(timeout=10000)).strip()
            m = re.search(r"放送予定(.*?)(?:番組表のアイコン|無料動画|新着記事|テーマ曲|$)", text)
            section = m.group(1) if m else ""
            if not section:
                print("J SPORTS OFFICIAL SECTION MISSING:", url)
                continue
            for d, match, tm in parse_jsports_official_section(section):
                candidates.append((d, match, tm, url))
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

def _extract_explicit_airtime(text):
    """Return a time only when the source labels it as a broadcast/programme start."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    patterns = (
        r"(?:放送開始|放送時間|中継開始)[^\d]{0,20}(\d{1,2}):(\d{2})",
        r"(\d{1,2})時(\d{1,2})分?\s*(?:から|より)\s*(?:放送|生中継|中継)",
        r"(?:放送|生中継|中継)[^。\n]{0,35}?(\d{1,2}):(\d{2})\s*(?:～|〜|-|から)",
    )
    for index, pattern in enumerate(patterns):
        m = re.search(pattern, text)
        if not m:
            continue
        if index == 1:
            hour, minute = int(m.group(1)), int(m.group(2) or 0)
        else:
            hour, minute = int(m.group(1)), int(m.group(2))
        if hour > 23 or minute > 59:
            continue
        return f"{hour:02d}:{minute:02d}"
    return ""


def _extract_search_broadcast_date(text, match):
    """Find a season date tied to a matchup, not a bare article publication date."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    for sentence in re.split(r"(?<=[。！？])", text):
        if not any(st in sentence for st in VALID_STATIONS):
            continue
        if not any(word in sentence for word in BROADCAST_WORDS):
            continue
        date_matches = list(re.finditer(r"(?<!\d)(\d{1,2})月(\d{1,2})日", sentence))
        for index, m in enumerate(date_matches):
            month, day = int(m.group(1)), int(m.group(2))
            candidate = f"{2026 if month >= 9 else 2027:04d}-{month:02d}-{day:02d}"
            if not valid_season_date(candidate):
                continue
            end = date_matches[index + 1].start() if index + 1 < len(date_matches) else len(sentence)
            segment = sentence[m.end():end]
            if parse_match(segment) == match:
                return candidate

    # Full dates are accepted only when explicitly labelled as a broadcast/event date.
    for sentence in re.split(r"(?<=[。！？])", text):
        if not any(st in sentence for st in VALID_STATIONS):
            continue
        if not any(word in sentence for word in BROADCAST_WORDS):
            continue
        for m in re.finditer(r"(20\d{2})[./年-](\d{1,2})[./月-](\d{1,2})", sentence):
            prefix = sentence[max(0, m.start() - 24):m.start()]
            if not re.search(r"(?:放送日|放送日時|中継日|開催日)", prefix):
                continue
            candidate = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            if not valid_season_date(candidate):
                continue
            end = sentence.find("。", m.end())
            segment = sentence[m.end():end if end >= 0 else len(sentence)]
            if parse_match(segment) == match:
                return candidate
    return None


def _extract_search_broadcast(text, require_time=False):
    """Extract a source-page candidate; time is populated only if airtime is explicit."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    match = parse_match(text)
    if not match:
        return None
    d = _extract_search_broadcast_date(text, match)
    if not d:
        return None

    station = None
    for st in sorted(VALID_STATIONS, key=len, reverse=True):
        if st in text:
            station = st
            break
    if not station and re.search(r"\btvk\b", text, re.I):
        station = "テレビ神奈川"
    if not station or not any(w in text for w in BROADCAST_WORDS):
        return None

    tm = _extract_explicit_airtime(text)
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
    # Some X posts expose image descriptions only through alt/ARIA metadata.
    # Include those in source evidence so accessible schedule-image text is not
    # discarded before verification.
    for selector in ('img[alt]', 'img[aria-label]', '[role="img"][aria-label]'):
        try:
            loc = page.locator(selector)
            for i in range(min(loc.count(), 30)):
                value = loc.nth(i).get_attribute("alt") or loc.nth(i).get_attribute("aria-label")
                if value:
                    parts.append(value)
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

def _verify_search_result(page, title, href, snippet, require_time=True):
    """Open a search result and require the source page itself to confirm the broadcast.
    Official SV.LEAGUE posts may be accepted without a time when their announcement
    omits it; other discovery sources still require an explicit time."""
    candidate = _extract_search_broadcast(" ".join((title, snippet)), require_time=False)
    if not candidate or not href:
        return None
    try:
        page.goto(href, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(700)
        evidence = _page_evidence_text(page)
        verified = _extract_search_broadcast(evidence, require_time=require_time)
        if not verified:
            return None
        if verified[:3] != candidate[:3]:
            return None
        return verified
    except Exception as e:
        print("SEARCH RESULT VERIFY ERROR:", href, e)
        return None


VOLLEYBALLKING_LISTING_URLS = (
    "https://volleyballking.jp/",
    "https://volleyballking.jp/league/svleague/",
    "https://volleyballking.jp/league/svleague/page/2/",
    "https://volleyballking.jp/league/svleague/page/3/",
    "https://volleyballking.jp/league/svleague-men/",
    "https://volleyballking.jp/league/svleague-women/",
)
VOLLEYBALLKING_TITLE_TERMS = (
    "放送", "生中継", "中継", "テレビ", "tvk", "地上波", "BS", "CS",
    "メディアパートナー", "番組表", "テレビ局",
)


VOLLEYBALLKING_DISCOVERY_URLS = (
    "https://volleyballking.jp/sitemap.xml",
    "https://volleyballking.jp/sitemap_index.xml",
    "https://volleyballking.jp/sitemap-index.xml",
    "https://volleyballking.jp/wp-sitemap.xml",
    "https://volleyballking.jp/feed/",
    "https://volleyballking.jp/feed",
    "https://volleyballking.jp/rss.xml",
    "https://volleyballking.jp/atom.xml",
)

def _volleyballking_local_name(tag):
    return str(tag).rsplit("}", 1)[-1].casefold()

def _normalise_volleyballking_url(href, base_url):
    """Accept only first-party VolleyballKing URLs; discard tracking/query fragments."""
    if not href:
        return None
    absolute = urllib.parse.urljoin(base_url, str(href).strip())
    parsed = urllib.parse.urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    if (parsed.hostname or "").casefold() not in {"volleyballking.jp", "www.volleyballking.jp"}:
        return None
    return urllib.parse.urlunparse(("https", "volleyballking.jp", parsed.path, "", "", ""))

def _normalise_volleyballking_article_url(href, base_url):
    url = _normalise_volleyballking_url(href, base_url)
    if not url:
        return None
    path = urllib.parse.urlparse(url).path
    if not re.fullmatch(r"/article/\d+/?", path):
        return None
    return "https://volleyballking.jp" + path.rstrip("/") + "/"

def _parse_volleyballking_discovery_document(document_url, content):
    """Parse robots.txt, sitemap XML, RSS and Atom as discovery hints only.

    Returned article URLs are candidates, never broadcast facts. The article page
    must still independently confirm station, broadcast date, teams and airtime.
    """
    sitemap_urls = []
    article_entries = []
    parsed_url = urllib.parse.urlparse(document_url)
    if parsed_url.path.casefold().endswith("/robots.txt"):
        for line in content.splitlines():
            m = re.match(r"\s*sitemap\s*:\s*(\S+)", line, re.I)
            if m:
                url = _normalise_volleyballking_url(m.group(1), document_url)
                if url:
                    sitemap_urls.append((url, ""))
        return list(dict.fromkeys(sitemap_urls)), [], "robots"

    try:
        root = ET.fromstring(content)
    except (ET.ParseError, ValueError, TypeError):
        return [], [], None

    root_name = _volleyballking_local_name(root.tag)

    def child_text(node, wanted):
        for child in node:
            if _volleyballking_local_name(child.tag) == wanted:
                return (child.text or "").strip()
        return ""

    if root_name == "sitemapindex":
        for node in root:
            if _volleyballking_local_name(node.tag) != "sitemap":
                continue
            loc = child_text(node, "loc")
            url = _normalise_volleyballking_url(loc, document_url)
            if url:
                sitemap_urls.append((url, child_text(node, "lastmod")))
        sitemap_urls.sort(key=lambda item: item[1], reverse=True)
        return sitemap_urls, [], "sitemap-index"

    if root_name == "urlset":
        for node in root:
            if _volleyballking_local_name(node.tag) != "url":
                continue
            loc = child_text(node, "loc")
            article_url = _normalise_volleyballking_article_url(loc, document_url)
            if article_url:
                article_entries.append((article_url, child_text(node, "lastmod")))
        article_entries.sort(key=lambda item: item[1], reverse=True)
        return [], article_entries, "sitemap-urlset"

    if root_name in {"rss", "feed", "rdf"}:
        for node in root.iter():
            tag = _volleyballking_local_name(node.tag)
            if tag == "item":
                href = child_text(node, "link") or child_text(node, "guid")
                published = child_text(node, "pubdate") or child_text(node, "date")
                article_url = _normalise_volleyballking_article_url(href, document_url)
                if article_url:
                    article_entries.append((article_url, published))
            elif tag == "entry":
                href = ""
                for child in node:
                    if _volleyballking_local_name(child.tag) == "link":
                        rel = child.attrib.get("rel", "alternate")
                        if rel in ("alternate", ""):
                            href = child.attrib.get("href") or (child.text or "").strip()
                            if href:
                                break
                published = child_text(node, "updated") or child_text(node, "published")
                article_url = _normalise_volleyballking_article_url(href, document_url)
                if article_url:
                    article_entries.append((article_url, published))
        return [], article_entries, "feed"

    return [], [], None

def _extract_volleyballking_jsonld_articles(script_texts):
    """Extract first-party article URLs/titles from JSON-LD without treating them as facts."""
    found = {}
    article_types = {"article", "newsarticle", "blogposting", "reportagenewsarticle"}

    def visit(value):
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return

        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]
        is_article = any(str(item).casefold() in article_types for item in types)
        title = re.sub(r"\s+", " ", str(value.get("headline") or value.get("name") or "")).strip()
        raw_url = value.get("url") or value.get("@id")
        main_entity = value.get("mainEntityOfPage")
        if not raw_url and isinstance(main_entity, dict):
            raw_url = main_entity.get("url") or main_entity.get("@id")
        elif not raw_url and isinstance(main_entity, str):
            raw_url = main_entity
        url = _normalise_volleyballking_article_url(raw_url, "https://volleyballking.jp/")
        if is_article and url and title and any(term.casefold() in title.casefold() for term in VOLLEYBALLKING_TITLE_TERMS):
            found.setdefault(url, title)

        for child in value.values():
            if isinstance(child, (dict, list)):
                visit(child)

    for raw in script_texts:
        try:
            visit(json.loads(raw))
        except (json.JSONDecodeError, TypeError) as e:
            print("VOLLEYBALLKING JSON-LD PARSE ERROR:", type(e).__name__)
    return list(found.items())


def _merge_volleyballking_sitemap_candidates(target, sitemap_rows, visited):
    """Keep child sitemaps even when the index omits lastmod metadata."""
    for url, lastmod in sitemap_rows:
        if url in visited:
            continue
        old = target.get(url, "")
        if url not in target or lastmod > old:
            target[url] = lastmod

def _discover_volleyballking_supplemental_articles(page):
    """Probe robots.txt, declared/common sitemaps and RSS/Atom feeds.

    Failures are logged as failures, not interpreted as an empty article list.
    The URLs discovered here are only candidates and must pass article-page parsing.
    """
    request = page.request
    robots_url = "https://volleyballking.jp/robots.txt"
    declared_sitemaps = []
    try:
        response = request.get(robots_url, timeout=15000)
        if response.status == 200:
            body = response.text()
            sitemap_rows, _, _ = _parse_volleyballking_discovery_document(robots_url, body)
            declared_sitemaps = [url for url, _ in sitemap_rows]
            print("VOLLEYBALLKING ROBOTS OK:", robots_url, "declared_sitemaps", len(declared_sitemaps))
        else:
            print("VOLLEYBALLKING ROBOTS FETCH ERROR:", robots_url, "status", response.status)
    except Exception as e:
        print("VOLLEYBALLKING ROBOTS FETCH ERROR:", robots_url, e)

    initial_urls = list(dict.fromkeys(declared_sitemaps + list(VOLLEYBALLKING_DISCOVERY_URLS)))
    visited = set()
    child_sitemaps = {}
    article_lastmod = {}
    article_titles = {}
    valid_sources = []

    def inspect_source(url):
        if url in visited:
            return
        visited.add(url)
        try:
            response = request.get(url, timeout=15000)
            if response.status != 200:
                print("VOLLEYBALLKING DISCOVERY SOURCE UNAVAILABLE:", url, "status", response.status)
                return
            body = response.text()
            if len(body) > 5_000_000:
                print("VOLLEYBALLKING DISCOVERY SOURCE SKIPPED (over 5 MB):", url)
                return
            sitemaps, articles, kind = _parse_volleyballking_discovery_document(url, body)
            if kind is None:
                print("VOLLEYBALLKING DISCOVERY SOURCE UNRECOGNIZED:", url)
                return
            valid_sources.append((url, kind))
            print("VOLLEYBALLKING DISCOVERY SOURCE OK:", url, kind, "articles", len(articles), "child_sitemaps", len(sitemaps))
            _merge_volleyballking_sitemap_candidates(child_sitemaps, sitemaps, visited)
            if kind == "feed":
                for article_url, title in _extract_volleyballking_feed_titles(url, body).items():
                    old_title = article_titles.get(article_url, "")
                    title_is_relevant = any(term.casefold() in title.casefold() for term in VOLLEYBALLKING_TITLE_TERMS)
                    old_title_is_relevant = any(term.casefold() in old_title.casefold() for term in VOLLEYBALLKING_TITLE_TERMS)
                    if not old_title or (title_is_relevant and not old_title_is_relevant):
                        article_titles[article_url] = title
            for article_url, lastmod in articles:
                old = article_lastmod.get(article_url, "")
                if article_url not in article_lastmod or lastmod > old:
                    article_lastmod[article_url] = lastmod
        except Exception as e:
            print("VOLLEYBALLKING DISCOVERY SOURCE FETCH ERROR:", url, e)

    for url in initial_urls[:12]:
        inspect_source(url)

    # Follow only a bounded number of newest child sitemaps; never crawl an
    # unbounded sitemap tree in a scheduled run.
    for url, _ in sorted(child_sitemaps.items(), key=lambda item: (item[1] or "", item[0]), reverse=True)[:5]:
        inspect_source(url)

    urls = _prioritize_volleyballking_article_urls(article_lastmod, article_titles)
    title_matches = sum(
        1 for title in article_titles.values()
        if any(term.casefold() in title.casefold() for term in VOLLEYBALLKING_TITLE_TERMS)
    )
    print("VOLLEYBALLKING DISCOVERY VALID SOURCES:", len(valid_sources))
    print("VOLLEYBALLKING DISCOVERY CANDIDATE ARTICLES:", len(urls))
    print("VOLLEYBALLKING FEED TITLES RETAINED:", len(article_titles))
    print("VOLLEYBALLKING FEED TITLES MATCHING BROADCAST TERMS:", title_matches)
    if len(child_sitemaps) > 5:
        print("VOLLEYBALLKING DISCOVERY CHILD SITEMAPS DEFERRED:", len(child_sitemaps) - 5)
    if len(urls) > 100:
        print("VOLLEYBALLKING DISCOVERY ARTICLE URLS DEFERRED:", len(urls) - 100)
    return urls[:100]

def _extract_volleyballking_feed_titles(document_url, content):
    """Retain RSS/Atom article titles as discovery metadata for prioritization only."""
    try:
        root = ET.fromstring(content)
    except (ET.ParseError, ValueError, TypeError):
        return {}

    found = {}
    for node in root.iter():
        tag = _volleyballking_local_name(node.tag)
        if tag not in {"item", "entry"}:
            continue
        title = ""
        href = ""
        fallback_href = ""
        for child in node:
            child_tag = _volleyballking_local_name(child.tag)
            value = (child.text or "").strip()
            if child_tag == "title":
                title = re.sub(r"\s+", " ", value).strip()
            elif child_tag == "link":
                if tag == "entry":
                    rel = child.attrib.get("rel", "alternate")
                    if rel in ("alternate", ""):
                        href = child.attrib.get("href") or value
                elif value and not href:
                    href = value
            elif child_tag == "guid" and value:
                fallback_href = value
        article_url = _normalise_volleyballking_article_url(href, document_url)
        if not article_url:
            article_url = _normalise_volleyballking_article_url(fallback_href, document_url)
        if article_url and title:
            found[article_url] = title
    return found


def _prioritize_volleyballking_article_urls(article_lastmod, article_titles):
    """Prioritize broadcast-related feed titles; title metadata never confirms a broadcast."""
    ordered = sorted(article_lastmod.items(), key=lambda item: item[1] or "", reverse=True)

    def title_matches(url):
        title = article_titles.get(url, "").casefold()
        return any(term.casefold() in title for term in VOLLEYBALLKING_TITLE_TERMS)

    relevant = [url for url, _ in ordered if title_matches(url)]
    other = [url for url, _ in ordered if not title_matches(url)]
    return relevant + other


def _extract_volleyballking_broadcasts(text):
    """Extract multiple explicit station/date/match pairs from an opened article.

    A sentence must contain exactly one recognized station and an explicit TV
    broadcast term. Article publication timestamps are ignored; a missing
    broadcast start time stays blank rather than borrowing the match start.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not any(term.casefold() in text.casefold() for term in VOLLEYBALLKING_TITLE_TERMS):
        return []

    found = []
    seen = set()
    sentences = re.split(r"(?<=[。！？])", text)
    for sentence in sentences:
        stations = [st for st in sorted(VALID_STATIONS, key=len, reverse=True) if st in sentence]
        stations = list(dict.fromkeys(stations))
        if len(stations) != 1:
            # A sentence mentioning multiple channels cannot safely map every
            # card to one station; skip it rather than guessing.
            continue
        station = stations[0]
        if not re.search(r"(?:放送|生中継|中継|テレビ)", sentence):
            continue

        dates = list(re.finditer(r"(?<!\d)(\d{1,2})月(\d{1,2})日", sentence))
        for index, date_match in enumerate(dates):
            month, day = int(date_match.group(1)), int(date_match.group(2))
            candidate_date = f"{2026 if month >= 9 else 2027:04d}-{month:02d}-{day:02d}"
            if not valid_season_date(candidate_date):
                continue
            segment_end = dates[index + 1].start() if index + 1 < len(dates) else len(sentence)
            segment = sentence[date_match.end():segment_end]
            match = parse_match(segment)
            if not match:
                continue

            # Only parse explicitly labelled broadcast times. A standalone
            # "試合開始 13:05" is deliberately not accepted as airing time.
            airtime = ""
            time_match = re.search(
                r"(\d{1,2})時(\d{1,2})分\s*(?:から|より)\s*(?:放送|生中継|中継)",
                segment,
            )
            if time_match:
                airtime = f"{int(time_match.group(1)):02d}:{int(time_match.group(2)):02d}"
            if not airtime:
                time_match = re.search(
                    r"(?:放送開始|放送時間|中継開始)[^\d]{0,12}(\d{1,2}):(\d{2})",
                    segment,
                )
                if time_match:
                    airtime = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
            if not airtime:
                time_match = re.search(
                    r"(?:放送|生中継|中継)[^。]{0,35}?(\d{1,2}):(\d{2})\s*(?:～|〜|-)",
                    segment,
                )
                if time_match:
                    airtime = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"

            item = (station, candidate_date, match, airtime)
            if item not in seen:
                seen.add(item)
                found.append(item)
    return found


def _extract_volleyballking_broadcast(text):
    """Parse explicit broadcast evidence from a VolleyballKing article.
    Article publication dates are not treated as broadcast dates. The source
    must state the match date, channel, broadcast start time, and both teams.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not any(term.casefold() in text.casefold() for term in VOLLEYBALLKING_TITLE_TERMS):
        return None

    station = None
    for st in sorted(VALID_STATIONS, key=len, reverse=True):
        if st in text:
            station = st
            break
    if not station and re.search(r"\btvk\b", text, re.I):
        station = "テレビ神奈川"
    if not station:
        return None

    match = parse_match(text)
    if not match:
        return None

    # Prefer an explicit Japanese month/day in the article body. Do not use
    # the article's publication timestamp as a broadcast date.
    d = None
    for m in re.finditer(r"(?<!\d)(\d{1,2})月(\d{1,2})日", text):
        month, day = int(m.group(1)), int(m.group(2))
        candidate = f"{2026 if month >= 9 else 2027:04d}-{month:02d}-{day:02d}"
        if valid_season_date(candidate):
            d = candidate
            break
    if not d:
        # Full dates are accepted only when explicitly labelled as a broadcast
        # date, not when they appear as an article publication date.
        m = re.search(
            r"(?:放送日|放送日時|放送予定|放送開始日)[^\d]{0,12}"
            r"(20\d{2})[./年-](\d{1,2})[./月-](\d{1,2})",
            text,
        )
        if m:
            candidate = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            if valid_season_date(candidate):
                d = candidate
    if not d:
        return None

    # Extract the broadcast start time, not the match start time.
    tm = ""
    m = re.search(r"(\d{1,2})時(\d{1,2})分\s*(?:から|より)\s*(?:放送|生中継|中継)", text)
    if m:
        tm = f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
    if not tm:
        m = re.search(r"(?:放送開始|放送時間|中継開始)[^\d]{0,12}(\d{1,2}):(\d{2})", text)
        if m:
            tm = f"{int(m.group(1)):02d}:{m.group(2)}"
    if not tm:
        m = re.search(r"(?:放送|生中継|中継)[^。]{0,35}?(\d{1,2}):(\d{2})\s*(?:～|〜|-)", text)
        if m:
            tm = f"{int(m.group(1)):02d}:{m.group(2)}"
    if not tm:
        return None
    return station, d, match, tm

def scrape_volleyballking(page, rows):
    """Daily direct crawl of VolleyballKing's latest/SV article listings."""
    article_links = {}
    listing_successes = 0
    for url in VOLLEYBALLKING_LISTING_URLS:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(500)
            listing_successes += 1
            links = page.locator('a[href*="/article/"]')
            for i in range(links.count()):
                link = links.nth(i)
                try:
                    href = link.get_attribute("href") or ""
                    title = re.sub(r"\s+", " ", link.inner_text(timeout=1500)).strip()
                    if not href:
                        continue
                    if href.startswith("/"):
                        href = "https://volleyballking.jp" + href
                    href = href.split("#")[0].split("?")[0]
                    if "/article/" not in href:
                        continue
                    if any(term.casefold() in title.casefold() for term in VOLLEYBALLKING_TITLE_TERMS):
                        article_links[href] = title
                except Exception:
                    continue
            try:
                for href, title in _extract_volleyballking_jsonld_articles(
                    page.locator('script[type="application/ld+json"]').all_text_contents()
                ):
                    if href not in article_links:
                        article_links[href] = title
                        print("VOLLEYBALLKING JSON-LD CANDIDATE:", href, "|", title)
            except Exception as e:
                print("VOLLEYBALLKING JSON-LD READ ERROR:", url, e)
        except Exception as e:
            print("VOLLEYBALLKING LIST ERROR:", url, e)

    supplemental_urls = _discover_volleyballking_supplemental_articles(page)
    if listing_successes == 0 and not article_links and not supplemental_urls:
        raise RuntimeError("Could not fetch any VolleyballKing listing, RSS feed or sitemap")

    accepted = 0
    needs_review = 0
    already_covered = 0
    # RSS/Atom titles prioritize likely broadcast articles, but title metadata
    # never confirms a broadcast. Every candidate is opened and parsed.
    listing_candidates = list(article_links.items())[:20]
    listing_urls = set(article_links)
    supplemental_candidates = [(href, "") for href in supplemental_urls if href not in listing_urls][:10]
    for href, title in listing_candidates + supplemental_candidates:
        try:
            page.goto(href, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(350)
            evidence = _page_evidence_text(page)
            article_text = title + " " + evidence
            items = _extract_volleyballking_broadcasts(article_text)
            if not items:
                article_stations = [st for st in VALID_STATIONS if st in article_text]
                if len(article_stations) == 1:
                    single_item = _extract_volleyballking_broadcast(article_text)
                    if single_item:
                        items = [single_item]
            if not items:
                needs_review += 1
                print("VOLLEYBALLKING NEEDS REVIEW:", href, "|", title)
                continue

            for station, d, match, tm in items:
                identity = (station, d, match[0], match[1])
                existing_records = list(rows) + load_previous() + known_facts()
                exact_existing = any(
                    (r.station, r.broadcast_date, r.home, r.away) == identity
                    and (not tm or r.broadcast_time == tm)
                    for r in existing_records
                )
                # A time-less secondary-source row must not duplicate a known
                # official/broadcaster row or overwrite its broadcast time.
                if exact_existing or (not tm and any(
                    (r.station, r.broadcast_date, r.home, r.away) == identity
                    for r in existing_records
                )):
                    already_covered += 1
                    print("VOLLEYBALLKING CONFIRMS EXISTING ROW:", station, d, match[0], "vs", match[1], "|", href)
                    continue
                add(rows, station, d, match, href, tm)
                accepted += 1
                print("VOLLEYBALLKING ACCEPTED:", station, d, tm, match[0], "vs", match[1], "|", href)
        except Exception as e:
            print("VOLLEYBALLKING ARTICLE ERROR:", href, e)
    print("VOLLEYBALLKING LISTINGS OK:", listing_successes)
    print("VOLLEYBALLKING LISTING/JSON-LD CANDIDATES:", len(article_links))
    print("VOLLEYBALLKING LISTING CANDIDATES PROCESSED:", len(listing_candidates))
    print("VOLLEYBALLKING SUPPLEMENTAL CANDIDATES PROCESSED:", len(supplemental_candidates))
    if len(article_links) > len(listing_candidates):
        print("VOLLEYBALLKING LISTING CANDIDATES DEFERRED:", len(article_links) - len(listing_candidates))
    if len(supplemental_urls) > len(supplemental_candidates):
        print("VOLLEYBALLKING SUPPLEMENTAL CANDIDATES DEFERRED:", len(supplemental_urls) - len(supplemental_candidates))
    print("VOLLEYBALLKING ACCEPTED:", accepted)
    print("VOLLEYBALLKING CONFIRMED ALREADY-COVERED ROWS:", already_covered)
    print("VOLLEYBALLKING NEEDS REVIEW:", needs_review)


GUNMA_TV_URL = "https://www.gtv.co.jp/timetable/"

def _parse_gunma_tv_airtime(text):
    """Parse an explicitly labeled broadcast-start time from Gunma TV's timetable."""
    m = re.search(
        r"(午前|午後)?\s*(\d{1,2})(?::(\d{2})|時(?:(\d{1,2})分?)?)"
        r"\s*(?:～|〜|~|−|-|から|より)?\s*(?:生中継|中継|放送)",
        text,
    )
    if not m:
        return ""
    period, hour_text, colon_minute, japanese_minute = m.groups()
    hour = int(hour_text)
    minute = int(colon_minute or japanese_minute or 0)
    if period == "午後" and hour < 12:
        hour += 12
    elif period == "午前" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return ""
    return f"{hour:02d}:{minute:02d}"

def _parse_gunma_tv_schedule(text):
    """Parse only dated Gunma Green Wings TV listings with an explicit airing time."""
    text = re.sub(r"\s+", " ", text).strip()
    date_matches = list(re.finditer(
        r"(?<!\d)(\d{1,2})月(\d{1,2})日(?:\s*[（(][月火水木金土日][）)])?",
        text,
    ))
    found = []
    seen = set()
    for i, date_match in enumerate(date_matches):
        start = date_match.end()
        end = date_matches[i + 1].start() if i + 1 < len(date_matches) else min(len(text), start + 300)
        chunk = text[start:end]
        if "群馬グリーンウイングス" not in chunk:
            continue
        if not any(word in chunk for word in ("生中継", "中継", "放送")):
            continue
        match = parse_match(chunk)
        if not match:
            print("GUNMA TV NEEDS REVIEW (matchup):", date_match.group(0), chunk[:140])
            continue
        airtime = _parse_gunma_tv_airtime(chunk)
        if not airtime:
            print("GUNMA TV NEEDS REVIEW (airtime):", date_match.group(0), chunk[:140])
            continue
        month, day = int(date_match.group(1)), int(date_match.group(2))
        year = 2026 if month >= 9 else 2027
        broadcast_date = f"{year:04d}-{month:02d}-{day:02d}"
        if not valid_season_date(broadcast_date):
            continue
        key = (broadcast_date, match, airtime)
        if key not in seen:
            seen.add(key)
            found.append((broadcast_date, match, airtime))
    return found

def scrape_gunma_tv(page, rows):
    """Directly read Gunma TV's official monthly timetable; search snippets are not used."""
    page.goto(GUNMA_TV_URL, wait_until="domcontentloaded", timeout=45000)
    # The monthly timetable is rendered asynchronously on some runs. Wait for
    # the team name before reading the body instead of treating an early,
    # incomplete DOM as an empty schedule.
    try:
        page.locator("text=群馬グリーンウイングス").first.wait_for(timeout=10000)
    except Exception as e:
        print("GUNMA TV CONTENT WAIT WARNING:", e)
    page.wait_for_timeout(300)
    body = page.locator("body").inner_text(timeout=10000)
    if not body.strip():
        raise RuntimeError(f"Gunma TV timetable returned empty text at {page.url}")
    parsed = _parse_gunma_tv_schedule(body)
    if not parsed:
        print("GUNMA TV PAGE TEXT DIAGNOSTIC:", repr(body[:700]))
        raise RuntimeError(f"Gunma TV timetable loaded, but no dated matchup with an explicit broadcast-start time could be parsed at {page.url}")
    for broadcast_date, match, airtime in parsed:
        add(rows, "群馬テレビ", broadcast_date, match, GUNMA_TV_URL, airtime)
        print("GUNMA TV ACCEPTED:", broadcast_date, airtime, match[0], "vs", match[1], "|", GUNMA_TV_URL)
    print("GUNMA TV PARSED ROWS:", len(parsed))


def _canonical_search_result_url(href):
    """Strip tracking query/fragment and trailing slash for safe source URL deduplication."""
    raw = str(href or "").strip()
    parsed = urllib.parse.urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunparse((parsed.scheme.casefold(), parsed.netloc.casefold(), path, "", "", ""))

def _unique_search_results(results, seen_urls, allow_unknown_time=False):
    """Deduplicate per verification policy so a relaxed pass is not lost after a strict pass."""
    unique = []
    policy = bool(allow_unknown_time)
    for result in results:
        if len(result) < 3:
            continue
        canonical = _canonical_search_result_url(result[1])
        key = (canonical, policy)
        if not canonical or key in seen_urls:
            continue
        seen_urls.add(key)
        unique.append(result)
    return unique

def scrape_social_and_regional(page, rows):
    """Daily discovery across team X/Instagram and regional TV sources.
    Search results are candidates only. A row is accepted only after opening its
    source URL and confirming station, broadcast date, both teams and TV context.
    The time remains blank unless the source explicitly labels a broadcast start."""
    team_items = []
    seen_team = set()
    for canonical in sorted(SEARCH_TEAM_ALIASES):
        team_items.append((canonical, SEARCH_TEAM_ALIASES[canonical]))
        seen_team.add(canonical)
    for canonical in TEAM_NAMES:
        if canonical not in seen_team:
            team_items.append((canonical, [canonical]))

    seen = set()
    seen_result_urls = set()
    candidate_count = 0
    verified_count = 0
    accepted = 0
    search_failures = 0
    search_unavailable = False

    def process_results(results, allow_unknown_time=False):
        nonlocal candidate_count, verified_count, accepted
        for title, href, snippet in _unique_search_results(results, seen_result_urls, allow_unknown_time):
            candidate_count += 1
            item = _verify_search_result(page, title, href, snippet, require_time=False)
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

    def search_and_process(query, error_label, allow_unknown_time=False):
        nonlocal search_failures, search_unavailable
        # Bing retries once inside _bing_results. If it is unavailable, do not
        # spend the rest of the run repeating hundreds of identical failed calls.
        if search_unavailable:
            return
        try:
            process_results(_bing_results(page, query), allow_unknown_time=allow_unknown_time)
        except Exception as e:
            search_failures += 1
            search_unavailable = True
            print(error_label, query, e)
            print("SOCIAL/REGIONAL DISCOVERY ABORTED: search engine unavailable after retry; remaining searches skipped.")
            flag_source_discovery_degraded(f"Search engine unavailable; remaining social/regional searches skipped: {error_label} {query}")

    # The league account is a first-priority source. Search it explicitly on every
    # run in addition to the team and regional searches below; a result is only
    # accepted after the source itself confirms a dated, named TV broadcast.
    search_and_process(
        'site:x.com/SVLEAGUE_JP ("放送" OR "テレビ" OR "中継" OR "BS10" OR "GAORA" OR "J SPORTS" OR "フジテレビ" OR "今週の対戦カード")',
        "OFFICIAL SV.LEAGUE X SEARCH ERROR:",
        allow_unknown_time=True,
    )

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


KNOWN_VERIFIED_AIRTIME_SOURCES = {
    ("J SPORTS 2", "2026-10-17", "NECレッドロケッツ川崎", "ヴィクトリーナ姫路"):
        "https://www.jsports.co.jp/volleyball/svleague/golden_live/",
    ("J SPORTS 1", "2026-10-18", "NECレッドロケッツ川崎", "ヴィクトリーナ姫路"):
        "https://www.jsports.co.jp/volleyball/svleague/golden_live/",
    ("J SPORTS 2", "2026-10-24", "ウルフドッグス名古屋", "東京グレートベアーズ"):
        "https://www.jsports.co.jp/volleyball/svleague_men/",
    ("J SPORTS 2", "2026-10-25", "ウルフドッグス名古屋", "東京グレートベアーズ"):
        "https://www.jsports.co.jp/volleyball/svleague_men/",
    ("J SPORTS 4", "2026-10-31", "フラーゴラッド鹿児島", "北海道イエロースターズ"):
        "https://www.jsports.co.jp/volleyball/svleague/golden_live/",
}


def normalize_time_semantics(row):
    """Migrate legacy rows so only verified programme-start times remain in broadcast_time."""
    identity = (row.station, row.broadcast_date, row.home, row.away)
    source = row.source or ""
    source_lower = source.casefold()

    if (
        row.station == "群馬テレビ"
        and row.broadcast_date == "2026-10-24"
        and row.home == "群馬グリーンウイングス"
        and row.away == "アランマーレ秋田庄内"
        and "x.com/vbm_link/status/2113610880101568860" in source
        and row.broadcast_time == "13:00"
        and not row.match_start_time
    ):
        return Broadcast(row.station, row.broadcast_date, row.home, row.away,
                         row.source, row.broadcast_time, "13:05")

    if row.match_start_time or not row.broadcast_time:
        return row
    if "svleague.jp/news/detail/100609" in source_lower:
        return Broadcast(row.station, row.broadcast_date, row.home, row.away,
                         row.source, "", row.broadcast_time)
    if source == "known-official-fixture":
        verified_source = KNOWN_VERIFIED_AIRTIME_SOURCES.get(identity)
        if verified_source:
            return Broadcast(row.station, row.broadcast_date, row.home, row.away,
                             verified_source, row.broadcast_time, "")
        return Broadcast(row.station, row.broadcast_date, row.home, row.away,
                         row.source, "", row.broadcast_time)
    return row


def known_facts():
    # Authoritative facts from SV.LEAGUE official announcements and broadcaster schedules.
    # An official SV.LEAGUE broadcast announcement is sufficient proof a broadcast exists;
    # broadcaster-side listings are supplemental only.
    src = "known-official-fixture"
    facts = [
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
        # J SPORTS confirms Game 1 also receives a free BS television broadcast,
        # but the channel name/time is not stated in the announcement. Keep it as
        # a separate TV-only row instead of guessing the channel or dropping it.
        Broadcast("BS無料放送（局名未公表）","2026-10-17","NECレッドロケッツ川崎","ヴィクトリーナ姫路","https://www.jsports.co.jp/press_release/page/365/",""),
        Broadcast("J SPORTS 1","2026-10-18","NECレッドロケッツ川崎","ヴィクトリーナ姫路",src,"15:15"),
        Broadcast("J SPORTS 2","2026-10-24","ウルフドッグス名古屋","東京グレートベアーズ",src,"16:25"),
        Broadcast("J SPORTS 2","2026-10-25","ウルフドッグス名古屋","東京グレートベアーズ",src,"15:25"),
        Broadcast("J SPORTS 4","2026-10-31","フラーゴラッド鹿児島","北海道イエロースターズ",src,"13:45"),
        Broadcast("BS無料放送（局名未公表）","2026-10-31","フラーゴラッド鹿児島","北海道イエロースターズ","https://www.jsports.co.jp/press_release/page/365/",""),
        # The SV.LEAGUE article marks these additional Game 1 cards as GOLDEN LIVE;
        # J SPORTS confirms that Game 1 of every GOLDEN LIVE card receives a free
        # BS TV broadcast. Channel and BS broadcast time are not yet specified.
        Broadcast("BS無料放送（局名未公表）","2026-11-07","ウルフドッグス名古屋","ジェイテクトSTINGS愛知","https://www.jsports.co.jp/press_release/page/365/ | https://www.svleague.jp/news/detail/100609/?grade=sv",""),
        Broadcast("BS無料放送（局名未公表）","2026-11-21","PFUブルーキャッツ石川かほく","埼玉上尾メディックス","https://www.jsports.co.jp/press_release/page/365/ | https://www.svleague.jp/news/detail/100609/?grade=sv",""),
        Broadcast("BS無料放送（局名未公表）","2026-12-19","東京グレートベアーズ","サントリーサンバーズ大阪","https://www.jsports.co.jp/press_release/page/365/ | https://www.svleague.jp/news/detail/100609/?grade=sv",""),
        Broadcast("J SPORTS 2","2026-11-01","フラーゴラッド鹿児島","北海道イエロースターズ",src,"13:05"),
        # Official SV.LEAGUE article 100609 is authoritative: these broadcasts are real
        # even when a broadcaster has not yet published its own schedule. Keep them
        # as durable facts; do not gate them on third-party confirmation.
        Broadcast("BS10", "2026-11-07", "ウルフドッグス名古屋", "ジェイテクトSTINGS愛知", "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:35"),
        Broadcast("BS10", "2026-11-14", "SAGA久光スプリングス", "PFUブルーキャッツ石川かほく", "https://www.svleague.jp/news/detail/100609/?grade=sv", "13:05"),
        Broadcast("GAORA SPORTS", "2026-11-26", "日本製鉄堺ブレイザーズ", "東京グレートベアーズ", "https://www.svleague.jp/news/detail/100609/?grade=sv", "18:35"),
        Broadcast("GAORA SPORTS", "2026-11-27", "日本製鉄堺ブレイザーズ", "東京グレートベアーズ", "https://www.svleague.jp/news/detail/100609/?grade=sv", "18:35"),
        Broadcast("BS10", "2026-11-28", "NECレッドロケッツ川崎", "PFUブルーキャッツ石川かほく", "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:05"),
        Broadcast("GAORA SPORTS", "2026-12-19", "東レアローズ滋賀", "PFUブルーキャッツ石川かほく", "https://www.svleague.jp/news/detail/100609/?grade=sv", "13:05"),
        Broadcast("GAORA SPORTS", "2026-12-20", "東レアローズ滋賀", "PFUブルーキャッツ石川かほく", "https://www.svleague.jp/news/detail/100609/?grade=sv", "13:05"),
        Broadcast("GAORA SPORTS", "2026-12-26", "東レアローズ滋賀", "SAGA久光スプリングス", "https://www.svleague.jp/news/detail/100609/?grade=sv", "13:05"),
        Broadcast("GAORA SPORTS", "2026-12-27", "東レアローズ滋賀", "SAGA久光スプリングス", "https://www.svleague.jp/news/detail/100609/?grade=sv", "13:05"),
        Broadcast("GAORA SPORTS", "2027-01-02", "大阪マーヴェラス", "ヴィクトリーナ姫路", "https://www.svleague.jp/news/detail/100609/?grade=sv", "12:05"),
        Broadcast("GAORA SPORTS", "2027-01-03", "大阪マーヴェラス", "ヴィクトリーナ姫路", "https://www.svleague.jp/news/detail/100609/?grade=sv", "12:05"),
        Broadcast("GAORA SPORTS", "2027-01-16", "東レアローズ滋賀", "ヴィクトリーナ姫路", "https://www.svleague.jp/news/detail/100609/?grade=sv", "13:05"),
        Broadcast("GAORA SPORTS", "2027-01-17", "東レアローズ滋賀", "ヴィクトリーナ姫路", "https://www.svleague.jp/news/detail/100609/?grade=sv", "13:05"),
        Broadcast("GAORA SPORTS", "2027-01-23", "ヴィクトリーナ姫路", "アランマーレ秋田庄内", "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:05"),
        Broadcast("GAORA SPORTS", "2027-01-24", "ヴィクトリーナ姫路", "アランマーレ秋田庄内", "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:05"),
        # VolleyballKing article confirms the tvk broadcast; the TV guide confirms its date.
        Broadcast("テレビ神奈川","2026-10-17","NECレッドロケッツ川崎","ヴィクトリーナ姫路","known-volleyballking-tvk","18:30"),
        # Official Gunma TV timetable gives 13:00 airing; Volleyball Magazine X fixture graphic gives the 13:05 match start (2026-10-24).
        Broadcast("群馬テレビ", "2026-10-24", "群馬グリーンウイングス", "アランマーレ秋田庄内", "https://www.gtv.co.jp/timetable/ | https://x.com/vbm_link/status/2113610880101568860", "13:00"),
        # Preserve the two previously confirmed Sun TV listings even if regional search is unavailable.
        Broadcast("サンテレビジョン", "2026-10-24", "ヴィクトリーナ姫路", "PFUブルーキャッツ石川かほく", "previously-confirmed-user-shared-tv-listing", "12:00"),
        Broadcast("サンテレビジョン", "2026-10-25", "ヴィクトリーナ姫路", "PFUブルーキャッツ石川かほく", "previously-confirmed-user-shared-tv-listing", "12:00"),
        # GTV announced that all 18 Gunma home matches will be televised. Until each
        # broadcast slot is announced, keep a visible placeholder on the match date.
        Broadcast("群馬テレビ", "2026-10-25", "群馬グリーンウイングス", "アランマーレ秋田庄内", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2026-11-21", "群馬グリーンウイングス", "アリーザ愛知", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2026-11-22", "群馬グリーンウイングス", "アリーザ愛知", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2026-12-05", "群馬グリーンウイングス", "SAGA久光スプリングス", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2026-12-06", "群馬グリーンウイングス", "SAGA久光スプリングス", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2026-12-26", "群馬グリーンウイングス", "NECレッドロケッツ川崎", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2026-12-27", "群馬グリーンウイングス", "NECレッドロケッツ川崎", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2027-01-23", "群馬グリーンウイングス", "ＫＵＲＯＢＥアクアフェアリーズ富山", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2027-01-24", "群馬グリーンウイングス", "ＫＵＲＯＢＥアクアフェアリーズ富山", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2027-02-06", "群馬グリーンウイングス", "PFUブルーキャッツ石川かほく", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2027-02-07", "群馬グリーンウイングス", "PFUブルーキャッツ石川かほく", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2027-02-20", "群馬グリーンウイングス", "Astemoリヴァーレ茨城", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2027-02-21", "群馬グリーンウイングス", "Astemoリヴァーレ茨城", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2027-02-27", "群馬グリーンウイングス", "埼玉上尾メディックス", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2027-02-28", "群馬グリーンウイングス", "埼玉上尾メディックス", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2027-03-20", "群馬グリーンウイングス", "デンソーエアリービーズ", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        Broadcast("群馬テレビ", "2027-03-21", "群馬グリーンウイングス", "デンソーエアリービーズ", "provisional-gunma-tv-home-broadcast;match-date-placeholder;https://www.gtv.co.jp/timetable/;https://gunmagreenwings.jp/games/", ""),
        # GTV weekly grid lists a 19:00 replay of this matchup, but the text view does not reliably associate it with a date; do not invent one.
        # Durable fallback for every remaining explicit TV entry in official announcement 100609.
        Broadcast("J SPORTS 3", "2026-11-28", "ＫＵＲＯＢＥアクアフェアリーズ富山", "Astemoリヴァーレ茨城", "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:05"),
        Broadcast("J SPORTS 3", "2026-11-29", "ＫＵＲＯＢＥアクアフェアリーズ富山", "Astemoリヴァーレ茨城", "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:05"),
        Broadcast("フジテレビTWO", "2026-12-05", "大阪ブルテオン", "ジェイテクトSTINGS愛知", "https://www.svleague.jp/news/detail/100609/?grade=sv", "18:05"),
        Broadcast("フジテレビNEXT", "2026-12-06", "大阪ブルテオン", "ジェイテクトSTINGS愛知", "https://www.svleague.jp/news/detail/100609/?grade=sv", "15:05"),
        Broadcast("フジテレビNEXT", "2026-12-26", "東京グレートベアーズ", "大阪ブルテオン", "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:05"),
        Broadcast("フジテレビNEXT", "2026-12-27", "東京グレートベアーズ", "大阪ブルテオン", "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:05"),
        Broadcast("フジテレビNEXT", "2027-01-16", "サントリーサンバーズ大阪", "大阪ブルテオン", "https://www.svleague.jp/news/detail/100609/?grade=sv", "13:05"),
        Broadcast("フジテレビNEXT", "2027-01-17", "サントリーサンバーズ大阪", "大阪ブルテオン", "https://www.svleague.jp/news/detail/100609/?grade=sv", "13:05"),
        Broadcast("フジテレビNEXT", "2027-02-27", "ジェイテクトSTINGS愛知", "大阪ブルテオン", "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:05"),
        Broadcast("フジテレビNEXT", "2027-02-28", "ジェイテクトSTINGS愛知", "大阪ブルテオン", "https://www.svleague.jp/news/detail/100609/?grade=sv", "14:05"),
    ]
    return [normalize_time_semantics(r) for r in facts]

def reconcile(rows):
    """Merge sources by broadcast identity while keeping airing and match times separate."""
    banned = {
        ("フジテレビNEXT","2026-09-18","PFUブルーキャッツ石川かほく","SAGA久光スプリングス"),
        ("NHK BS","2026-09-18","PFUブルーキャッツ石川かほく","SAGA久光スプリングス"),
        ("GAORA SPORTS","2026-09-18","試合社会貢献・普及コラムメディアすべてJSPORTSバレーボールキング2026","2"),
        ("GAORA SPORTS","2026-10-31","東レアローズ滋賀","デンソーエアリービーズ"),
        ("フジテレビNEXT","2026-10-30","東レアローズ滋賀","デンソーエアリービーズ"),
    }
    out = {}

    def identity(row):
        return (row.station, row.broadcast_date, row.home, row.away)

    def is_replay(row):
        source = (row.source or "").casefold()
        return any(tag in source for tag in ("replay", "録画", "再放送", "recorded"))

    def source_priority(row):
        source = (row.source or "").casefold()
        if "program_guide/channel" in source or "gtv.co.jp/timetable" in source:
            return 7
        if any(domain in source for domain in ("jsports.co.jp", "gaora.co.jp", "myjcom.jp")):
            return 6
        if any(token in source for token in ("known-volleyballking-tvk", "previously-confirmed-user-shared-tv-listing")):
            return 5
        if "svleague.jp" in source:
            return 4
        if "x.com" in source or "instagram.com" in source:
            return 3
        if "provisional" in source:
            return 0
        if "known-official-fixture" in source:
            return 1
        return 2

    def upsert(raw_row):
        row = normalize_time_semantics(raw_row)
        key4 = identity(row)
        if key4 in banned:
            return
        related = [(key, value) for key, value in out.items() if key[:4] == key4]
        known_match_start = row.match_start_time or next(
            (value.match_start_time for _, value in related if value.match_start_time), ""
        )

        if not row.broadcast_time:
            timed = [(key, value) for key, value in related if value.broadcast_time]
            if timed:
                for key, value in timed:
                    if known_match_start and not value.match_start_time:
                        out[key] = Broadcast(value.station, value.broadcast_date, value.home, value.away,
                                             value.source, value.broadcast_time, known_match_start)
                return
            key = key4 + ("",)
            existing = out.get(key)
            if existing:
                best = row if source_priority(row) > source_priority(existing) else existing
                match_start = existing.match_start_time or row.match_start_time
                out[key] = Broadcast(best.station, best.broadcast_date, best.home, best.away,
                                     best.source, "", match_start)
            else:
                out[key] = Broadcast(row.station, row.broadcast_date, row.home, row.away,
                                     row.source, "", known_match_start)
            return

        blank_key = key4 + ("",)
        blank = out.pop(blank_key, None)
        if blank and not known_match_start:
            known_match_start = blank.match_start_time

        same_key = key4 + (row.broadcast_time,)
        existing_same = out.get(same_key)
        if existing_same:
            best = row if source_priority(row) > source_priority(existing_same) else existing_same
            match_start = existing_same.match_start_time or row.match_start_time or known_match_start
            out[same_key] = Broadcast(best.station, best.broadcast_date, best.home, best.away,
                                      best.source, row.broadcast_time, match_start)
            return

        conflicts = [
            (key, value) for key, value in out.items()
            if key[:4] == key4 and value.broadcast_time and value.broadcast_time != row.broadcast_time
        ]
        if conflicts and not is_replay(row) and not any(is_replay(value) for _, value in conflicts):
            best_key, best_row = max(conflicts, key=lambda item: source_priority(item[1]))
            if source_priority(row) <= source_priority(best_row):
                if known_match_start and not best_row.match_start_time:
                    out[best_key] = Broadcast(best_row.station, best_row.broadcast_date, best_row.home,
                                              best_row.away, best_row.source, best_row.broadcast_time,
                                              known_match_start)
                return
            for key, _ in conflicts:
                del out[key]

        out[same_key] = Broadcast(row.station, row.broadcast_date, row.home, row.away,
                                  row.source, row.broadcast_time, known_match_start)

    for record in load_previous() + list(rows) + known_facts():
        upsert(record)

    channel_rows = [
        row for row in out.values()
        if row.station in {"J SPORTS 1", "J SPORTS 2", "J SPORTS 3", "J SPORTS 4"}
    ]
    for key, row in list(out.items()):
        if row.station != "J SPORTS（チャンネル未公表）":
            continue
        if any(
            other.broadcast_date == row.broadcast_date
            and other.home == row.home and other.away == row.away
            and other.broadcast_time == row.broadcast_time
            for other in channel_rows
        ):
            del out[key]

    return sorted(out.values(), key=lambda row: (
        row.broadcast_date, row.broadcast_time or row.match_start_time,
        row.station, row.home, row.away
    ))


# Required coverage from the official 2026-27 broadcast announcement.
# Identity keys omit time/source so text changes do not hide missing records.
REQUIRED_100609 = {
    ("BS10", "2026-11-07", "ウルフドッグス名古屋", "ジェイテクトSTINGS愛知"),
    ("BS10", "2026-11-14", "SAGA久光スプリングス", "PFUブルーキャッツ石川かほく"),
    ("GAORA SPORTS", "2026-11-26", "日本製鉄堺ブレイザーズ", "東京グレートベアーズ"),
    ("GAORA SPORTS", "2026-11-27", "日本製鉄堺ブレイザーズ", "東京グレートベアーズ"),
    ("BS10", "2026-11-28", "NECレッドロケッツ川崎", "PFUブルーキャッツ石川かほく"),
    ("GAORA SPORTS", "2026-12-19", "東レアローズ滋賀", "PFUブルーキャッツ石川かほく"),
    ("GAORA SPORTS", "2026-12-20", "東レアローズ滋賀", "PFUブルーキャッツ石川かほく"),
    ("GAORA SPORTS", "2026-12-26", "東レアローズ滋賀", "SAGA久光スプリングス"),
    ("GAORA SPORTS", "2026-12-27", "東レアローズ滋賀", "SAGA久光スプリングス"),
    ("GAORA SPORTS", "2027-01-02", "大阪マーヴェラス", "ヴィクトリーナ姫路"),
    ("GAORA SPORTS", "2027-01-03", "大阪マーヴェラス", "ヴィクトリーナ姫路"),
    ("GAORA SPORTS", "2027-01-16", "東レアローズ滋賀", "ヴィクトリーナ姫路"),
    ("GAORA SPORTS", "2027-01-17", "東レアローズ滋賀", "ヴィクトリーナ姫路"),
    ("GAORA SPORTS", "2027-01-23", "ヴィクトリーナ姫路", "アランマーレ秋田庄内"),
    ("GAORA SPORTS", "2027-01-24", "ヴィクトリーナ姫路", "アランマーレ秋田庄内"),
}

# Remaining entries from the same official article: full-coverage gate.
REQUIRED_100609 |= {
    ("NHK BS", "2026-10-23", "デンソーエアリービーズ", "SAGA久光スプリングス"),
    ("NHK BS", "2026-11-01", "大阪ブルテオン", "ウルフドッグス名古屋"),
    ("フジテレビNEXT", "2026-10-24", "北海道イエロースターズ", "大阪ブルテオン"),
    ("フジテレビNEXT", "2026-10-25", "北海道イエロースターズ", "大阪ブルテオン"),
    ("フジテレビNEXT", "2026-10-31", "大阪ブルテオン", "ウルフドッグス名古屋"),
    ("フジテレビNEXT", "2026-11-01", "大阪ブルテオン", "ウルフドッグス名古屋"),
    ("フジテレビTWO", "2026-12-05", "大阪ブルテオン", "ジェイテクトSTINGS愛知"),
    ("フジテレビNEXT", "2026-12-06", "大阪ブルテオン", "ジェイテクトSTINGS愛知"),
    ("フジテレビNEXT", "2026-12-26", "東京グレートベアーズ", "大阪ブルテオン"),
    ("フジテレビNEXT", "2026-12-27", "東京グレートベアーズ", "大阪ブルテオン"),
    ("フジテレビNEXT", "2027-01-16", "サントリーサンバーズ大阪", "大阪ブルテオン"),
    ("フジテレビNEXT", "2027-01-17", "サントリーサンバーズ大阪", "大阪ブルテオン"),
    ("フジテレビNEXT", "2027-02-27", "ジェイテクトSTINGS愛知", "大阪ブルテオン"),
    ("フジテレビNEXT", "2027-02-28", "ジェイテクトSTINGS愛知", "大阪ブルテオン"),
    ("GAORA SPORTS", "2026-10-17", "大阪マーヴェラス", "岡山シーガルズ"),
    ("GAORA SPORTS", "2026-10-18", "大阪マーヴェラス", "岡山シーガルズ"),
    ("GAORA SPORTS", "2026-10-24", "ヴィクトリーナ姫路", "PFUブルーキャッツ石川かほく"),
    ("GAORA SPORTS", "2026-10-25", "ヴィクトリーナ姫路", "PFUブルーキャッツ石川かほく"),
    ("GAORA SPORTS", "2026-11-01", "東レアローズ滋賀", "デンソーエアリービーズ"),
    ("GAORA SPORTS", "2026-11-07", "大阪マーヴェラス", "SAGA久光スプリングス"),
    ("GAORA SPORTS", "2026-11-08", "大阪マーヴェラス", "SAGA久光スプリングス"),
    ("GAORA SPORTS", "2026-11-14", "ヴィクトリーナ姫路", "東レアローズ滋賀"),
    ("J SPORTS 2", "2026-10-17", "NECレッドロケッツ川崎", "ヴィクトリーナ姫路"),
    ("J SPORTS 1", "2026-10-18", "NECレッドロケッツ川崎", "ヴィクトリーナ姫路"),
    ("J SPORTS 1", "2026-11-14", "SAGA久光スプリングス", "PFUブルーキャッツ石川かほく"),
    ("J SPORTS 2", "2026-11-15", "SAGA久光スプリングス", "PFUブルーキャッツ石川かほく"),
    ("J SPORTS 2", "2026-11-21", "PFUブルーキャッツ石川かほく", "埼玉上尾メディックス"),
    ("J SPORTS 2", "2026-11-22", "PFUブルーキャッツ石川かほく", "埼玉上尾メディックス"),
    ("J SPORTS 3", "2026-11-28", "ＫＵＲＯＢＥアクアフェアリーズ富山", "Astemoリヴァーレ茨城"),
    ("J SPORTS 3", "2026-11-29", "ＫＵＲＯＢＥアクアフェアリーズ富山", "Astemoリヴァーレ茨城"),
    ("J SPORTS 2", "2026-12-26", "大阪マーヴェラス", "アリーザ愛知"),
    ("J SPORTS 4", "2026-12-27", "大阪マーヴェラス", "アリーザ愛知"),
    ("J SPORTS 2", "2026-10-24", "ウルフドッグス名古屋", "東京グレートベアーズ"),
    ("J SPORTS 2", "2026-10-25", "ウルフドッグス名古屋", "東京グレートベアーズ"),
    ("J SPORTS 4", "2026-10-31", "フラーゴラッド鹿児島", "北海道イエロースターズ"),
    ("J SPORTS 2", "2026-11-01", "フラーゴラッド鹿児島", "北海道イエロースターズ"),
    ("J SPORTS 2", "2026-11-07", "ウルフドッグス名古屋", "ジェイテクトSTINGS愛知"),
    ("J SPORTS 2", "2026-11-08", "ウルフドッグス名古屋", "ジェイテクトSTINGS愛知"),
    ("J SPORTS 3", "2026-12-05", "広島サンダーズ", "サントリーサンバーズ大阪"),
    ("J SPORTS 2", "2026-12-06", "広島サンダーズ", "サントリーサンバーズ大阪"),
    ("J SPORTS 2", "2026-12-19", "東京グレートベアーズ", "サントリーサンバーズ大阪"),
    ("J SPORTS 2", "2026-12-20", "東京グレートベアーズ", "サントリーサンバーズ大阪"),
}

def validate(rows, official_ok):
    if not official_ok:
        return False, "SV.LEAGUE official source could not be safely fetched."
    if len(rows) < len(known_facts()):
        return False, f"Abnormally small result set: {len(rows)} rows."
    keys = [(r.station,r.broadcast_date,r.home,r.away,r.broadcast_time) for r in rows]
    if len(keys) != len(set(keys)):
        return False, "Duplicate keys detected."
    present = {(r.station,r.broadcast_date,r.home,r.away) for r in rows}
    missing_official = sorted(REQUIRED_100609 - present)
    if missing_official:
        return False, "Required 100609 official broadcast records missing: " + repr(missing_official)
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
        return [normalize_time_semantics(Broadcast(**x)) for x in json.loads(p.read_text(encoding="utf-8"))]
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
    # A missing optional team logo must not block publishing verified broadcast data.
    # The site renders the team name as text when no logo is available.
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
        w.writerow(["放送局","放送日","ホームチーム","アウェイチーム","放送開始","試合開始"])
        for r in rows:
            w.writerow([r.station, r.broadcast_date.replace("-","/"), r.home, r.away, r.broadcast_time, r.match_start_time])

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
.station-logo.fuji{background:#fff;padding:2px}.station-logo.fuji img{display:block;width:100%;height:100%;max-width:100%;max-height:100%;object-fit:contain;transform:none}.station-logo.fuji.next img{transform:none}.station-logo.fuji.next.fallback:after{content:"フジテレビ NEXT";display:flex;align-items:center;justify-content:center;width:100%;height:100%;font-size:10px;font-weight:900;line-height:1.1;text-align:center;color:#111}
.station-logo.nhk{background:#fff}.station-logo.nhk img{width:57px}.station-logo.regional{font-size:10px;font-weight:900;line-height:1.1;text-align:center;color:#111;overflow-wrap:anywhere;padding:4px}
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
 <p>放送開始時刻は放送局が明示した場合のみ表示。試合開始時刻とは別管理</p>
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
 <div class="footer"><strong>※ 放送日時・対戦カードは変更になる場合があります。</strong><br>「—」は放送開始時刻が未確認であることを示します。試合開始時刻を放送開始時刻として代用していません。最新情報は各放送局の公式サイトおよびSV.LEAGUE公式発表をご確認ください。__PROVISIONAL_NOTE__</div>
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
function rowKey(row){const t=row.querySelectorAll('.team');return [row.dataset.station,row.dataset.date||'',t[0]?.textContent.trim(),t[1]?.textContent.trim(),row.querySelector('.time')?.textContent.trim()].join('|')}
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
            return '<span class="station-logo fuji next"><img src="https://www2.myjcom.jp/special/common/channel_logo/fuji_tv_next.jpg" alt="フジテレビNEXT ライブ・プレミアム" loading="lazy" onerror="this.style.display=&quot;none&quot;;this.parentElement.classList.add(&quot;fallback&quot;)"></span>'
        if station == "フジテレビONE":
            return '<span class="station-logo fuji"><img src="https://www2.myjcom.jp/special/common/channel_logo/fuji_tv_one.jpg" alt="フジテレビONE スポーツ・バラエティ" loading="lazy"></span>'
        if station == "フジテレビTWO":
            return '<span class="station-logo fuji"><img src="https://www2.myjcom.jp/special/common/channel_logo/fuji_tv_two.jpg" alt="フジテレビTWO ドラマ・アニメ" loading="lazy"></span>'
        if station == "NHK BS":
            return '<span class="station-logo nhk"><img src="https://commons.wikimedia.org/wiki/Special:Redirect/file/NHK_BS_2023_logo.svg" alt="NHK BS" loading="lazy"></span>'
        return f'<span class="station-logo regional">{esc(station)}</span>'

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
            f'<div class="grid-head"><div>放送局</div><div>放送開始</div><div>ホームチーム</div><div>アウェイチーム</div><div>録画予約</div></div>'
            f'{"".join(body)}</div>'
        )

    html = html.replace("__ROWS__", "".join(day_blocks))
    html = html.replace("__DATES__", date_options)
    html = html.replace("__UPDATED__", datetime.now().strftime("%Y.%m.%d %H:%M"))
    provisional_note = ""
    if any("provisional-gunma-tv-home-broadcast" in r.source for r in rows):
        provisional_note = '<br><strong>※ 群馬テレビの「今季ホーム戦18試合を全て放送」発表に基づく仮登録があります。放送日時未発表の試合は試合日を仮置きし、放送枠が確認でき次第更新します。</strong><br><strong>※ 群馬テレビの週間番組表には19:00の録画中継も記載されていますが、放送日を確定できないため日付確定待ちです。</strong>'
    html = html.replace("__PROVISIONAL_NOTE__", provisional_note)
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
            flag_source_discovery_degraded(f"SV.LEAGUE official source failed: {e}")
        try:
            scrape_gaora(page, rows)
        except Exception as e:
            print("GAORA ERROR:", e)
            flag_source_discovery_degraded(f"GAORA source failed: {e}")
        try:
            scrape_jsports_golden_live(page, rows)
        except Exception as e:
            print("J SPORTS GOLDEN LIVE ERROR:", e)
            flag_source_discovery_degraded(f"J SPORTS GOLDEN LIVE source failed: {e}")
        try:
            scrape_jsports_official(page, rows)
        except Exception as e:
            print("J SPORTS ERROR:", e)
            flag_source_discovery_degraded(f"J SPORTS source failed: {e}")
        try:
            scrape_jcom(page, rows)
        except Exception as e:
            print("J:COM ERROR:", e)
            flag_source_discovery_degraded(f"J:COM source failed: {e}")
        try:
            scrape_volleyballking(page, rows)
        except Exception as e:
            print("VOLLEYBALLKING ERROR:", e)
            flag_source_discovery_degraded(f"VolleyballKing crawl failed: {e}")
        try:
            scrape_gunma_tv(page, rows)
        except Exception as e:
            print("GUNMA TV ERROR:", e)
            flag_source_discovery_degraded(f"Gunma TV timetable failed: {e}")
        try:
            scrape_social_and_regional(page, rows)
        except Exception as e:
            print("SOCIAL/REGIONAL ERROR:", e)
            flag_source_discovery_degraded(f"Social/regional discovery failed: {e}")
        try:
            team_logos = scrape_team_logos(page)
        except Exception as e:
            # Logos are cosmetic. Keep station/team text and publish the schedule
            # even when a logo endpoint fails or a team mark is unavailable.
            print("TEAM LOGO WARNING (non-blocking):", e)
            team_logos = {}
        browser.close()

    rows = reconcile(rows)
    try:
        validate_team_logos(team_logos, rows)
    except Exception as e:
        # Never let missing team logos prevent a confirmed broadcast from being added.
        print("TEAM LOGO VALIDATION WARNING (non-blocking):", e)
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
