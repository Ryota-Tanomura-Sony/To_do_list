# schedule_gui.py
# -*- coding: utf-8 -*-

import io
import pandas as pd
import panel as pn

from gen_schedule import generate_pptx_bytes

pn.extension("tabulator", sizing_mode="stretch_width")

# -----------------------
# 初期データ（列定義）
# -----------------------
COLUMNS = ["lane","type","label","start","end","status","shape","color","note"]
DEFAULT_ROWS = [
    dict(lane="S7515 Proto1", type="bar",   label="Proto1-1(SCF)", start="2026-04", end="2026-09", status="E",
         shape="", color="", note=""),
    dict(lane="S7515 Proto1", type="point", label="中間審査1",     start="2026-07", end="2026-07", status="M",
         shape="Decision point", color="", note=""),
    dict(lane="S7515 TS/ES",  type="point", label="TS投入",        start="2027-02", end="2027-02", status="B",
         shape="Milestone", color="", note=""),
]
df = pd.DataFrame(DEFAULT_ROWS, columns=COLUMNS)

# -----------------------
# Tabulator（Panel 1.8.2互換）
# editable= は使わない
# editors + configuration で編集可能化する [1](https://panel.holoviz.org/reference/widgets/Tabulator.html)
# -----------------------
EDITORS = {
    "lane": "input",
    "label": "input",
    "start": "input",
    "end": "input",
    "color": "input",
    "note": "input",
    "type": {"type": "select", "values": ["bar", "point"]},
    "status": {"type": "select", "values": ["E", "M", "B"]},
    "shape": {"type": "select", "values": ["", "Sample", "Milestone", "Decision point", "ISO_Events"]},
}

tab = pn.widgets.Tabulator(
    df,
    show_index=False,
    height=360,
    pagination="local",
    page_size=50,
    selectable=True,  # 行選択（環境によっては "checkbox" が効かないことがあるので True に）
    editors=EDITORS,
    configuration={
        # Tabulator(JS)側に編集許可を渡す（Panelが露出していないオプションは configuration で渡す）[1](https://panel.holoviz.org/reference/widgets/Tabulator.html)
        "clipboard": True,
        "clipboardPasteAction": "replace",
    },
)

# -----------------------
# 行追加フォーム
# -----------------------
lane_w   = pn.widgets.TextInput(name="lane", value="S7515 Proto1")
type_w   = pn.widgets.Select(name="type", options=["bar","point"], value="bar")
label_w  = pn.widgets.TextInput(name="label", value="")
start_w  = pn.widgets.TextInput(name="start (YYYY-MM)", value="2026-01")
end_w    = pn.widgets.TextInput(name="end (YYYY-MM)", value="2026-01")
status_w = pn.widgets.Select(name="status", options=["E","M","B"], value="M")
shape_w  = pn.widgets.Select(name="shape", options=["","Sample","Milestone","Decision point","ISO_Events"], value="")
color_w  = pn.widgets.TextInput(name="color (任意: #RRGGBB / R,G,B / Green等)", value="")
note_w   = pn.widgets.TextInput(name="note", value="")

add_btn  = pn.widgets.Button(name="＋ 行追加", button_type="primary")
del_btn  = pn.widgets.Button(name="🗑 選択行削除", button_type="warning")

# -----------------------
# CSV 入出力
# FileInput は bytes を value に持つ [5](https://panel.holoviz.org/reference/widgets/FileInput.html)
# FileDownload callback は file-like（readを持つ）を返す必要あり [2](https://panel.holoviz.org/reference/widgets/FileDownload.html)
# bytes を返すと落ちる（今回のエラー）→ BytesIOで返す
# -----------------------
csv_in = pn.widgets.FileInput(accept=".csv")

def _csv_bytesio():
    b = tab.value.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    bio = io.BytesIO(b)
    bio.seek(0)  # 念のため先頭へ [4](https://docs.holoviz.org/panel/0.14.4/gallery/simple/file_download_examples.html)
    return bio

save_csv_btn = pn.widgets.FileDownload(
    label="💾 CSVダウンロード",
    filename="schedule.csv",
    button_type="success",
    callback=_csv_bytesio,
)

# -----------------------
# PPTX テンプレ入力
# -----------------------
pptx_in = pn.widgets.FileInput(accept=".pptx")

# -----------------------
# 生成設定
# -----------------------
start_axis = pn.widgets.TextInput(name="タイムライン開始 (YYYY-MM)", value="2026-01")
end_axis   = pn.widgets.TextInput(name="タイムライン終了 (YYYY-MM)", value="2030-12")
slide_idx  = pn.widgets.IntInput(name="対象スライドindex", value=0, start=0)

gen_btn = pn.widgets.Button(name="🚀 PPTX生成", button_type="danger")
status = pn.pane.Markdown("")

_generated = {"bytes": b""}  # 空でも bytes ではなく BytesIO で返す（NoneはNG）[3](https://discourse.holoviz.org/t/filedownload-widget-how-to-handle-the-case-of-returning-empty-string-none/7206)

def _pptx_bytesio():
    # FileDownload は file-like を要求する [2](https://panel.holoviz.org/reference/widgets/FileDownload.html)
    bio = io.BytesIO(_generated["bytes"] if _generated["bytes"] else b"")
    bio.seek(0)  # 念のため先頭へ [4](https://docs.holoviz.org/panel/0.14.4/gallery/simple/file_download_examples.html)
    return bio

download_pptx = pn.widgets.FileDownload(
    label="⬇️ 生成PPTXダウンロード",
    filename="schedule_generated.pptx",
    button_type="success",
    callback=_pptx_bytesio,
)

# -----------------------
# コールバック
# -----------------------
def _on_add(_):
    new = dict(
        lane=lane_w.value,
        type=type_w.value,
        label=label_w.value,
        start=start_w.value,
        end=end_w.value,
        status=status_w.value,
        shape=shape_w.value,
        color=color_w.value,
        note=note_w.value,
    )
    cur = tab.value.copy()
    cur.loc[len(cur)] = new
    tab.value = cur[COLUMNS].copy()

def _on_del(_):
    cur = tab.value.copy()
    sel = list(tab.selection) if tab.selection is not None else []
    if not sel:
        status.object = "⚠️ 削除する行を選択してください（表の行をクリック）"
        return
    cur = cur.drop(index=sel).reset_index(drop=True)
    tab.value = cur[COLUMNS].copy()

def _on_csv_loaded(event):
    if csv_in.value is None:
        return
    try:
        new_df = pd.read_csv(io.BytesIO(csv_in.value), dtype=str).fillna("")
        for c in COLUMNS:
            if c not in new_df.columns:
                new_df[c] = ""
        tab.value = new_df[COLUMNS].copy()
        status.object = "✅ CSVを読み込みました（不足列は自動補完）"
    except Exception as e:
        status.object = f"❌ CSV読み込みに失敗: {e}"

def _on_generate(_):
    if pptx_in.value is None:
        status.object = "❌ テンプレPPTX（.pptx）をアップロードしてください"
        return
    try:
        out_bytes = generate_pptx_bytes(
            template_pptx_bytes=pptx_in.value,
            df=tab.value.copy(),
            start_ym=start_axis.value,
            end_ym=end_axis.value,
            slide_index=int(slide_idx.value),
        )
        _generated["bytes"] = out_bytes
        status.object = "✅ 生成完了：下の「生成PPTXダウンロード」から取得できます"
    except Exception as e:
        status.object = f"❌ 生成に失敗: {e}"

add_btn.on_click(_on_add)
del_btn.on_click(_on_del)
csv_in.param.watch(_on_csv_loaded, "value")
gen_btn.on_click(_on_generate)

# -----------------------
# 画面レイアウト
# -----------------------
form = pn.Card(
    pn.Row(lane_w, type_w, status_w),
    pn.Row(label_w),
    pn.Row(start_w, end_w),
    pn.Row(shape_w, color_w),
    pn.Row(note_w),
    pn.Row(add_btn, del_btn),
    title="行追加フォーム",
)

io_card = pn.Card(
    pn.Row(csv_in, save_csv_btn),
    pn.Row(pptx_in),
    pn.Row(start_axis, end_axis, slide_idx),
    pn.Row(gen_btn, download_pptx),
    status,
    title="入出力（CSV / PPTX）",
)

app = pn.Column(
    "## 生産展開スケジュール：CSV作成GUI → PPTX自動生成（Panel 1.8.2対応）",
    pn.Row(form, io_card),
    pn.Card(tab, title="CSV編集（Tabulator）"),
)

app.servable()