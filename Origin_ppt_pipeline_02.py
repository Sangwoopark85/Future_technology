# Origin_ppt_pipeline_02.py
import os
import time
import pandas as pd
import win32com.client as win32
import win32con
import win32api
import win32gui
import matplotlib
matplotlib.use('Agg')  # GUI 없이 백엔드에서 렌더링만
import matplotlib.pyplot as plt

# ══════════════════════════════════════════════════════════════
# 공정별 그래프 설정
# ══════════════════════════════════════════════════════════════

OTPU_DIR = r'C:\Users\tablrain\Desktop\origin_dev\09_OTPU'

PROCESS_CONFIGS = {
    "Formation": {
        "data_source": "cyc",
        "graphs": [
            {
                "x"    : "Capacity",
                "y"    : "Voltage",
                "title": "Galvanostatic Profile",
                "slide": 7,
            },
            {
                "x"    : "Voltage",
                "y"    : "dQdV",
                "title": "dQ/dV Profile",
                "slide": 7,
            },
        ],
        "step_types": ["CHARGE", "DISCHARGE"],
        "cycle_nos" : [1],
    },
    "RPT": {
        "data_source": "cyc",
        "step_types": ["CHARGE", "DISCHARGE"],
        "cycle_nos" : [1],
        # 슬라이드 9: Galvanostatic(line) + Boxplot 4개 (위 2 / 아래 3)
        "slide_9": {
            "slide": 9,
            "layout": [2, 3],
            "graphs": [
                {"type": "line", "x": "Capacity", "y": "Voltage",
                 "title": "Galvanostatic Profile"},
                {"type": "box",  "y": "Capacity",
                 "title": "Capacity Boxplot"},
                {"type": "box",  "y": "Impedance",
                 "title": "10s DCIR Boxplot"},
                {"type": "box",  "y": "Impedance_0.1s",
                 "title": "0.1s DCIR Boxplot"},
                {"type": "box",  "y": "Impedance_5s",
                 "title": "5s DCIR Boxplot"},
            ],
        },
        # 슬라이드 10: Boxplot 2개(고정) + 사용자 선택 슬롯 4개 (위 3 / 아래 3)
        "slide_10": {
            "slide": 10,
            "layout": [3, 3],
            "graphs": [
                {"type": "box", "y": "Impedance_30s", "title": "30s DCIR Boxplot"},
                {"type": "box", "y": "Impedance_60s", "title": "60s DCIR Boxplot"},
                # 나머지 4개는 UI에서 선택한 컬럼으로 런타임에 채워짐
                # (selected_extra_columns 파라미터로 전달됨)
            ],
        },
    },
}

# ══════════════════════════════════════════════════════════════
# 유틸 함수
# ══════════════════════════════════════════════════════════════

def inches_to_pt(inches):
    return inches * 72


def cm_to_pt(cm):
    return cm * 28.3465  # 1 cm = 28.3465 pt (72 pt/inch ÷ 2.54 cm/inch)


def safe_filename(name, max_len=80):
    """
    파일명에 쓸 수 없는 문자 제거 + 길이 제한
    """
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, '_')
    if len(name) > max_len:
        name = name[:max_len]
    return name


def export_graph_png(col_pairs, plot_data, x_col, y_col, title, png_path, log_fn=print):
    """
    matplotlib으로 동일한 line 그래프를 PNG로 저장 (Origin과 독립적, 빠름)

    파라미터:
        col_pairs : [(x_col_lt, y_col_lt, legend_label, ch_idx), ...]
        plot_data : {y_col_lt: (x_data, y_data)} 형태의 dict
        title     : 그래프 제목
        png_path  : 저장 경로
    """
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)

    for x_lt, y_lt, legend_label, ch_idx in col_pairs:
        x_data, y_data = plot_data[y_lt]
        ax.plot(x_data, y_data, label=legend_label, linewidth=1.2)

    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title)
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

    if os.path.exists(png_path):
        log_fn(f"      └── PNG 저장 완료: {os.path.basename(png_path)}")
        return True
    else:
        log_fn(f"      ⚠️ PNG 저장 실패: {png_path}")
        return False


def export_boxplot_png(channel_data, y_col, title, png_path, log_fn=print):
    """
    matplotlib으로 채널별 boxplot을 PNG로 저장 (Origin과 독립적, 백업용)

    파라미터:
        channel_data : {ch_num: [values...]} 형태 dict
        y_col        : Y축 컬럼명
        title        : 그래프 제목
        png_path     : 저장 경로
    """
    ch_nums = sorted(channel_data.keys())
    labels  = [f"CH{int(ch):03d}" for ch in ch_nums]
    data    = [channel_data[ch] for ch in ch_nums]

    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    ax.boxplot(data, tick_labels=labels)
    ax.set_xlabel("Channel")
    ax.set_ylabel(y_col)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

    if os.path.exists(png_path):
        log_fn(f"      └── PNG 저장 완료: {os.path.basename(png_path)}")
        return True
    else:
        log_fn(f"      ⚠️ PNG 저장 실패: {png_path}")
        return False


def filter_data(df, step_types, cycle_nos):
    result = df.copy()
    if step_types:
        result = result[result['chStepType'].isin(step_types)]
    if cycle_nos:
        result = result[result['ulCurrentCycleNum'].isin(cycle_nos)]
    return result.reset_index(drop=True)


def get_channel_list(df):
    if 'chNo' in df.columns:
        return sorted(df['chNo'].dropna().unique().tolist())
    return []


def collect_channel_boxplot_data(filtered_df, y_col, channels):
    """
    채널별로 y_col 값들을 모아서 dict 반환
    {ch_num: [values...]}
    """
    result = {}
    if y_col not in filtered_df.columns:
        return result
    for ch in channels:
        ch_df  = filtered_df[filtered_df['chNo'] == ch]
        values = pd.to_numeric(ch_df[y_col], errors='coerce').dropna().tolist()
        if values:
            result[ch] = values
    return result


def calc_grid_positions(layout, slide_width_cm=27.517, slide_height_cm=19.05,
                         margin_cm=0.5, gap_cm=0.3, top_margin_cm=1.0,
                         bottom_margin_cm=1.0, row_gap_cm=0.3):
    """
    좌측 정렬 그리드 좌표 계산 (cm 단위로 계산 후 pt 반환)

    파라미터:
        layout : [위쪽 개수, 아래쪽 개수, ...] 예: [2, 3]

    반환:
        positions : [(left_pt, top_pt, width_pt, height_pt), ...]
                    그래프 순서대로 (위쪽 행 먼저, 그 다음 아래쪽 행)
    """
    max_cols = max(layout)
    usable_width  = slide_width_cm - 2 * margin_cm
    cell_width_cm = (usable_width - gap_cm * (max_cols - 1)) / max_cols

    usable_height  = (slide_height_cm - top_margin_cm - bottom_margin_cm
                       - row_gap_cm * (len(layout) - 1))
    cell_height_cm = usable_height / len(layout)

    positions = []
    for row_idx, n_in_row in enumerate(layout):
        top_cm = top_margin_cm + row_idx * (cell_height_cm + row_gap_cm)
        for col_idx in range(n_in_row):
            left_cm = margin_cm + col_idx * (cell_width_cm + gap_cm)
            positions.append((
                cm_to_pt(left_cm),
                cm_to_pt(top_cm),
                cm_to_pt(cell_width_cm),
                cm_to_pt(cell_height_cm),
            ))
    return positions


def find_origin_hwnd():
    result = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if "Origin" in win32gui.GetWindowText(hwnd):
                result.append(hwnd)
    win32gui.EnumWindows(callback, None)
    return result[0] if result else None


def find_ppt_hwnd():
    result = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            if "PowerPoint" in win32gui.GetWindowText(hwnd):
                result.append(hwnd)
    win32gui.EnumWindows(callback, None)
    return result[0] if result else None


def copy_graph_to_clipboard(origin, graph_name, log_fn=print):
    # ① PySide6 UI 윈도우 찾아서 최소화 (포커스 경쟁 제거)
    pyside_hwnd = None
    def find_pyside(hwnd, _):
        nonlocal pyside_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "충방전 Data Processing Tool" in title:
                pyside_hwnd = hwnd
    win32gui.EnumWindows(find_pyside, None)

    if pyside_hwnd:
        win32gui.ShowWindow(pyside_hwnd, 6)  # 최소화
        time.sleep(0.5)

    # ② PPT도 최소화
    ppt_hwnd = find_ppt_hwnd()
    if ppt_hwnd:
        win32gui.ShowWindow(ppt_hwnd, 6)
        time.sleep(0.5)

    # ③ Origin 활성화
    origin.Execute(f"win -a {graph_name};")
    time.sleep(2)

    origin_hwnd = find_origin_hwnd()
    if origin_hwnd:
        win32gui.ShowWindow(origin_hwnd, 9)
        win32gui.SetForegroundWindow(origin_hwnd)
        time.sleep(2)

    origin.Execute(f"win -a {graph_name};")
    time.sleep(1)

    focused_title = win32gui.GetWindowText(win32gui.GetForegroundWindow())
    log_fn(f"    ├── Ctrl+J 직전 포커스 창: '{focused_title}'")

    if "Origin" not in focused_title:
        raise RuntimeError(f"Origin 포커스 확보 실패. 현재 포커스: '{focused_title}'")

    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(ord('J'), 0, 0, 0)
    time.sleep(0.1)
    win32api.keybd_event(ord('J'), 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(3)

    # ④ PySide6 UI 복구
    if pyside_hwnd:
        win32gui.ShowWindow(pyside_hwnd, 9)


def open_presentation(pptx_app, template, log_fn=print):
    if template and os.path.exists(template):
        log_fn(f"    ├── 템플릿 경로: {template}")
        prs = pptx_app.Presentations.Open(
            template,
            ReadOnly=False,
            Untitled=True,
            WithWindow=False
        )
        prs.NewWindow()
        time.sleep(2)
        log_fn(f"    └── 템플릿 로드: {os.path.basename(template)} ({prs.Slides.Count}장)")
    else:
        prs = pptx_app.Presentations.Add()
        log_fn("    └── 빈 PPT 생성")
    time.sleep(2)
    return prs


def paste_ole_to_slide(prs, pptx_app, target_slide, left_pt, top_pt, width_pt, height_pt,
                        title, stem, log_fn=print):
    """
    클립보드에 복사된 Origin 그래프를 PPT의 지정 슬라이드/위치에 OLE로 붙여넣기
    """
    ppt_hwnd = find_ppt_hwnd()
    if ppt_hwnd:
        win32gui.ShowWindow(ppt_hwnd, 9)
        time.sleep(1)

    pptx_app.Activate()
    time.sleep(1)
    prs.Windows(1).Activate()
    time.sleep(1)
    prs.Windows(1).View.GotoSlide(target_slide)
    time.sleep(1)

    current_slide = prs.Windows(1).View.Slide
    prs.Windows(1).View.Slide.Shapes.Paste()
    time.sleep(2)

    current_slide = prs.Windows(1).View.Slide
    ole_shape     = current_slide.Shapes(current_slide.Shapes.Count)
    ole_shape.Left   = left_pt
    ole_shape.Top    = top_pt
    ole_shape.Width  = width_pt
    ole_shape.Height = height_pt

    # 그래프 아래 타이틀
    txt_top_pt = top_pt + height_pt + inches_to_pt(0.05)
    txt_h_pt   = inches_to_pt(0.25)
    txb = current_slide.Shapes.AddTextbox(
        1, left_pt, txt_top_pt, width_pt, txt_h_pt
    )
    txb.TextFrame.TextRange.Text = f"{title} - {stem}"
    txb.TextFrame.TextRange.Font.Size = 9
    txb.TextFrame.TextRange.Font.Bold = True
    txb.TextFrame.TextRange.ParagraphFormat.Alignment = 2

    log_fn(f"    └── 슬라이드 {target_slide} '{title}' 배치 완료 ✅")


# ══════════════════════════════════════════════════════════════
# 그래프 빌드 함수 (Line)
# ══════════════════════════════════════════════════════════════

def _build_graph(origin, ws_name, col_pairs, x_col, y_col, log_fn):
    """
    워크시트: col1=X(공통), col2~=Y(채널별)
    worksheet -s all + worksheet -p 200 → Origin 자동 색상 순환
    반환: 실제 생성된 그래프 이름
    """

    # ── [1] 컬럼 타입 설정 + LongName ────────────────────────
    origin.Execute(f"win -a {ws_name};")
    time.sleep(0.5)

    wks = origin.FindWorksheet(ws_name)

    # X컬럼(col1): type=4
    origin.Execute("wks.col(1).type = 4;")

    # Y컬럼(col2~): type=1 + LongName
    for x_lt, y_lt, legend_label, ch_idx in col_pairs:
        origin.Execute(f"wks.col({y_lt}).type = 1;")
        if wks:
            col = wks.Columns(y_lt - 1)  # 0-based
            col.LongName = legend_label
        time.sleep(0.05)

    origin.Execute("doc -uw;")
    time.sleep(0.5)
    log_fn(f"      └── 컬럼 타입 + LongName 설정 완료")

    # ── [2] 워크시트 전체 선택 후 한번에 플롯 ────────────────
    origin.Execute(f"win -a {ws_name};")
    time.sleep(0.5)
    origin.Execute("worksheet -s all;")
    time.sleep(0.5)
    origin.Execute("worksheet -p 200;")
    time.sleep(3)

    # ── [3] 실제 생성된 그래프 이름 확인 ─────────────────────
    actual_graph_name = origin.LTStr("page.name$")
    log_fn(f"      └── 생성된 그래프: '{actual_graph_name}'")

    gl = origin.FindGraphLayer(actual_graph_name)
    if gl:
        log_fn(f"      └── DataPlots.Count = {gl.DataPlots.Count}")

    origin.Execute("doc -uw;")
    time.sleep(0.5)
    origin.Execute("layer -a;")
    time.sleep(1)

    # ── [4] 축 타이틀 + 레전드 설정 ─────────────────────────
    gl = origin.FindGraphLayer(actual_graph_name)
    if gl is None:
        log_fn(f"      ⚠️ FindGraphLayer 실패")
        return actual_graph_name

    go_obj = gl.GraphObjects
    cnt    = go_obj.Count

    for i in range(cnt):
        go   = go_obj(i)
        name = go.Name
        if name == "XB":
            go.Text = x_col
            log_fn(f"      X축 타이틀 = '{x_col}' ✅")
        elif name == "YL":
            go.Text = y_col
            log_fn(f"      Y축 타이틀 = '{y_col}' ✅")

    # 레전드: Y컬럼 수만큼
    n_curves    = len(col_pairs)
    legend_text = "\r".join(
        f"\\l({i+1}) %({i+1},@LL)"
        for i in range(n_curves)
    )
    for i in range(cnt):
        go = go_obj(i)
        if go.Name == "Legend":
            go.Text = legend_text
            log_fn(f"      레전드 설정 완료 ({n_curves}개) ✅")
            break

    # ── [5] 최종 확정 ─────────────────────────────────────────
    origin.Execute(f"win -a {actual_graph_name};")
    time.sleep(0.5)
    origin.Execute("doc -uw;")
    time.sleep(1)

    return actual_graph_name


# ══════════════════════════════════════════════════════════════
# 그래프 빌드 함수 (Box Chart) — RPT용, 신규
# ══════════════════════════════════════════════════════════════

def _build_boxplot(origin, ws_name, channel_data, y_col, title, log_fn):
    """
    채널별 boxplot 생성
    워크시트: col1=CH001 데이터, col2=CH002 데이터, ... (채널마다 별도 컬럼)
    LongName = 채널명(예: CH001) → x축 카테고리로 사용됨

    파라미터:
        channel_data : {ch_num: [값1, 값2, ...]} 형태 dict
        y_col        : Y축(값) 컬럼명 (축 표기용)
        title        : 그래프 제목

    반환: 실제 생성된 그래프 이름 (실패 시 None)

    ⚠️ 주의: worksheet -p 906 (Box Chart plot ID)은 Origin 2025 환경에서
    아직 실제 검증되지 않았습니다. 실행 결과에 따라 LabTalk 명령을
    함께 수정해 나갈 예정입니다.
    """
    if not channel_data:
        log_fn(f"      ⚠️ Boxplot 데이터 없음 ({y_col}) → 스킵")
        return None

    origin.Execute(f"win -a {ws_name};")
    time.sleep(0.5)

    wks = origin.FindWorksheet(ws_name)
    if wks is None:
        log_fn(f"      ⚠️ FindWorksheet({ws_name}) 실패")
        return None

    ch_nums = sorted(channel_data.keys())

    # ── [1] 채널별 컬럼에 데이터 삽입 + LongName 설정 ────────
    for col_idx, ch_num in enumerate(ch_nums):
        values = channel_data[ch_num]
        wks.SetData(values, 0, col_idx)  # 0-based row, 0-based col
        origin.Execute(f"wks.col({col_idx + 1}).type = 1;")  # Y타입
        col = wks.Columns(col_idx)
        col.LongName = f"CH{int(ch_num):03d}"
        time.sleep(0.03)

    origin.Execute("doc -uw;")
    time.sleep(0.5)
    log_fn(f"      └── Boxplot 데이터 주입 완료 ({len(ch_nums)}개 채널)")

    # ── [2] 워크시트 전체 선택 + Box Chart로 플롯 ────────────
    origin.Execute(f"win -a {ws_name};")
    time.sleep(0.5)
    origin.Execute("worksheet -s all;")
    time.sleep(0.5)
    # TODO: Box Chart plot ID 검증 필요 (Origin 2025 기준)
    origin.Execute("worksheet -p 906;")
    time.sleep(3)

    # ── [3] 실제 생성된 그래프 이름 확인 ─────────────────────
    actual_graph_name = origin.LTStr("page.name$")
    log_fn(f"      └── 생성된 그래프: '{actual_graph_name}'")

    gl = origin.FindGraphLayer(actual_graph_name)
    if gl is None:
        log_fn(f"      ⚠️ FindGraphLayer 실패")
        return actual_graph_name

    origin.Execute("doc -uw;")
    time.sleep(0.5)
    origin.Execute("layer -a;")
    time.sleep(1)

    # ── [4] 축 타이틀 설정 ────────────────────────────────────
    gl = origin.FindGraphLayer(actual_graph_name)
    go_obj = gl.GraphObjects
    cnt    = go_obj.Count

    for i in range(cnt):
        go   = go_obj(i)
        name = go.Name
        if name == "XB":
            go.Text = "Channel"
            log_fn(f"      X축 타이틀 = 'Channel' ✅")
        elif name == "YL":
            go.Text = y_col
            log_fn(f"      Y축 타이틀 = '{y_col}' ✅")

    # ── [5] 그래프 제목 설정 ──────────────────────────────────
    try:
        origin.Execute(f'label -s "{title}";')
        time.sleep(0.3)
    except Exception as ex:
        log_fn(f"      ⚠️ 제목 설정 실패: {ex}")

    # ── [6] 최종 확정 ─────────────────────────────────────────
    origin.Execute(f"win -a {actual_graph_name};")
    time.sleep(0.5)
    origin.Execute("doc -uw;")
    time.sleep(1)

    return actual_graph_name


# ══════════════════════════════════════════════════════════════
# RPT 전용 슬라이드 처리 함수
# ══════════════════════════════════════════════════════════════

def _process_rpt_slide(origin, prs, pptx_app, slide_cfg, filtered_df, channels,
                        stem, process, output_name, output_dir, ws_prefix,
                        selected_extra_columns, log_fn):
    """
    RPT 공정의 슬라이드 1개(9 또는 10)를 처리
    - line/box 그래프 혼합 생성
    - Origin OLE로 PPT에 좌측정렬 그리드 배치
    - matplotlib PNG 백업 저장

    파라미터:
        slide_cfg               : PROCESS_CONFIGS["RPT"]["slide_9"] 또는 ["slide_10"]
        ws_prefix                : 워크시트 이름 접두사 (슬라이드별로 겹치지 않게)
        selected_extra_columns   : 슬라이드 10에서 사용자가 선택한 추가 컬럼 리스트
                                    (slide_9에서는 빈 리스트 전달)
    """
    target_slide = slide_cfg["slide"]
    layout       = slide_cfg["layout"]
    graph_cfgs   = list(slide_cfg["graphs"])  # 복사

    # 슬라이드 10의 경우, 사용자가 선택한 컬럼들로 나머지 슬롯을 채움
    for extra_col in selected_extra_columns:
        graph_cfgs.append({
            "type": "box",
            "y": extra_col,
            "title": f"{extra_col} Boxplot",
        })

    n_expected = sum(layout)
    if len(graph_cfgs) > n_expected:
        log_fn(f"    ⚠️ 슬라이드 {target_slide}: 그래프 {len(graph_cfgs)}개가 "
               f"레이아웃 슬롯({n_expected}개)보다 많습니다 → 초과분 무시")
        graph_cfgs = graph_cfgs[:n_expected]
    elif len(graph_cfgs) < n_expected:
        log_fn(f"    ℹ️ 슬라이드 {target_slide}: {len(graph_cfgs)}/{n_expected} "
               f"슬롯만 채워짐 (나머지는 빈 공간)")

    log_fn(f"\n▶ 슬라이드 {target_slide} 처리 중... ({len(graph_cfgs)}개 그래프)")

    # 슬라이드가 없으면 추가
    while prs.Slides.Count < target_slide:
        prs.Slides.Add(prs.Slides.Count + 1, target_slide)

    positions = calc_grid_positions(layout)

    for idx, cfg in enumerate(graph_cfgs):
        graph_type = cfg["type"]
        y_col      = cfg["y"]
        title      = cfg["title"]
        ws_name    = f"{ws_prefix}_{idx+1}"

        log_fn(f"\n    ▶ [{idx+1}/{len(graph_cfgs)}] {title} (type={graph_type}, Y={y_col})")

        if y_col not in filtered_df.columns:
            log_fn(f"    ⚠️ '{y_col}' 컬럼 없음 → 스킵")
            continue

        origin.CreatePage(2, ws_name, "Origin")
        time.sleep(1)
        wks = origin.FindWorksheet(ws_name)
        if wks is None:
            log_fn(f"    ⚠️ FindWorksheet({ws_name}) 실패")
            continue

        actual_name = None
        safe_title  = safe_filename(title.replace('/', '_'))
        png_path    = os.path.join(output_dir, f"{output_name}_{safe_title}.png")

        if graph_type == "line":
            x_col = cfg["x"]

            col_pairs  = []
            plot_data  = {}
            x_inserted = False
            x_col_lt   = 1

            for ch_idx, ch in enumerate(channels):
                ch_df  = filtered_df[filtered_df['chNo'] == ch]
                ch_num = int(ch)

                x_data = pd.to_numeric(ch_df[x_col], errors='coerce').dropna().tolist()
                y_data = pd.to_numeric(ch_df[y_col], errors='coerce').dropna().tolist()

                if not x_data or not y_data:
                    continue

                min_len = min(len(x_data), len(y_data))
                x_data  = x_data[:min_len]
                y_data  = y_data[:min_len]

                if not x_inserted:
                    wks.SetData(x_data, 0, 0)
                    x_inserted = True

                y_col_lt = len(col_pairs) + 2
                wks.SetData(y_data, 0, y_col_lt - 1)

                legend_label = f"CH{ch_num:03d}"
                col_pairs.append((x_col_lt, y_col_lt, legend_label, ch_idx))
                plot_data[y_col_lt] = (x_data, y_data)

            if not col_pairs:
                log_fn(f"    ⚠️ 데이터 없음 → 스킵")
                continue

            time.sleep(1)
            actual_name = _build_graph(origin, ws_name, col_pairs, x_col, y_col, log_fn)
            export_graph_png(col_pairs, plot_data, x_col, y_col, title, png_path, log_fn)

        elif graph_type == "box":
            channel_data = collect_channel_boxplot_data(filtered_df, y_col, channels)
            if not channel_data:
                log_fn(f"    ⚠️ 데이터 없음 → 스킵")
                continue

            time.sleep(1)
            actual_name = _build_boxplot(origin, ws_name, channel_data, y_col, title, log_fn)
            export_boxplot_png(channel_data, y_col, title, png_path, log_fn)

        else:
            log_fn(f"    ⚠️ 알 수 없는 그래프 타입: {graph_type} → 스킵")
            continue

        if actual_name is None:
            log_fn(f"    ⚠️ 그래프 생성 실패 → OLE 삽입 스킵")
            continue

        left_pt, top_pt, width_pt, height_pt = positions[idx]

        copy_graph_to_clipboard(origin, actual_name, log_fn)
        paste_ole_to_slide(
            prs, pptx_app, target_slide,
            left_pt, top_pt, width_pt, height_pt,
            title, stem, log_fn
        )


# ══════════════════════════════════════════════════════════════
# 통합 파이프라인
# ══════════════════════════════════════════════════════════════

def run_pipeline(
    cyc_df,
    cts_df,
    output_dir,
    stem,
    process    = "Formation",
    step_types = None,
    cycle_nos  = None,
    template   = None,
    selected_extra_columns = None,   # RPT 슬라이드10 추가 슬롯용 컬럼 리스트
    img_left   = 1.0,
    img_top    = 1.5,
    img_width  = 8.0,
    img_height = 5.0,
    log_fn     = print,
):
    os.makedirs(output_dir, exist_ok=True)
    output_name = safe_filename(f"{stem}_{process}")
    opju_path = os.path.join(output_dir, f"{output_name}.opju")
    pptx_path = os.path.join(output_dir, f"{output_name}.pptx")

    if process not in PROCESS_CONFIGS:
        raise ValueError(f"지원하지 않는 공정: {process}")

    proc_cfg    = PROCESS_CONFIGS[process]
    data_source = proc_cfg["data_source"]
    step_types  = step_types or proc_cfg["step_types"]
    cycle_nos   = cycle_nos  or proc_cfg["cycle_nos"]
    selected_extra_columns = selected_extra_columns or []

    # 데이터 소스 선택
    if cyc_df is not None and cts_df is not None:
        plot_df = cyc_df if data_source == 'cyc' else cts_df
        log_fn(f"  ├── 데이터 소스: {data_source.upper()} (공정 설정 기준)")
    elif cyc_df is not None:
        plot_df = cyc_df
        log_fn(f"  ├── 데이터 소스: CYC (자동 선택)")
    elif cts_df is not None:
        plot_df = cts_df
        log_fn(f"  ├── 데이터 소스: CTS (자동 선택)")
    else:
        raise ValueError("cyc_df, cts_df 모두 없습니다.")

    # ── [1] 데이터 필터링 ──────────────────────────────────────
    log_fn(f"\n▶ [1/4] 데이터 필터링 중... (공정: {process})")
    log_fn(f"    ├── Step type : {step_types}")
    log_fn(f"    ├── Cycle nos : {cycle_nos}")

    filtered_df = filter_data(plot_df, step_types, cycle_nos)
    channels    = get_channel_list(filtered_df)

    log_fn(f"    ├── 채널 수   : {len(channels)}개 → {channels}")
    log_fn(f"    └── 데이터 수 : {len(filtered_df)}행")

    if filtered_df.empty:
        raise ValueError("필터링 후 데이터가 없습니다.")

    # ── [2] PPT 실행 ───────────────────────────────────────────
    log_fn("\n▶ [2/4] PowerPoint 실행 중...")
    pptx_app = win32.Dispatch("PowerPoint.Application")
    pptx_app.Visible = 1
    time.sleep(2)
    prs = open_presentation(pptx_app, template, log_fn)

    # ── [3] Origin 실행 ────────────────────────────────────────
    log_fn("\n▶ [3/4] Origin 실행 중...")
    origin = win32.Dispatch("Origin.Application")
    origin.Visible = 1
    time.sleep(3)
    log_fn("    └── Origin 실행 완료")

    try:
        origin.NewProject()
        time.sleep(1)

        if process == "Formation":
            _run_formation(origin, prs, pptx_app, proc_cfg, filtered_df, channels,
                            stem, process, output_name, output_dir, opju_path, log_fn)

        elif process == "RPT":
            log_fn("\n▶ [4/4] RPT 슬라이드 9, 10 처리 중...")
            _process_rpt_slide(
                origin, prs, pptx_app, proc_cfg["slide_9"], filtered_df, channels,
                stem, process, output_name, output_dir, "S9",
                selected_extra_columns=[], log_fn=log_fn
            )
            _process_rpt_slide(
                origin, prs, pptx_app, proc_cfg["slide_10"], filtered_df, channels,
                stem, process, output_name, output_dir, "S10",
                selected_extra_columns=selected_extra_columns, log_fn=log_fn
            )

            # ── .opju 저장 ─────────────────────────────────────
            log_fn("\n    ▶ .opju 저장 중...")
            if os.path.exists(opju_path):
                os.remove(opju_path)
            opju_path_lt = opju_path.replace('\\', '/')
            origin.Execute(f'save {opju_path_lt}')
            time.sleep(5)
            if not os.path.exists(opju_path):
                raise FileNotFoundError(f".opju 저장 실패: {opju_path}")
            log_fn(f"    ├── .opju 저장 완료: {opju_path}")
            log_fn(f"    └── 파일 크기: {os.path.getsize(opju_path):,} bytes")

        else:
            raise ValueError(f"run_pipeline에서 처리되지 않은 공정: {process}")

    except Exception as e:
        log_fn(f"\n  ❌ 파이프라인 실패: {e}")
        raise

    finally:
        log_fn("\n  ▶ Origin 종료 중...")
        try:
            origin.Exit()
            time.sleep(2)
        except Exception as ex:
            log_fn(f"    ⚠️ Origin 종료 예외: {ex}")
        try:
            del origin
            log_fn("    └── Origin COM 릴리즈 완료")
        except Exception:
            pass

    log_fn(f"\n  ▶ PPT 저장: {pptx_path}")
    prs.SaveAs(pptx_path)
    time.sleep(2)
    prs.Close()
    pptx_app.Quit()
    log_fn("    └── PPT 저장 완료 ✅")


def _run_formation(origin, prs, pptx_app, proc_cfg, filtered_df, channels,
                    stem, process, output_name, output_dir, opju_path, log_fn):
    """
    Formation 공정 처리 (기존 로직, 변경 없음)
    """
    graphs = proc_cfg["graphs"]
    graph_name_map = {}

    for i, cfg in enumerate(graphs):
        x_col   = cfg["x"]
        y_col   = cfg["y"]
        title   = cfg["title"]
        ws_name = f"Data{i+1}"

        log_fn(f"\n    ▶ 그래프 {i+1}: {title} (X={x_col}, Y={y_col})")

        if y_col not in filtered_df.columns:
            log_fn(f"    ⚠️ '{y_col}' 컬럼 없음 → 스킵")
            continue

        origin.CreatePage(2, ws_name, "Origin")
        time.sleep(1)

        wks = origin.FindWorksheet(ws_name)
        if wks is None:
            log_fn(f"    ⚠️ FindWorksheet({ws_name}) 실패")
            continue

        col_pairs  = []
        plot_data  = {}
        x_inserted = False
        x_col_lt   = 1

        for ch_idx, ch in enumerate(channels):
            ch_df  = filtered_df[filtered_df['chNo'] == ch]
            ch_num = int(ch)

            for cyc in proc_cfg["cycle_nos"]:
                cyc_data = ch_df[ch_df['ulCurrentCycleNum'] == cyc]

                for stype in proc_cfg["step_types"]:
                    stype_df = cyc_data[cyc_data['chStepType'] == stype]
                    if stype_df.empty:
                        continue

                    x_data = pd.to_numeric(stype_df[x_col], errors='coerce').dropna().tolist()
                    y_data = pd.to_numeric(stype_df[y_col], errors='coerce').dropna().tolist()

                    if not x_data or not y_data:
                        continue

                    min_len = min(len(x_data), len(y_data))
                    x_data  = x_data[:min_len]
                    y_data  = y_data[:min_len]

                    if not x_inserted:
                        wks.SetData(x_data, 0, 0)
                        x_inserted = True

                    y_col_lt = len(col_pairs) + 2
                    wks.SetData(y_data, 0, y_col_lt - 1)

                    stype_abbr   = "CHG" if stype == "CHARGE" else "DCH"
                    legend_label = f"CH{ch_num:03d} {stype_abbr}"
                    col_pairs.append((x_col_lt, y_col_lt, legend_label, ch_idx))
                    plot_data[y_col_lt] = (x_data, y_data)

        if not col_pairs:
            log_fn(f"    ⚠️ 데이터 없음 → 스킵")
            continue

        time.sleep(1)

        actual_name = _build_graph(origin, ws_name, col_pairs, x_col, y_col, log_fn)
        graph_name_map[i] = actual_name
        log_fn(f"    └── {actual_name} 생성 완료 ({len(col_pairs)}개 선)")

        safe_title = safe_filename(title.replace('/', '_'))
        png_path = os.path.join(output_dir, f"{output_name}_{safe_title}.png")
        export_graph_png(col_pairs, plot_data, x_col, y_col, title, png_path, log_fn)

    # ── .opju 저장 ─────────────────────────────────────────
    log_fn("\n    ▶ .opju 저장 중...")
    if os.path.exists(opju_path):
        os.remove(opju_path)

    opju_path_lt = opju_path.replace('\\', '/')
    origin.Execute(f'save {opju_path_lt}')
    time.sleep(5)

    if not os.path.exists(opju_path):
        raise FileNotFoundError(f".opju 저장 실패: {opju_path}")

    log_fn(f"    ├── .opju 저장 완료: {opju_path}")
    log_fn(f"    └── 파일 크기: {os.path.getsize(opju_path):,} bytes")

    # ── 슬라이드: 두 그래프 나란히 배치 ─────────────
    target_slide = graphs[0].get("slide", 7)
    slide_values = {cfg.get("slide", 7) for cfg in graphs}
    if len(slide_values) > 1:
        log_fn(f"    ⚠️ 그래프별 slide 값이 다릅니다 {slide_values} → "
               f"첫 번째 그래프 기준 슬라이드 {target_slide} 사용")

    log_fn(f"\n▶ [4/4] 슬라이드 {target_slide} 나란히 배치 중...")

    while prs.Slides.Count < target_slide:
        prs.Slides.Add(prs.Slides.Count + 1, target_slide)

    side_width_pt  = cm_to_pt(13)
    side_height_pt = cm_to_pt(10)

    gap_pt = inches_to_pt(0.2)
    side_left_1_pt = inches_to_pt(0.3)
    side_left_2_pt = side_left_1_pt + side_width_pt + gap_pt
    side_top_pt    = inches_to_pt(0.8)

    graph_configs_side = [
        (graph_name_map.get(0), graphs[0]["title"], side_left_1_pt),
        (graph_name_map.get(1), graphs[1]["title"], side_left_2_pt),
    ]

    pptx_app.Activate()
    time.sleep(1)
    prs.Windows(1).Activate()
    time.sleep(1)
    prs.Windows(1).View.GotoSlide(target_slide)
    time.sleep(1)

    for actual_name, title, left_pos_pt in graph_configs_side:
        if actual_name is None:
            log_fn(f"    ⚠️ {title} 스킵 (그래프 없음)")
            continue

        copy_graph_to_clipboard(origin, actual_name, log_fn)
        paste_ole_to_slide(
            prs, pptx_app, target_slide,
            left_pos_pt, side_top_pt, side_width_pt, side_height_pt,
            title, stem, log_fn
        )