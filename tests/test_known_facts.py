import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from scraper import known_facts, reconcile, validate

def test_known_official_facts_present():
    rows = reconcile([])
    keys={(r.station,r.broadcast_date,r.home,r.away) for r in rows}
    assert ('フジテレビNEXT','2026-10-24','北海道イエロースターズ','大阪ブルテオン') in keys
    assert ('フジテレビNEXT','2026-10-25','北海道イエロースターズ','大阪ブルテオン') in keys
    assert ('フジテレビNEXT','2026-10-31','大阪ブルテオン','ウルフドッグス名古屋') in keys
    assert ('フジテレビNEXT','2026-11-01','大阪ブルテオン','ウルフドッグス名古屋') in keys
    assert ('GAORA SPORTS','2026-11-01','東レアローズ滋賀','デンソーエアリービーズ') in keys
    assert ('NHK BS','2026-10-23','デンソーエアリービーズ','SAGA久光スプリングス') in keys
    assert ('NHK BS','2026-11-01','大阪ブルテオン','ウルフドッグス名古屋') in keys

def test_known_bad_rows_rejected():
    rows=reconcile([
      known_facts()[0].__class__('フジテレビNEXT','2026-09-18','PFUブルーキャッツ石川かほく','SAGA久光スプリングス','x',''),
      known_facts()[0].__class__('GAORA SPORTS','2026-10-31','東レアローズ滋賀','デンソーエアリービーズ','x',''),
    ])
    keys={(r.station,r.broadcast_date,r.home,r.away) for r in rows}
    assert ('フジテレビNEXT','2026-09-18','PFUブルーキャッツ石川かほく','SAGA久光スプリングス') not in keys
    assert ('GAORA SPORTS','2026-10-31','東レアローズ滋賀','デンソーエアリービーズ') not in keys
