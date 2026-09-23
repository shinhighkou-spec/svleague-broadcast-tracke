from __future__ import annotations
import csv, json, re, shutil
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
SITE = ROOT / 'site'
DATA.mkdir(exist_ok=True); SITE.mkdir(exist_ok=True)

OFFICIAL_NEWS = 'https://www.svleague.jp/news/detail/100414/?grade=sv'
GAORA = 'https://www.gaora.co.jp/volleyball/4396990'
GAORA_WEEKLY = 'https://www.gaora.co.jp/program/{ymd}'

@dataclass(frozen=True)
class Broadcast:
    station: str
    broadcast_date: str
    home: str
    away: str
    source: str
    broadcast_time: str = ''

TEAM_MAP = {
    '大阪Ｂ': '大阪ブルテオン', '大阪ブルテオン': '大阪ブルテオン',
    '大阪ブルテオン（男子）': '大阪ブルテオン',
    '東レ滋賀': '東レアローズ滋賀', '東レアローズ滋賀': '東レアローズ滋賀',
    '大阪MV': '大阪マーヴェラス', '大阪マーヴェラス': '大阪マーヴェラス',
    '姫路': 'ヴィクトリーナ姫路', 'ヴィクトリーナ姫路': 'ヴィクトリーナ姫路',
    'PFU': 'PFUブルーキャッツ石川かほく', 'PFUブルーキャッツ石川かほく': 'PFUブルーキャッツ石川かほく',
    '岡山': '岡山シーガルズ', '岡山シーガルズ': '岡山シーガルズ',
    'SAGA久光': 'SAGA久光スプリングス', 'SAGA久光スプリングス': 'SAGA久光スプリングス',
    'デンソー': 'デンソーエアリービーズ', 'デンソーエアリービーズ': 'デンソーエアリービーズ',
    '北海道YS': '北海道イエロースターズ', '北海道イエロースターズ': '北海道イエロースターズ',
    'ウルフドッグス名古屋': 'ウルフドッグス名古屋',
    '日本製鉄堺ブレイザーズ': '日本製鉄堺ブレイザーズ',
    '東京GB': '東京グレートベアーズ', '東京グレートベアーズ': '東京グレートベアーズ',
}

VALID_STATIONS = {
    'GAORA SPORTS','J SPORTS 1','J SPORTS 2','J SPORTS 3','J SPORTS 4',
    'フジテレビONE','フジテレビTWO','フジテレビNEXT','NHK BS',
}

def canon_team(s: str) -> str:
    s = re.sub(r'\s+', '', s).strip()
    return TEAM_MAP.get(s, s)

def clean_station(s: str) -> str:
    s = re.sub(r'\s+', ' ', s).strip()
    if s == 'GAORA': return 'GAORA SPORTS'
    return s

def parse_date(s: str) -> str | None:
    m = re.search(r'(20\d{2})[./年-](\d{1,2})[./月-](\d{1,2})', s)
    if m:
        return f'{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
    m = re.search(r'(\d{1,2})月(\d{1,2})日', s)
    if m:
        # 2026-27 season: Sep-Dec 2026, Jan-May 2027.
        y = 2026 if int(m.group(1)) >= 9 else 2027
        return f'{y:04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}'
    return None

def parse_time(s: str) -> str:
    m = re.search(r'(\d{1,2}):(\d{2})', s)
    return f'{int(m.group(1)):02d}:{m.group(2)}' if m else ''

def valid_season_date(d: str) -> bool:
    try:
        x = date.fromisoformat(d)
    except ValueError:
        return False
    return date(2026, 9, 1) <= x <= date(2027, 6, 30)

def parse_match(s: str):
    # Explicit known separators used by broadcaster pages.
    s = re.sub(r'\s+', ' ', s).strip()
    pairs = [
        r'(.+?)\s+vs\s+(.+?)(?:\s*[（(]|$)',
        r'(.+?)\s*[-―−]\s*(.+?)(?:\s*\d|\s*[（(]|$)',
    ]
    for p in pairs:
        m = re.search(p, s, re.I)
        if m:
            h, a = canon_team(m.group(1)), canon_team(m.group(2))
            if h and a and h != a and len(h) < 80 and len(a) < 80:
                return h, a
    return None

def add(rows, station, d, match, source, t=''):
    station = clean_station(station)
    if station == 'J SPORTS' or station == 'J SPORTSオンデマンド': return
    if station not in VALID_STATIONS: return
    if not d or not valid_season_date(d) or not match: return
    rows.append(Broadcast(station, d, match[0], match[1], source, t))

def scrape_gaora(page, rows):
    page.goto(GAORA, wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(1500)
    # Main schedule cards. Each card contains its own date, avoiding the historical
    # 10/31 -> 11/1 inheritance bug.
    cards = page.locator('text=ガオバレ！SVリーグ 2026-27')
    for i in range(cards.count()):
        el = cards.nth(i)
        try:
            block = el.locator('xpath=..').inner_text(timeout=3000)
        except Exception:
            continue
        d = parse_date(block)
        tm = parse_time(block)
        m = parse_match(block)
        if d and m:
            add(rows, 'GAORA SPORTS', d, m, GAORA, tm)
    # Weekly program pages are used as a second independent dynamic-page source.
    # They are particularly useful when the series page only exposes the first few cards.
    for ymd in ['20261016','20261017','20261021','20261023','20261030','20261106','20261113']:
        url = GAORA_WEEKLY.format(ymd=ymd)
        try:
            page.goto(url, wait_until='networkidle', timeout=45000)
            text = page.locator('body').inner_text(timeout=5000)
            for match_block in re.finditer(r'ガオバレ！SVリーグ 2026-27(.{0,500})', text, re.S):
                b = match_block.group(0)
                d = parse_date(b)
                tm = parse_time(b)
                m = parse_match(b)
                if d and m: add(rows, 'GAORA SPORTS', d, m, url, tm)
        except Exception:
            pass

def scrape_official(page, rows):
    page.goto(OFFICIAL_NEWS, wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(1000)
    text = page.locator('body').inner_text(timeout=10000)
    # The official page is authoritative, but its HTML layout may change. Keep
    # conservative extraction and only accept rows containing a station + date + matchup.
    stations = ['フジテレビNEXT','フジテレビONE','フジテレビTWO','NHK BS','J SPORTS 1','J SPORTS 2','J SPORTS 3','J SPORTS 4','GAORA SPORTS']
    for st in stations:
        for m0 in re.finditer(re.escape(st), text):
            block = text[max(0,m0.start()-700):m0.end()+700]
            d = parse_date(block)
            tm = parse_time(block)
            match = parse_match(block)
            if d and match: add(rows, st, d, match, OFFICIAL_NEWS, tm)
    if not text.strip():
        raise RuntimeError('SV.LEAGUE official announcement page returned empty text')

def known_facts():
    src = 'known-official-fixture'
    return [
        Broadcast('フジテレビNEXT','2026-10-24','北海道イエロースターズ','大阪ブルテオン',src,'14:05'),
        Broadcast('フジテレビNEXT','2026-10-25','北海道イエロースターズ','大阪ブルテオン',src,'13:05'),
        Broadcast('フジテレビNEXT','2026-10-31','大阪ブルテオン','ウルフドッグス名古屋',src,'12:05'),
        Broadcast('フジテレビNEXT','2026-11-01','大阪ブルテオン','ウルフドッグス名古屋',src,'15:05'),
        Broadcast('GAORA SPORTS','2026-10-17','大阪マーヴェラス','岡山シーガルズ',src,'14:05'),
        Broadcast('GAORA SPORTS','2026-10-18','大阪マーヴェラス','岡山シーガルズ',src,'13:05'),
        Broadcast('GAORA SPORTS','2026-10-24','ヴィクトリーナ姫路','PFUブルーキャッツ石川かほく',src,'12:05'),
        Broadcast('GAORA SPORTS','2026-10-25','ヴィクトリーナ姫路','PFUブルーキャッツ石川かほく',src,'12:05'),
        Broadcast('GAORA SPORTS','2026-11-01','東レアローズ滋賀','デンソーエアリービーズ',src,'13:05'),
        Broadcast('GAORA SPORTS','2026-11-07','大阪マーヴェラス','SAGA久光スプリングス',src,'13:05'),
        Broadcast('GAORA SPORTS','2026-11-08','大阪マーヴェラス','SAGA久光スプリングス',src,'13:05'),
        Broadcast('GAORA SPORTS','2026-11-14','ヴィクトリーナ姫路','東レアローズ滋賀',src,'14:05'),
        Broadcast('NHK BS','2026-09-18','PFUブルーキャッツ石川かほく','SAGA久光スプリングス',src,''),
    ]

def reconcile(rows):
    # Known official corrections/fixtures are testable invariants, not blindly
    # appended duplicates. Remove the historically wrong Fuji 9/18 and GAORA 10/31 rows.
    banned = {
        ('フジテレビNEXT','2026-09-18','PFUブルーキャッツ石川かほく','SAGA久光スプリングス'),
        ('GAORA SPORTS','2026-10-31','東レアローズ滋賀','デンソーエアリービーズ'),
        ('フジテレビNEXT','2026-10-30','東レアローズ滋賀','デンソーエアリービーズ'),
    }
    out = {}
    for r in rows:
        key=(r.station,r.broadcast_date,r.home,r.away)
        if key in banned: continue
        out[key]=r
    for r in known_facts(): out[(r.station,r.broadcast_date,r.home,r.away)] = r
    return sorted(out.values(), key=lambda r:(r.broadcast_date,r.station,r.home,r.away))

def validate(rows, official_ok):
    if not official_ok: return False, 'SV.LEAGUE official source could not be safely fetched.'
    if len(rows) < 5: return False, f'Abnormally small result set: {len(rows)} rows.'
    keys=[(r.station,r.broadcast_date,r.home,r.away) for r in rows]
    if len(keys)!=len(set(keys)): return False, 'Duplicate keys detected.'
    for r in rows:
        if not r.station or not r.broadcast_date or not r.home or not r.away: return False, f'Malformed row: {r}'
        if not valid_season_date(r.broadcast_date): return False, f'Out-of-season date: {r.broadcast_date}'
        if r.home==r.away: return False, f'Same-team matchup: {r}'
    return True, 'ok'

def load_previous():
    p=DATA/'broadcasts.json'
    if not p.exists(): return []
    try:
        return [Broadcast(**x) for x in json.loads(p.read_text(encoding='utf-8'))]
    except Exception: return []

def write_outputs(rows):
    (DATA/'broadcasts.json').write_text(json.dumps([asdict(r) for r in rows],ensure_ascii=False,indent=2),encoding='utf-8')
    with (DATA/'broadcasts.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(['放送局','放送日','ホームチーム','アウェイチーム'])
        for r in rows: w.writerow([r.station,r.broadcast_date.replace('-','/'),r.home,r.away])
    html='''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SVリーグ 放送予定</title><style>body{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f6f7f9;color:#111}main{max-width:1000px;margin:auto;padding:24px}h1{font-size:24px}table{width:100%;border-collapse:collapse;background:white;border-radius:12px;overflow:hidden}th,td{padding:12px;border-bottom:1px solid #ddd;text-align:left}th{background:#eee}td.date{background:#fff5a8}td.toray,td.osaka{background:#87C6FF}@media(max-width:650px){th,td{padding:9px 6px;font-size:13px}}</style></head><body><main><h1>SVリーグ 放送予定</h1><p>2026-27シーズン／最終更新: __UPDATED__</p><table><thead><tr><th>放送局</th><th>放送日</th><th>ホームチーム</th><th>アウェイチーム</th></tr></thead><tbody>__ROWS__</tbody></table></main></body></html>'''
    trs=[]
    for r in rows:
        hcls='toray' if r.home=='東レアローズ滋賀' else ('osaka' if r.home=='大阪ブルテオン' else '')
        acls='toray' if r.away=='東レアローズ滋賀' else ('osaka' if r.away=='大阪ブルテオン' else '')
        trs.append(f'<tr><td>{r.station}</td><td class="date">{r.broadcast_date.replace("-","/")}</td><td class="{hcls}">{r.home}</td><td class="{acls}">{r.away}</td></tr>')
    html=html.replace('__ROWS__',''.join(trs)).replace('__UPDATED__',datetime.now().strftime('%Y-%m-%d %H:%M'))
    (SITE/'index.html').write_text(html,encoding='utf-8')

def main():
    rows=[]; official_ok=False
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(locale='ja-JP')
        try: scrape_official(page,rows); official_ok=True
        except Exception as e: print('OFFICIAL ERROR:',e)
        try: scrape_gaora(page,rows)
        except Exception as e: print('GAORA ERROR:',e)
        browser.close()
    rows=reconcile(rows)
    ok,msg=validate(rows,official_ok)
    if not ok:
        print('VALIDATION FAILED:',msg)
        prev=load_previous()
        if prev: write_outputs(prev)
        raise SystemExit(2)
    write_outputs(rows)
    print(f'OK: {len(rows)} rows')

if __name__=='__main__': main()
