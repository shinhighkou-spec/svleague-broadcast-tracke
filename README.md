# SV.LEAGUE 放送予定 自動収集

SV.LEAGUE 2026-27シーズンのテレビ放送予定をPlaywrightで取得し、
検証後にGitHub Pagesへ公開するプロジェクトです。

## 表示

- 放送局
- 放送日
- ホームチーム
- アウェイチーム

放送時間は内部検証に使用しますが、公開表には表示しません。

## 自動更新

GitHub Actionsで毎日、日本時間06:00ごろに実行します。
公式取得や検証に失敗した場合は、直前の正常データを保持します。

## GitHub Pages

リポジトリの **Settings → Pages → Source = GitHub Actions** にしてください。

## ローカル実行

```bash
pip install -r requirements.txt
playwright install chromium
pytest -q
python scraper.py
```
