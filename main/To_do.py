# To_do.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime as dt
import os
import re
import tempfile
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

# カスタムCSS（モダンデザイン - raw_cssで安全に注入）
_CUSTOM_CSS = """
.bk-btn-success { background: #10b981 !important; border: none !important; border-radius: 8px !important; color: #fff !important; }
.bk-btn-danger  { background: #ef4444 !important; border: none !important; border-radius: 8px !important; color: #fff !important; }
.bk-btn-warning { background: #f59e0b !important; border: none !important; border-radius: 8px !important; color: #fff !important; }
.bk-btn-primary { background: #6366f1 !important; border: none !important; border-radius: 8px !important; color: #fff !important; }
.bk-btn-light   { background: #f1f5f9 !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; }
"""
pn.config.raw_css.append(_CUSTOM_CSS)

# =========================
# 設定
# =========================
BASE_DIR = Path(__file__).resolve().parent
# データファイルはホームディレクトリ固定（worktree切替・再起動でもデータが消えない）
_DATA_DIR = Path.home() / "Documents" / "ToDoAppData"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = _DATA_DIR / "todo_list.csv"
LOG_FILE = _DATA_DIR / "activity_log.csv"
ENCODING = "utf-8-sig"

WDAYS = ["月", "火", "水", "木", "金", "土", "日"]

QUADRANTS = [
    "Do (緊急かつ重要)",
    "Schedule (重要だが緊急でない)",
    "Delegate (緊急だが重要でない)",
    "Eliminate (重要でも緊急でもない)",
]

# タグ候補
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


_MD_ESCAPE_RE = re.compile(r"([\\`*_{}\[\]()#+\-.!|>])")


def _escape_md(text: str) -> str:
    """最低限の Markdown エスケープ（レイアウト崩れ対策）."""
    return _MD_ESCAPE_RE.sub(r"\\\1", text)


def _normalize_tags(tag_str: str) -> list[str]:
    """'A,B' や 'A / B' を ['A','B'] に正規化."""
    if not tag_str:
        return []
    raw = re.split(r"[,/，、]\s*|\s+/\s+", str(tag_str))
    tags = [t.strip() for t in raw if t and t.strip()]
    # 重複除去（順序維持）
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
    """一時ファイル経由で原子的にCSV保存（途中で壊れない）."""
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
    """操作ログを activity_log.csv に追記（表示はしないが残す）."""
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
# アプリ本体
# =========================
class TodoApp(param.Parameterized):
    def __init__(self, **params: Any):
        super().__init__(**params)

        self.df = load_data()

        # ---------- 入力（UI） ----------
        self.title_input = pn.widgets.TextInput(name="タスク名", placeholder="例: レビュー資料作成")
        self.quadrant_input = pn.widgets.Select(name="象限", options=QUADRANTS, value=QUADRANTS[1])
        self.deadline_input = pn.widgets.DatePicker(name="期限", value=dt.date.today())

        # ① タグ：スクロールで候補から選べる（MultiSelect + size） [1](https://panel.holoviz.org/reference/widgets/MultiSelect.html)
        #    複数タグ選択も可能（CSVには "A,B" で保存）
        self.tags_select = pn.widgets.MultiSelect(
            name="タグ（複数可）",
            options=TAGS,
            value=[],
            size=min(10, max(6, len(TAGS))),  # 候補が多いとスクロール
        )

        self.add_button = pn.widgets.Button(name="追加", button_type="primary")

        # ---------- 編集フォーム ----------
        self._editing_id: Optional[int] = None

        self.edit_title_input = pn.widgets.TextInput(name="タスク名（編集）")
        self.edit_quadrant_input = pn.widgets.Select(name="象限（編集）", options=QUADRANTS, value=QUADRANTS[1])
        self.edit_deadline_input = pn.widgets.DatePicker(name="期限（編集）", value=dt.date.today())
        self.edit_tags_select = pn.widgets.MultiSelect(
            name="タグ（編集・複数可）",
            options=TAGS,
            value=[],
            size=min(10, max(6, len(TAGS))),
        )
        self.edit_save_button = pn.widgets.Button(name="💾 保存", button_type="success")
        self.edit_cancel_button = pn.widgets.Button(name="キャンセル", button_type="default")

        self.edit_form = pn.Column(
            pn.pane.Markdown("## ✏️ タスク編集"),
            self.edit_title_input,
            self.edit_quadrant_input,
            self.edit_deadline_input,
            self.edit_tags_select,
            pn.Row(self.edit_save_button, self.edit_cancel_button),
            pn.layout.Divider(),
            visible=False,
            styles={"background": "linear-gradient(135deg, #fefce8, #fef9c3)",
                    "padding": "12px", "border-radius": "12px",
                    "border": "1px solid #fde047",
                    "box-shadow": "0 2px 8px rgba(250,204,21,0.15)"},
        )

        self.filter_tag = pn.widgets.Select(
            name="タグで絞り込み",
            options=["すべて"] + TAGS,
            value="すべて",
        )

        # ② Tag別タスク数（未完了）棒グラフ：Bokeh Figure を Panel で表示 [2](https://panel.holoviz.org/reference/panes/Bokeh.html)
        self._tag_count_source = ColumnDataSource(data=dict(tag=[], count=[]))
        self._tag_bar_fig = figure(
            title="Tag別タスク数（未完了）",
            x_range=[],
            height=260,
            toolbar_location=None,
            tools="",
        )
        self._tag_bar_fig.vbar(x="tag", top="count", source=self._tag_count_source, width=0.75, color="#6366f1", alpha=0.85)
        self._tag_bar_fig.y_range.start = 0
        self._tag_bar_fig.xgrid.grid_line_color = None
        self._tag_bar_fig.ygrid.grid_line_dash = "dotted"
        self._tag_bar_fig.ygrid.grid_line_alpha = 0.4
        self._tag_bar_fig.yaxis.axis_label = "件数"
        self._tag_bar_fig.xaxis.major_label_orientation = 0.9
        self._tag_bar_fig.outline_line_color = None
        self._tag_bar_fig.border_fill_color = None
        self._tag_bar_fig.background_fill_color = None

        self.tag_bar_pane = pn.pane.Bokeh(self._tag_bar_fig, sizing_mode="stretch_width")  # [2](https://panel.holoviz.org/reference/panes/Bokeh.html)

        # ---------- 表示（Matrix / Calendar / Archive） ----------
        # GridSpec のセル再代入による overlap 警告を避けるため、セルは初回だけ配置し中身だけ更新する。 [3](https://panel.holoviz.org/reference/layouts/GridSpec.html)
        self.matrix_view = pn.GridSpec(nrows=2, ncols=2, min_height=620, mode="override")

        # ③ Matrix セル色分け（象限別）
        self._quadrant_styles = {
            QUADRANTS[0]: {"background": "#fff0f0", "border-left": "5px solid #ef4444"},
            QUADRANTS[1]: {"background": "#eff6ff", "border-left": "5px solid #6366f1"},
            QUADRANTS[2]: {"background": "#fffbeb", "border-left": "5px solid #f59e0b"},
            QUADRANTS[3]: {"background": "#f8fafc", "border-left": "5px solid #94a3b8"},
        }

        self._matrix_cells: list[pn.Column] = []
        for i, q in enumerate(QUADRANTS):
            styles = dict(self._quadrant_styles.get(q, {}))
            styles.update(
                {
                    "padding": "12px",
                    "border-radius": "12px",
                    "box-shadow": "0 2px 6px #0000000f",
                }
            )

            cell = pn.Column(
                pn.pane.Markdown(f"### {q}"),
                scroll=True,
                sizing_mode="stretch_both",
                styles=styles,
            )
            self._matrix_cells.append(cell)
            self.matrix_view[i // 2, i % 2] = cell  # 初回だけ

        self.calendar_view = pn.Column(scroll=True, sizing_mode="stretch_both")
        self.archive_view = pn.Column(scroll=True, sizing_mode="stretch_both")

        self.tabs = pn.Tabs(
            ("マトリクス", self.matrix_view),
            ("カレンダー", self.calendar_view),
            ("完了一覧", self.archive_view),
            sizing_mode="stretch_both",
        )

        # ---------- イベント ----------
        self.add_button.on_click(self.add_task)
        self.edit_save_button.on_click(self.save_edit)
        self.edit_cancel_button.on_click(self.cancel_edit)
        self.filter_tag.param.watch(lambda _e: self.refresh_ui(), "value")

        self.refresh_ui()

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

            # MultiSelect の value は list
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

            # 入力リセット
            self.title_input.value = ""
            self.tags_select.value = []

            self.refresh_ui()
            _notify("success", "タスクを追加しました")
        except Exception as e:
            _notify("error", f"追加に失敗しました: {e!s}")

    def start_edit(self, task_id: int) -> None:
        """編集フォームを指定タスクの値で開く."""
        mask = self.df["id"] == int(task_id)
        if not mask.any():
            _notify("error", "対象タスクが見つかりません")
            return
        row = self.df.loc[mask].iloc[0]
        self._editing_id = int(task_id)
        self.edit_title_input.value = str(row["title"])
        self.edit_quadrant_input.value = row["quadrant"] if row["quadrant"] in QUADRANTS else QUADRANTS[1]
        deadline = row["deadline"]
        self.edit_deadline_input.value = deadline if (deadline is not None and not pd.isna(deadline)) else dt.date.today()
        self.edit_tags_select.value = _normalize_tags(str(row["tags"]))
        self.edit_form.visible = True

    def save_edit(self, _event: Any) -> None:
        """編集内容をDataFrameに反映して保存."""
        if self._editing_id is None:
            return
        try:
            mask = self.df["id"] == int(self._editing_id)
            if not mask.any():
                _notify("error", "対象タスクが見つかりません")
                return
            title = self.edit_title_input.value.strip()
            if not title:
                _notify("error", "タスク名を入力してください")
                return
            self.df.loc[mask, "title"] = title
            self.df.loc[mask, "quadrant"] = self.edit_quadrant_input.value
            self.df.loc[mask, "deadline"] = self.edit_deadline_input.value
            self.df.loc[mask, "tags"] = _tags_to_str(self.edit_tags_select.value)
            save_data(self.df)
            _log_action("edit", self._editing_id, title)
            self._editing_id = None
            self.edit_form.visible = False
            self.refresh_ui()
            _notify("success", "タスクを更新しました")
        except Exception as e:
            _notify("error", f"更新に失敗しました: {e!s}")

    def cancel_edit(self, _event: Any) -> None:
        """編集フォームを閉じる."""
        self._editing_id = None
        self.edit_form.visible = False

    def toggle_complete(self, task_id: int) -> None:
        """完了フラグをトグル（完了→未完了も可能）."""
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
        """タスク削除（ハードデリート）."""
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
    # 表示部品
    # =====================
    def _match_tag_filter(self, tag_str: str) -> bool:
        """現在のフィルタ条件に合うか（複数タグ対応）."""
        if self.filter_tag.value == "すべて":
            return True
        tags = set(_normalize_tags(tag_str))
        return self.filter_tag.value in tags

    def get_task_row(self, r: pd.Series) -> pn.Row:
        deadline = r["deadline"]
        completed = bool(r["completed"])
        title = _escape_md(str(r["title"]))
        tags = _escape_md(str(r["tags"]))

        if pd.isna(deadline) or deadline is None:
            date_str = "期限未設定"
            is_overdue = False
        else:
            deadline = cast(dt.date, deadline)
            date_str = f"{deadline.strftime('%m/%d')} ({WDAYS[deadline.weekday()]})"
            is_overdue = (deadline < dt.date.today()) and (not completed)

        style = {"color": "#ef4444", "font-weight": "600"} if is_overdue else {"color": "#1e293b"}

        # タスクカードをHTMLで描画（css_classesとstyles混在を避ける）
        border_color = "#ef4444" if is_overdue else "#e2e8f0"
        title_color  = "#ef4444" if is_overdue else "#1e293b"
        card_html = (
            f'<div style="background:#ffffff;border:1px solid {border_color};'
            f'border-left:4px solid {border_color};border-radius:10px;'
            f'padding:8px 12px;margin:4px 0;">'
            f'<span style="font-weight:600;color:{title_color}">{title}</span><br>'
            f'<span style="color:#64748b;font-size:0.83em">📅 {date_str} &nbsp;│&nbsp; 🏷️ {tags}</span>'
            f'</div>'
        )

        btn_done = pn.widgets.Button(
            name="✔" if not completed else "↩",
            width=40,
            button_type="success" if not completed else "warning",
        )
        btn_done.on_click(lambda _e, tid=int(r["id"]): self.toggle_complete(tid))

        btn_edit = pn.widgets.Button(name="✏️", width=40, button_type="light")
        btn_edit.on_click(lambda _e, tid=int(r["id"]): self.start_edit(tid))

        btn_del = pn.widgets.Button(name="🗑", width=40, button_type="danger")
        btn_del.on_click(lambda _e, tid=int(r["id"]): self.delete_task(tid))

        return pn.Row(
            pn.Column(btn_done, btn_edit, btn_del, width=50),
            pn.pane.HTML(card_html, sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
        )

    # =====================
    # グラフ更新（Tag別未完了数）
    # =====================
    def _update_tag_bar(self) -> None:
        """未完了タスクの tag 件数を集計し棒グラフを更新."""
        try:
            active = self.df[~self.df["completed"]].copy()
            # tags を分解してカウント（複数タグ対応）
            all_tags: list[str] = []
            for t in active["tags"].fillna("").astype(str).tolist():
                all_tags.extend(_normalize_tags(t))

            if all_tags:
                s = pd.Series(all_tags)
                counts = s.value_counts()
            else:
                counts = pd.Series(dtype="int64")

            # 表示順：TAGSの順を優先し、未知タグは末尾
            ordered = list(TAGS)
            for extra in counts.index.tolist():
                if extra not in ordered:
                    ordered.append(extra)

            tags = ordered
            vals = [int(counts.get(t, 0)) for t in tags]

            self._tag_count_source.data = {"tag": tags, "count": vals}
            self._tag_bar_fig.x_range.factors = tags  # ここでカテゴリ更新
        except Exception:
            # グラフ更新失敗でもアプリは落とさない
            pass

    # =====================
    # 再描画
    # =====================
    def refresh_ui(self) -> None:
        self.df = ensure_schema(self.df)

        # グラフは「未完了全体」の集計として更新（フィルタとは独立）
        self._update_tag_bar()

        active = self.df[~self.df["completed"]].copy()
        if self.filter_tag.value != "すべて":
            active = active[active["tags"].map(self._match_tag_filter)].copy()

        # ----- Matrix -----
        for i, q in enumerate(QUADRANTS):
            rows = [
                self.get_task_row(r)
                for _, r in active[active["quadrant"] == q].iterrows()
            ]
            cell = self._matrix_cells[i]
            # セル自体は置換しない（GridSpec overlap 回避） [3](https://panel.holoviz.org/reference/layouts/GridSpec.html)
            cell.objects = [pn.pane.Markdown(f"### {q}"), *rows]

        # ----- Calendar -----
        def _sort_key(s: pd.Series) -> pd.Series:
            dt_s = pd.to_datetime(s, errors="coerce")
            return dt_s.fillna(pd.Timestamp.max)

        sorted_active = active.sort_values("deadline", key=_sort_key)

        self.calendar_view.objects = [
            pn.pane.Markdown("## 期限順"),
            *[self.get_task_row(r) for _, r in sorted_active.iterrows()],
        ]

        # ----- Archive -----
        done_df = self.df[self.df["completed"]].copy()
        self.archive_view.objects = [
            pn.pane.Markdown("## 完了済み（↩で戻せます）"),
            *[self.get_task_row(r) for _, r in done_df.iterrows()],
        ]


# =========================
# 起動
# =========================
app = TodoApp()

template = pn.template.FastListTemplate(
    title="✨ Eisenhower Matrix ToDo",
    sidebar=[
        "## 📝 新規タスク",
        app.title_input,
        app.quadrant_input,
        app.deadline_input,
        app.tags_select,
        app.add_button,
        pn.layout.Divider(),
        app.edit_form,
        app.filter_tag,
        pn.layout.Divider(),
        "## 📊 Tag別タスク数",
        app.tag_bar_pane,
    ],
    main=[app.tabs],
    accent_base_color="#6366f1",
    header_background="#6366f1",
    sidebar_width=320,
)

template.servable()