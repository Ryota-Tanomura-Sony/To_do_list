import panel as pn
import pandas as pd
import datetime as dt
from plyer import notification
import os
import param
from typing import Any, cast

# Panelの拡張機能を有効化
pn.extension('tabulator', 'notifications')

# --- 設定とデータ管理 ---
DATA_FILE = "todo_list.csv"
LOG_FILE = "activity_log.csv"
ENCODING = "utf-8-sig"

# 曜日変換用
WDAYS = ["月", "火", "水", "木", "金", "土", "日"]

# タグリスト（一元管理）
TAGS = ['画像センサ提案', 'シミュレーション開発', '連絡待ち', '社内会議']


def _notify(kind: str, message: str) -> None:
"""pn.state.notifications が None の場合に備えたラッパー"""
notif = pn.state.notifications
if notif is not None:
getattr(notif, kind)(message)


def load_data() -> pd.DataFrame:
cols = ['id', 'title', 'quadrant', 'deadline', 'tags', 'completed']
if os.path.exists(DATA_FILE):
try:
df = pd.read_csv(DATA_FILE, encoding=ENCODING)
df['id'] = pd.Series(pd.to_numeric(df['id'], errors='coerce')).fillna(0).astype('int64')
df['completed'] = df['completed'].astype(str).map(lambda x: x.strip().lower() == 'true').astype(bool)
df['deadline'] = pd.Series(pd.to_datetime(df['deadline'], errors='coerce')).dt.date

for col in cols:
if col not in df.columns:
df[col] = False if col == 'completed' else ""
return cast(pd.DataFrame, df[cols])
except Exception as e:
print(f"Load Error: {e}")
return pd.DataFrame(columns=pd.Index(cols))


def save_data(df: pd.DataFrame) -> None:
try:
df.to_csv(DATA_FILE, index=False, encoding=ENCODING)
except Exception as e:
print(f"Save Error: {e}")


def update_activity() -> int:
today = dt.date.today()
if os.path.exists(LOG_FILE):
try:
log: pd.DataFrame = pd.read_csv(LOG_FILE, encoding=ENCODING)
log['date'] = pd.Series(pd.to_datetime(log['date'], errors='coerce')).dt.date
except Exception:
log = pd.DataFrame(columns=pd.Index(['date']))
else:
log = pd.DataFrame(columns=pd.Index(['date']))

if today not in log['date'].values:
new_row = pd.DataFrame({'date': [today]})
log = pd.concat([log, new_row], ignore_index=True)
log.to_csv(LOG_FILE, index=False, encoding=ENCODING)

dates = sorted(log['date'].unique(), reverse=True)
count = 0
curr = today
for d in dates:
if d == curr:
count += 1
curr -= dt.timedelta(days=1)
elif d > curr:
continue
else:
break
return count


# --- アプリケーションロジック ---

class TodoApp(param.Parameterized):
def __init__(self, **params: Any) -> None:
super().__init__(**params)
self.df: pd.DataFrame = load_data()
self.continuity_count = update_activity()

# UIコンポーネント (Input)
self.title_input = pn.widgets.TextInput(name='タスク名', placeholder='例: 資料作成', sizing_mode='stretch_width')
self.quadrant_input = pn.widgets.Select(name='象限', options=[
'Do (緊急かつ重要)',
'Schedule (重要だが緊急でない)',
'Delegate (緊急だが重要でない)',
'Eliminate (重要でも緊急でもない)'
], sizing_mode='stretch_width')
self.deadline_input = pn.widgets.DatePicker(name='期限', value=dt.date.today(), sizing_mode='stretch_width')
self.tags_input = pn.widgets.AutocompleteInput(
name='タグ', options=TAGS,
placeholder='タグを入力', sizing_mode='stretch_width'
)
self.add_button = pn.widgets.Button(name='タスクを追加', button_type='primary', sizing_mode='stretch_width')
self.filter_tag = pn.widgets.Select(name='タグで絞り込み', options=['すべて'] + TAGS, sizing_mode='stretch_width')

self.matrix_view = pn.GridSpec(ncols=2, nrows=2, sizing_mode='stretch_both', min_height=600)
self.calendar_view = pn.Column(sizing_mode='stretch_both', min_height=600, scroll=True)
self.archive_view = pn.Column(sizing_mode='stretch_both', min_height=600, scroll=True)

self.tabs = pn.Tabs(
('マトリクス', self.matrix_view),
('カレンダー表示', self.calendar_view),
('完了済み一覧', self.archive_view),
sizing_mode='stretch_both',
dynamic=True
)

self.sidebar_info = pn.indicators.Number(
name="連続更新日数", value=self.continuity_count,
format='{value}日目！', font_size='20pt', default_color='orange'
)

self.filter_tag.param.watch(lambda _e: self.refresh_ui(), 'value')

try:
self.refresh_ui()
except Exception as e:
print(f"Init UI Error: {e}")

def add_task(self, _event: Any) -> None:
if not self.title_input.value:
_notify('error', 'タスク名を入力してください')
return

try:
new_task = pd.DataFrame([{
'id': int(dt.datetime.now().timestamp() * 1000),
'title': self.title_input.value,
'quadrant': self.quadrant_input.value,
'deadline': self.deadline_input.value,
'tags': self.tags_input.value or "",
'completed': False
}])

self.df = pd.concat([self.df, new_task], ignore_index=True)
self.df['id'] = self.df['id'].astype('int64')
self.df['deadline'] = pd.Series(pd.to_datetime(self.df['deadline'], errors='coerce')).dt.date
save_data(self.df)

self.title_input.value = ''
self.continuity_count = update_activity()
self.refresh_ui()
_notify('success', 'タスクを追加しました')
except Exception as e:
_notify('error', f'追加エラー: {e}')

def toggle_complete(self, task_id: int) -> None:
try:
self.df.loc[self.df['id'] == int(task_id), 'completed'] = True
save_data(self.df)
self.refresh_ui()
_notify('success', 'タスクを完了しました')
except Exception as e:
_notify('error', f'完了処理エラー: {e}')

def get_task_row(self, row: pd.Series) -> pn.Row: # type: ignore[type-arg]
"""タスク1件分の行を生成"""
# cast(Any, ...) でpandasスタブの過剰な型推論を抑制
deadline: Any = cast(Any, row['deadline'])
title: str = str(row['title'])
tags: str = str(row['tags'])
task_id: int = int(cast(Any, row['id']))
completed: bool = bool(cast(Any, row['completed']))

if pd.isna(deadline):
return pn.Row(pn.pane.Markdown(f"**{title}** (期限未設定)"), sizing_mode='stretch_width')

wday = WDAYS[deadline.weekday()]
date_str = f"{deadline.strftime('%m/%d')} ({wday})"

is_overdue = deadline < dt.date.today() and not completed
styles = {'color': 'red', 'font-weight': 'bold'} if is_overdue else {}

complete_btn = pn.widgets.Button(name='✔', width=40, button_type='success')
complete_btn.on_click(lambda _e, tid=task_id: self.toggle_complete(tid))

return pn.Row(
complete_btn,
pn.pane.Markdown(f"**{title}** <br> 📅 {date_str} | 🏷️ {tags}", styles=styles),
sizing_mode='stretch_width'
)

def refresh_ui(self) -> None:
"""各コンテナの中身を更新"""
try:
self.df['completed'] = self.df['completed'].astype(bool)

view_df: pd.DataFrame = cast(pd.DataFrame, self.df[~self.df['completed']].copy())
if self.filter_tag.value != 'すべて':
view_df = cast(pd.DataFrame, view_df[view_df['tags'] == self.filter_tag.value].copy())

completed_df: pd.DataFrame = cast(pd.DataFrame, self.df[self.df['completed']].copy())

# 1. マトリクス表示の更新
quadrants = [
'Do (緊急かつ重要)', 'Schedule (重要だが緊急でない)',
'Delegate (緊急だが重要でない)', 'Eliminate (重要でも緊急でもない)'
]
for i, q in enumerate(quadrants):
q_tasks: pd.DataFrame = cast(pd.DataFrame, view_df[view_df['quadrant'] == q].copy())
task_items = [self.get_task_row(r) for _, r in q_tasks.iterrows()]

content = pn.Column(
f"### {q}",
pn.Column(*task_items, scroll=True, min_height=200, sizing_mode='stretch_both'),
styles={'background': '#f9f9f9', 'border': '1px solid #ddd', 'padding': '10px'},
sizing_mode='stretch_both'
)
self.matrix_view[i // 2, i % 2] = content

# 2. カレンダー表示の更新 (月・曜日ごと)
sorted_df: pd.DataFrame = view_df.sort_values('deadline')
calendar_objects: list[Any] = [pn.pane.Markdown("## 📅 月別スケジュール")]

current_month = None
for _, r in sorted_df.iterrows():
r_deadline: Any = cast(Any, r['deadline'])
if pd.isna(r_deadline):
calendar_objects.append(self.get_task_row(r))
continue
task_month = r_deadline.strftime('%Y年 %m月')
if task_month != current_month:
current_month = task_month
calendar_objects.append(pn.pane.Markdown(f"### 🗓️ {current_month}"))
calendar_objects.append(self.get_task_row(r))

self.calendar_view.objects = calendar_objects

# 3. 完了一覧の更新
archive_list: list[Any] = [
pn.pane.Markdown(f"~~{r['title']}~~ ({r['deadline']})")
for _, r in completed_df.iterrows()
]
self.archive_view.objects = [
pn.pane.Markdown("## ✅ 完了したタスク"),
pn.Column(*archive_list, sizing_mode='stretch_width')
]

self.sidebar_info.value = self.continuity_count
except Exception as e:
print(f"Refresh UI Error: {e}")
_notify('error', f"UI更新エラー: {e}")

def update_sidebar_info(self) -> pn.indicators.Number:
return self.sidebar_info

def main_view(self) -> pn.Tabs:
return self.tabs


# --- 初期化 ---
app = TodoApp()
app.add_button.on_click(app.add_task)

# --- レイアウト構築 ---
template = pn.template.FastListTemplate(
title="実務用 Eisenhower Matrix ToDo",
sidebar=[
"## 新規タスク追加",
app.title_input, app.quadrant_input, app.deadline_input, app.tags_input, app.add_button,
pn.layout.Divider(),
app.filter_tag,
pn.layout.Divider(),
app.update_sidebar_info
],
main=[app.main_view()],
accent_base_color="#2F4F4F",
header_background="#2F4F4F",
)


def send_notification() -> None:
try:
df = load_data()
incomplete: pd.DataFrame = cast(pd.DataFrame, df[~df['completed']].copy())
incomplete_sorted: pd.DataFrame = cast(pd.DataFrame, incomplete.sort_values('deadline'))
if not incomplete_sorted.empty:
notification.notify( # type: ignore[misc]
title="ToDoリマインダー",
message=f"未完了: {len(incomplete_sorted)}件\n最優先: {incomplete_sorted.iloc[0]['title']}",
app_name="ToDo App",
timeout=10
)
except Exception:
pass


def on_app_load() -> None:
pn.state.add_periodic_callback(send_notification, period=3600000)


pn.state.onload(on_app_load)

template.servable()
