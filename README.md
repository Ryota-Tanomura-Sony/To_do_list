# Eisenhower Matrix ToDo App

Panel（Python）製のローカルWebアプリ。アイゼンハワーマトリクスでタスクを管理します。

## 機能

- **Eisenhower Matrix** — Do / Schedule / Delegate / Eliminate の4象限でタスクを整理
- **7日グリッドカレンダー** — 月間カレンダー表示（前月/次月ナビ、今日ハイライト、期限超過赤表示）
- **タグ管理** — 複数タグ選択・絞り込み・Tag別タスク数グラフ
- **完了一覧** — 完了タスクのアーカイブ（↩で未完了に戻せる）
- **HTMLログイン認証** — Basic Auth によるパスワード保護
- **常時稼働** — Windowsログイン時に自動起動、watchdogによる自動復旧

## 起動方法

### 手動起動
```
main\start_server.bat をダブルクリック
```
→ ブラウザで **http://localhost:5006** を開く

### Windows起動時の自動起動
スタートアップフォルダに登録済み。次回ログインから自動起動します。

| ショートカット | 役割 |
|---|---|
| `ToDoApp_Panel.lnk` | Panel サーバー起動 |
| `ToDoWatchdog.lnk` | 死活監視・自動再起動（5分周期） |

## ログイン情報

| 項目 | 値 |
|---|---|
| URL | http://localhost:5006 |
| ユーザー名 | `admin` |
| パスワード | `password` |

パスワードは `main/credentials.json` を直接編集して変更できます（変更後はサーバー再起動）。

```json
{"ユーザー名": "パスワード"}
```

## ファイル構成

```
main/
├── To_do.py               # アプリ本体
├── action_items.py        # アクションアイテム管理
├── gen_schedule.py        # スケジュールPPTX生成
├── schedule_gui.py        # スケジュールGUI
├── start_server.bat       # サーバー起動スクリプト
├── watchdog.bat           # 死活監視・自動再起動
├── setup_taskscheduler.ps1# タスクスケジューラ登録（参考）
├── credentials.json       # ログイン情報（gitignore済み）
├── credentials.json.example # ログイン情報テンプレート
├── todo_list.csv          # タスクデータ（gitignore済み）
├── activity_log.csv       # 操作ログ（gitignore済み）
└── tests/
    └── test_todo.py       # ユニットテスト
```

## 開発・テスト

```bash
# テスト実行
cd main
python -m pytest tests/ -v
```

## 依存パッケージ

- Python 3.12+
- panel >= 1.8
- pandas
- bokeh
- param
