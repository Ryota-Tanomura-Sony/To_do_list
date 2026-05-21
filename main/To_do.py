# To_do.py
# -*- coding: utf-8 -*-
"""Eisenhower Matrix ToDo — Panel Web App (v2.0)

改修内容:
- 7日グリッドカレンダー（月表示 + 前月/次月ナビゲーション）
- リッチHTMLタスクカード（象限カラー、タグバッジ、ホバーエフェクト）
- 安定動作: ログローテーション、例外吸収、GC制御
"""
from __future__ import annotations

import calendar
import datetime as dt
import gc
import os
import re
import tempfile
from html import escape as html_escape
from pathlib import Path
from typing import Any, Iterable, Optional, cast

import pandas as pd
import panel as pn
import param
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure

# =========================
# Panel 初期化
# =========================
pn.extension("notifications", sizing_mode="stretch_width")

# =========================
# 設定
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "todo_list.csv"
LOG_FILE = BASE_DIR / "activity_log.csv"
ENCODING = "utf-8-sig"
LOG_MAX_ROWS = 5000  # ログローテーション上限

WDAYS = ["月", "火", "水", "木", "金", "土", "日"]

QUADRANTS = [
    "Do (緊急かつ重要)",
    "Schedule (重要だが緊急でない)",
    "Delegate (緊急だが重要でない)",
    "Eliminate (重要でも緊急でもない)",
]

QUADRANT_COLORS = {
    "Do (緊急かつ重要)": ("#ff4d4f", "#fff1f0"),
    "Schedule (重要だが緊急でない)": ("#1890ff", "#e6f7ff"),
    "Delegate (緊急だが重要でない)": ("#fa8c16", "#fff7e6"),
    "Eliminate (重要でも緊急でもない)": ("#8c8c8c", "#f5f5f5"),
}

TAGS = [
    "資料作成",
    "Rev案件",
    "特許提案",
    "simWG対応",
    "Option Mask対応",
    "TCAD内部対応",
    "研修対応",
    "連絡待ち",
    "社内会議",
]

COLUMNS = ["id", "title", "quadrant", "deadline", "tags", "completed"]

# =========================
# カスタムCSS
# =========================
CUSTOM_CSS = """
<style>
.task-card {
    border-radius: 8px;
    padding: 10px 14px;
    margin: 4px 0;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    cursor: default;
    border-left: 5px solid #ddd;
}
.task-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}
.task-card.overdue {
    border-left-color: #ff4d4f !important;
    background: #fff1f0 !important;
}
.task-card .tag-badge {
    display: inline-block;
    background: #e8e8e8;
    color: #555;
    border-radius: 10px;
    padding: 1px 8px;
    font-size: 0.75em;
    margin-right: 4px;
    margin-top: 4px;
}
.task-card .deadline-text {
    font-size: 0.85em;
    color: #666;
}
.task-card .deadline-text.overdue {
    color: #ff4d4f;
    font-weight: bold;
}
.task-card .title-text {
    font-weight: 600;
    font-size: 0.95em;
    margin-bottom: 4px;
}
.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
}
.cal-header {
    text-align: center;
    font-weight: bold;
    padding: 6px 0;
    background: #f0f0f0;
    border-radius: 4px;
    font-size: 0.85em;
}
.cal-cell {
    min-height: 80px;
    border: 1px solid #e8e8e8;
    border-radius: 6px;
    padding: 4px;
    font-size: 0.8em;
    overflow-y: auto;
    max-height: 140px;
    background: #fafafa;
    transition: background 0.2s;
}
.cal-cell:hover {
    background: #f0f5ff;
}
.cal-cell.today {
    background: #e6f7ff;
    border: 2px solid #1890ff;
}
.cal-cell.other-month {
    opacity: 0.4;
}
.cal-day-num {
    font-weight: bold;
    font-size: 1.05em;
    margin-bottom: 2px;
}
.cal-task {
    background: #fff;
    border-radius: 4px;
    padding: 2px 4px;
    margin: 2px 0;
    border-left: 3px solid #1890ff;
    font-size: 0.85em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.cal-task.overdue {
    border-left-color: #ff4d4f;
    color: #ff4d4f;
}
.quadrant-badge {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 4px;
}
.archive-card {
    opacity: 0.7;
    text-decoration: line-through;
}
.nav-btn {
    cursor: pointer;
    user-select: none;
    font-size: 1.2em;
}
</style>
"""

# =========================
# ユーティリティ
# =========================


def _notify(kind: str, msg: str) -> None:
    """Panel notifications wrapper (None安全 + 例外吸収)."""
    notif = pn.state.notifications
    if notif is None:
        return
    try:
        fn = getattr(notif, kind, None)
        if callable(fn):
            fn(msg)
    except Exception:
        pass


_TRUE_SET = {"true", "1", "yes", "y", "on"}
_FALSE_SET = {"false", "0", "no", "n", "off", ""}


def _parse_bool(v: Any) -> bool:
    """CSV由来の bool 文字列を安全に bool 化."""
    if isinstance(v, bool):
        return v
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return False
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        try:
            return bool(int(v))
        except Exception:
            return False
    s = str(v).strip().lower()
    if s in _TRUE_SET:
        return True
    if s in _FALSE_SET:
        return False
    return False


def _normalize_tags(tag_str: str) -> list[str]:
    """'A,B' や 'A / B' を ['A','B'] に正規化."""
    if not tag_str:
        return []
    raw = re.split(r"[,/，、]\s*|\s+/\s+", str(tag_str))
    tags = [t.strip() for t in raw if t and t.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def _tags_to_str(tags: Iterable[str]) -> str:
    """CSV保存用に 'A,B' 形式へ."""
    cleaned = [t.strip() for t in tags if t and t.strip()]
    return ",".join(cleaned)


def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    """列不足を補い、型を正規化して返す（壊れたCSVも吸収）."""
    for c in COLUMNS:
        if c not in df.columns:
            if c == "completed":
                df[c] = False
            elif c == "quadrant":
                df[c] = QUADRANTS[1]
            else:
                df[c] = ""

    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype("int64")
    df["title"] = df["title"].astype(str)

    df["quadrant"] = df["quadrant"].astype(str)
    df.loc[~df["quadrant"].isin(QUADRANTS), "quadrant"] = QUADRANTS[1]

    df["deadline"] = pd.to_datetime(df["deadline"], errors="coerce").dt.date
    df["completed"] = df["completed"].map(_parse_bool).astype(bool)
    df["tags"] = df["tags"].fillna("").astype(str)

    return df[COLUMNS].copy()


def _atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    """一時ファイル経由で原子的にCSV保存."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Optional[str] = None
    tmp_fd: Optional[int] = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=path.stem + "_", suffix=".tmp", dir=str(path.parent)
        )
        os.close(tmp_fd)
        df.to_csv(tmp_path, index=False, encoding=ENCODING)
        os.replace(tmp_path, path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _log_action(action: str, task_id: int, title: str) -> None:
    """操作ログを activity_log.csv に追記（ローテーション付き）."""
    now = dt.datetime.now()
    row = pd.DataFrame(
        [
            {
                "timestamp": now.isoformat(timespec="seconds"),
                "date": now.date().isoformat(),
                "action": action,
                "id": int(task_id),
                "title": str(title),
            }
        ]
    )
    try:
        if LOG_FILE.exists():
            old = pd.read_csv(LOG_FILE, encoding=ENCODING)
            out = pd.concat([old, row], ignore_index=True)
        else:
            out = row
        # ログローテーション: 上限超過時は古い行を削除
        if len(out) > LOG_MAX_ROWS:
            out = out.tail(LOG_MAX_ROWS).reset_index(drop=True)
        _atomic_write_csv(out, LOG_FILE)
    except Exception:
        pass


def create_sample_csv() -> pd.DataFrame:
    """初回起動用のサンプルCSV生成."""
    today = dt.date.today()
    now_ms = int(dt.datetime.now().timestamp() * 1000)
    df = pd.DataFrame(
        [
            {
                "id": now_ms,
                "title": "TCAD条件整理",
                "quadrant": QUADRANTS[0],
                "deadline": today + dt.timedelta(days=1),
                "tags": "TCAD内部対応",
                "completed": False,
            },
            {
                "id": now_ms + 1,
                "title": "レビュー資料作成",
                "quadrant": QUADRANTS[1],
                "deadline": today + dt.timedelta(days=7),
                "tags": "社内会議",
                "completed": False,
            },
        ]
    )
    df = ensure_schema(df)
    _atomic_write_csv(df, DATA_FILE)
    return df


def load_data() -> pd.DataFrame:
    """CSV読み込み。壊れていたらサンプルで復旧."""
    if not DATA_FILE.exists():
        return create_sample_csv()
    try:
        df = pd.read_csv(DATA_FILE, encoding=ENCODING)
        df = ensure_schema(df)
        _atomic_write_csv(df, DATA_FILE)
        return df
    except Exception:
        return create_sample_csv()


def save_data(df: pd.DataFrame) -> None:
    df = ensure_schema(df)
    _atomic_write_csv(df, DATA_FILE)


# =========================
# カレンダーユーティリティ
# =========================


def get_month_grid(year: int, month: int) -> list[list[Optional[dt.date]]]:
    """月のカレンダーグリッドを生成（月曜始まり、6週固定）."""
    cal = calendar.Calendar(firstweekday=0)  # 月曜始まり
    weeks: list[list[Optional[dt.date]]] = []
    for week in cal.monthdatescalendar(year, month):
        weeks.append(week)
    # 最大6週まで（表示安定化）
    while len(weeks) < 6:
        last_day = weeks[-1][-1]
        next_week = [last_day + dt.timedelta(days=i + 1) for i in range(7)]
        weeks.append(next_week)
    return weeks[:6]


# =========================
# アプリ本体
# =========================
class TodoApp(param.Parameterized):
    cal_year = param.Integer(default=dt.date.today().year)
    cal_month = param.Integer(default=dt.date.today().month)

    def __init__(self, **params: Any):
        super().__init__(**params)

        self.df = load_data()

        # ---------- 入力（UI） ----------
        self.title_input = pn.widgets.TextInput(
            name="タスク名", placeholder="例: レビュー資料作成",
            styles={"font-size": "14px"},
        )
        self.quadrant_input = pn.widgets.Select(
            name="象限", options=QUADRANTS, value=QUADRANTS[1],
        )
        self.deadline_input = pn.widgets.DatePicker(name="期限", value=dt.date.today())

        self.tags_select = pn.widgets.MultiSelect(
            name="タグ（複数可）",
            options=TAGS,
            value=[],
            size=min(8, max(5, len(TAGS))),
        )

        self.add_button = pn.widgets.Button(
            name="＋ タスク追加", button_type="primary",
            styles={"font-weight": "bold", "font-size": "14px"},
        )

        self.filter_tag = pn.widgets.Select(
            name="🔍 タグで絞り込み",
            options=["すべて"] + TAGS,
            value="すべて",
        )

        # ② Tag別タスク数（未完了）棒グラフ
        self._tag_count_source = ColumnDataSource(data=dict(tag=[], count=[]))
        self._tag_bar_fig = figure(
            title="Tag別タスク数（未完了）",
            x_range=[],
            height=220,
            toolbar_location=None,
            tools="",
        )
        self._tag_bar_fig.vbar(
            x="tag", top="count", source=self._tag_count_source,
            width=0.8, color="#3b82f6", line_color="#2563eb",
        )
        self._tag_bar_fig.y_range.start = 0
        self._tag_bar_fig.xgrid.grid_line_color = None
        self._tag_bar_fig.yaxis.axis_label = "件数"
        self._tag_bar_fig.xaxis.major_label_orientation = 0.85

        self.tag_bar_pane = pn.pane.Bokeh(self._tag_bar_fig, sizing_mode="stretch_width")

        # ---------- 表示（Matrix / Calendar / Archive） ----------
        self.matrix_view = pn.GridSpec(nrows=2, ncols=2, min_height=620, mode="override")

        self._matrix_cells: list[pn.Column] = []
        for i, q in enumerate(QUADRANTS):
            color, bg = QUADRANT_COLORS.get(q, ("#999", "#f9f9f9"))
            styles = {
                "background": bg,
                "border-left": f"6px solid {color}",
                "padding": "12px",
                "border-radius": "10px",
                "box-shadow": "0 2px 8px rgba(0,0,0,0.06)",
            }
            cell = pn.Column(
                pn.pane.Markdown(f"### {q}"),
                scroll=True,
                sizing_mode="stretch_both",
                styles=styles,
            )
            self._matrix_cells.append(cell)
            self.matrix_view[i // 2, i % 2] = cell

        # カレンダービュー（HTML描画）
        self._cal_nav_prev = pn.widgets.Button(name="◀ 前月", width=90, button_type="light")
        self._cal_nav_next = pn.widgets.Button(name="次月 ▶", width=90, button_type="light")
        self._cal_title = pn.pane.Markdown("", styles={"font-size": "1.2em", "font-weight": "bold"})
        self._cal_html = pn.pane.HTML("", sizing_mode="stretch_width")

        self._cal_nav_prev.on_click(self._cal_prev)
        self._cal_nav_next.on_click(self._cal_next)

        self.calendar_view = pn.Column(
            pn.Row(
                self._cal_nav_prev,
                self._cal_title,
                self._cal_nav_next,
                align="center",
            ),
            self._cal_html,
            scroll=True,
            sizing_mode="stretch_both",
        )

        self.archive_view = pn.Column(scroll=True, sizing_mode="stretch_both")

        self.tabs = pn.Tabs(
            ("マトリクス", self.matrix_view),
            ("カレンダー", self.calendar_view),
            ("完了一覧", self.archive_view),
            sizing_mode="stretch_both",
        )

        # ---------- イベント ----------
        self.add_button.on_click(self.add_task)
        self.filter_tag.param.watch(lambda _e: self.refresh_ui(), "value")

        self.refresh_ui()

    # =====================
    # カレンダーナビゲーション
    # =====================
    def _cal_prev(self, _event: Any) -> None:
        if self.cal_month == 1:
            self.cal_month = 12
            self.cal_year -= 1
        else:
            self.cal_month -= 1
        self._update_calendar()

    def _cal_next(self, _event: Any) -> None:
        if self.cal_month == 12:
            self.cal_month = 1
            self.cal_year += 1
        else:
            self.cal_month += 1
        self._update_calendar()

    # =====================
    # 操作
    # =====================
    def add_task(self, _event: Any) -> None:
        title = (self.title_input.value or "").strip()
        if not title:
            _notify("error", "タスク名を入力してください")
            return

        try:
            now_ms = int(dt.datetime.now().timestamp() * 1000)
            selected_tags = list(self.tags_select.value or [])
            tags_str = _tags_to_str(selected_tags)

            new = pd.DataFrame(
                [
                    {
                        "id": now_ms,
                        "title": title,
                        "quadrant": self.quadrant_input.value,
                        "deadline": self.deadline_input.value,
                        "tags": tags_str,
                        "completed": False,
                    }
                ]
            )
            self.df = pd.concat([self.df, new], ignore_index=True)
            save_data(self.df)
            _log_action("add", now_ms, title)

            self.title_input.value = ""
            self.tags_select.value = []

            self.refresh_ui()
            _notify("success", "タスクを追加しました")
        except Exception as e:
            _notify("error", f"追加に失敗しました: {e!s}")

    def toggle_complete(self, task_id: int) -> None:
        """完了フラグをトグル."""
        try:
            mask = self.df["id"] == int(task_id)
            if not mask.any():
                _notify("error", "対象タスクが見つかりません")
                return

            current = bool(self.df.loc[mask, "completed"].iloc[0])
            self.df.loc[mask, "completed"] = (not current)
            save_data(self.df)

            title = str(self.df.loc[mask, "title"].iloc[0])
            _log_action("complete" if not current else "reopen", task_id, title)

            self.refresh_ui()
            _notify("success", "更新しました")
        except Exception as e:
            _notify("error", f"更新に失敗しました: {e!s}")

    def delete_task(self, task_id: int) -> None:
        """タスク削除."""
        try:
            mask = self.df["id"] == int(task_id)
            if not mask.any():
                _notify("error", "対象タスクが見つかりません")
                return
            title = str(self.df.loc[mask, "title"].iloc[0])

            self.df = self.df.loc[~mask].copy()
            save_data(self.df)
            _log_action("delete", task_id, title)

            self.refresh_ui()
            _notify("success", "削除しました")
        except Exception as e:
            _notify("error", f"削除に失敗しました: {e!s}")

    # =====================
    # HTMLタスクカード生成
    # =====================
    def _task_card_html(self, r: pd.Series, compact: bool = False) -> str:
        """リッチHTMLタスクカード."""
        deadline = r["deadline"]
        completed = bool(r["completed"])
        title = html_escape(str(r["title"]))
        quadrant = str(r["quadrant"])
        tags = _normalize_tags(str(r["tags"]))

        color, _ = QUADRANT_COLORS.get(quadrant, ("#999", "#f9f9f9"))
        is_overdue = False

        if pd.isna(deadline) or deadline is None:
            date_html = '<span class="deadline-text">期限未設定</span>'
        else:
            deadline = cast(dt.date, deadline)
            wday = WDAYS[deadline.weekday()]
            date_html = f'<span class="deadline-text">{deadline.strftime("%m/%d")} ({wday})</span>'
            is_overdue = (deadline < dt.date.today()) and (not completed)
            if is_overdue:
                date_html = f'<span class="deadline-text overdue">⚠ {deadline.strftime("%m/%d")} ({wday})</span>'

        overdue_cls = " overdue" if is_overdue else ""
        archive_cls = " archive-card" if completed else ""

        tags_html = "".join(f'<span class="tag-badge">{html_escape(t)}</span>' for t in tags)

        if compact:
            return (
                f'<div class="task-card{overdue_cls}{archive_cls}" '
                f'style="border-left-color:{color};padding:6px 8px;">'
                f'<span class="title-text">{title}</span>'
                f'</div>'
            )

        return (
            f'<div class="task-card{overdue_cls}{archive_cls}" '
            f'style="border-left-color:{color};background:#fff;">'
            f'<div class="title-text">'
            f'<span class="quadrant-badge" style="background:{color};"></span>'
            f'{title}</div>'
            f'<div>{date_html} {tags_html}</div>'
            f'</div>'
        )

    def _match_tag_filter(self, tag_str: str) -> bool:
        """現在のフィルタ条件に合うか."""
        if self.filter_tag.value == "すべて":
            return True
        tags = set(_normalize_tags(tag_str))
        return self.filter_tag.value in tags

    def get_task_row(self, r: pd.Series) -> pn.Row:
        """タスク行（ボタン + HTMLカード）."""
        completed = bool(r["completed"])

        btn_done = pn.widgets.Button(
            name="✔" if not completed else "↩",
            width=38, height=38,
            button_type="success" if not completed else "warning",
        )
        btn_done.on_click(lambda _e, tid=int(r["id"]): self.toggle_complete(tid))

        btn_del = pn.widgets.Button(name="🗑", width=38, height=38, button_type="danger")
        btn_del.on_click(lambda _e, tid=int(r["id"]): self.delete_task(tid))

        card_html = self._task_card_html(r)

        return pn.Row(
            btn_done,
            btn_del,
            pn.pane.HTML(card_html, sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
        )

    # =====================
    # カレンダー表示（7日グリッド）
    # =====================
    def _update_calendar(self) -> None:
        """月間7日グリッドカレンダーをHTML生成（インラインスタイルで確実に7列表示）."""
        today = dt.date.today()
        year, month = self.cal_year, self.cal_month
        self._cal_title.object = f"**{year}年 {month}月**"

        weeks = get_month_grid(year, month)
        active = self.df[~self.df["completed"]].copy()

        # 日付→タスクリストのマッピング
        task_by_date: dict[dt.date, list[pd.Series]] = {}
        for _, r in active.iterrows():
            d = r["deadline"]
            if d is not None and not pd.isna(d):
                d = cast(dt.date, d)
                task_by_date.setdefault(d, []).append(r)

        # ---- インラインスタイル定義 ----
        S_GRID    = "display:grid;grid-template-columns:repeat(7,1fr);gap:4px;width:100%;box-sizing:border-box;"
        S_HEADER  = "text-align:center;font-weight:bold;padding:6px 0;background:#f0f0f0;border-radius:4px;font-size:0.85em;"
        S_CELL    = "min-height:90px;border:1px solid #e8e8e8;border-radius:6px;padding:4px;font-size:0.8em;overflow-y:auto;max-height:150px;background:#fafafa;vertical-align:top;"
        S_CELL_TODAY   = "min-height:90px;border:2px solid #1890ff;border-radius:6px;padding:4px;font-size:0.8em;overflow-y:auto;max-height:150px;background:#e6f7ff;vertical-align:top;"
        S_CELL_OTHER   = "min-height:90px;border:1px solid #e8e8e8;border-radius:6px;padding:4px;font-size:0.8em;overflow-y:auto;max-height:150px;background:#fafafa;opacity:0.4;vertical-align:top;"
        S_DAYNUM  = "font-weight:bold;font-size:1.05em;margin-bottom:3px;color:#333;"
        S_DAYNUM_TODAY = "font-weight:bold;font-size:1.05em;margin-bottom:3px;color:#1890ff;"
        S_TASK    = "background:#fff;border-radius:3px;padding:2px 5px;margin:2px 0;border-left:3px solid #1890ff;font-size:0.82em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
        S_TASK_OD = "background:#fff1f0;border-radius:3px;padding:2px 5px;margin:2px 0;border-left:3px solid #ff4d4f;font-size:0.82em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#ff4d4f;"
        S_SAT     = "color:#1890ff;"
        S_SUN     = "color:#ff4d4f;"

        # ---- HTMLグリッド構築 ----
        html_parts = [f'<div style="{S_GRID}">']

        # ヘッダー行（月〜日）
        for i, day_name in enumerate(WDAYS):
            extra = ""
            if i == 5:   extra = "color:#1890ff;"
            elif i == 6: extra = "color:#ff4d4f;"
            html_parts.append(f'<div style="{S_HEADER}{extra}">{day_name}</div>')

        # 週行
        for week in weeks:
            for i, day in enumerate(week):
                is_today      = (day == today)
                is_other_month = (day.month != month)
                is_overdue_day = (day < today)

                if is_today:
                    cell_style = S_CELL_TODAY
                    num_style  = S_DAYNUM_TODAY
                elif is_other_month:
                    cell_style = S_CELL_OTHER
                    num_style  = S_DAYNUM
                else:
                    cell_style = S_CELL
                    num_style  = S_DAYNUM

                # 土日の数字色
                if i == 5:
                    num_style = S_DAYNUM + S_SAT
                elif i == 6:
                    num_style = S_DAYNUM + S_SUN

                tasks = task_by_date.get(day, [])
                tasks_html = ""
                for t in tasks[:4]:
                    t_title = html_escape(str(t["title"]))[:18]
                    q_color, _ = QUADRANT_COLORS.get(str(t["quadrant"]), ("#999", "#f9f9f9"))
                    if is_overdue_day:
                        tasks_html += f'<div style="{S_TASK_OD}">{t_title}</div>'
                    else:
                        tasks_html += f'<div style="{S_TASK}border-left-color:{q_color};">{t_title}</div>'
                if len(tasks) > 4:
                    tasks_html += f'<div style="font-size:0.72em;color:#999;text-align:right;">+{len(tasks)-4}件</div>'

                html_parts.append(
                    f'<div style="{cell_style}">'
                    f'<div style="{num_style}">{day.day}</div>'
                    f'{tasks_html}'
                    f'</div>'
                )

        html_parts.append('</div>')
        self._cal_html.object = "".join(html_parts)

    # =====================
    # グラフ更新（Tag別未完了数）
    # =====================
    def _update_tag_bar(self) -> None:
        """未完了タスクの tag 件数を集計し棒グラフを更新."""
        try:
            active = self.df[~self.df["completed"]].copy()
            all_tags: list[str] = []
            for t in active["tags"].fillna("").astype(str).tolist():
                all_tags.extend(_normalize_tags(t))

            if all_tags:
                s = pd.Series(all_tags)
                counts = s.value_counts()
            else:
                counts = pd.Series(dtype="int64")

            ordered = list(TAGS)
            for extra in counts.index.tolist():
                if extra not in ordered:
                    ordered.append(extra)

            tags = ordered
            vals = [int(counts.get(t, 0)) for t in tags]

            self._tag_count_source.data = {"tag": tags, "count": vals}
            self._tag_bar_fig.x_range.factors = tags
        except Exception:
            pass

    # =====================
    # 再描画
    # =====================
    def refresh_ui(self) -> None:
        try:
            self.df = ensure_schema(self.df)
            self._update_tag_bar()

            active = self.df[~self.df["completed"]].copy()
            if self.filter_tag.value != "すべて":
                active = active[active["tags"].map(self._match_tag_filter)].copy()

            # ----- Matrix -----
            for i, q in enumerate(QUADRANTS):
                q_tasks = active[active["quadrant"] == q]
                count = len(q_tasks)
                rows = [self.get_task_row(r) for _, r in q_tasks.iterrows()]
                cell = self._matrix_cells[i]
                header = f"### {q} ({count})"
                cell.objects = [pn.pane.Markdown(header), *rows]

            # ----- Calendar -----
            self._update_calendar()

            # ----- Archive -----
            done_df = self.df[self.df["completed"]].copy()
            archive_rows = [self.get_task_row(r) for _, r in done_df.iterrows()]
            self.archive_view.objects = [
                pn.pane.Markdown("## 完了済み（↩で戻せます）"),
                *archive_rows,
            ]

            # 定期的にGC実行（長時間稼働時のメモリ管理）
            gc.collect(generation=0)
        except Exception as e:
            _notify("error", f"UI更新エラー: {e!s}")


# =========================
# 起動
# =========================
app = TodoApp()

template = pn.template.FastListTemplate(
    title="📋 Eisenhower Matrix ToDo",
    sidebar=[
        pn.pane.HTML(CUSTOM_CSS),
        "## ＋ 新規タスク",
        app.title_input,
        app.quadrant_input,
        app.deadline_input,
        app.tags_select,
        app.add_button,
        pn.layout.Divider(),
        app.filter_tag,
        pn.layout.Divider(),
        "## 📊 Tag別タスク数",
        app.tag_bar_pane,
    ],
    main=[pn.pane.HTML(CUSTOM_CSS), app.tabs],
    accent_base_color="#1890ff",
    header_background="#001529",
)

template.servable()