# Main_ui_03.py
import os
import sys
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QTextEdit,
    QGroupBox, QGridLayout, QProgressBar, QFrame,
    QSplitter, QCheckBox, QStackedWidget, QComboBox,
    QDialog, QDialogButtonBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QObject, QThread, QSettings
from PySide6.QtGui import QFont, QTextCursor, QPixmap, QFontDatabase, QPalette, QColor

# ══════════════════════════════════════════════════════════════
# 경로 설정
# ══════════════════════════════════════════════════════════════
LG_FONT_PATH = r"C:\Users\tablrain\Desktop\origin_dev\Setup_file\02_font\LGSmHaR_v1.4_151215.ttf"
LG_LOGO_PATH = r"C:\Users\tablrain\Desktop\origin_dev\Setup_file\01_ensol\lgensol.png"
HISTORY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "run_history.json"
)
SETTINGS_ORG = "LGEnS"
SETTINGS_APP = "ChDchTool"


# ══════════════════════════════════════════════════════════════
# 실행 이력 관리
# ══════════════════════════════════════════════════════════════
class HistoryManager:
    MAX = 20

    @staticmethod
    def load():
        try:
            if os.path.exists(HISTORY_PATH):
                with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    @staticmethod
    def save(records):
        try:
            with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(records[-HistoryManager.MAX:], f,
                          ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def add(record):
        records = HistoryManager.load()
        records.append(record)
        HistoryManager.save(records)


# ══════════════════════════════════════════════════════════════
# Worker
# ══════════════════════════════════════════════════════════════
class WorkerSignals(QObject):
    log   = Signal(str)
    done  = Signal(bool)
    stage = Signal(str, int)


class Worker(QThread):
    def __init__(self, config):
        super().__init__()
        self.config  = config
        self.signals = WorkerSignals()

    def run(self):
        log_file = None
        try:
            import pandas as pd
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from Origin_ppt_pipeline_02 import run_pipeline, PROCESS_CONFIGS

            cfg = self.config
            os.makedirs(cfg['output_dir'], exist_ok=True)
            log_path = os.path.join(cfg['output_dir'], 'log.txt')
            log_file = open(log_path, 'w', encoding='utf-8')

            def log(msg):
                self.signals.log.emit(msg)
                log_file.write(msg + '\n')
                log_file.flush()

            proc_cfg = PROCESS_CONFIGS[cfg['process']]
            log("=" * 50)
            log(f"▶ 실행 모드    : {cfg['mode']}")
            log(f"  공정         : {cfg['process']}")
            log(f"  데이터 소스  : {proc_cfg['data_source'].upper()}")
            log(f"  Step type   : {cfg['step_types']}")
            log(f"  Cycle nos   : {cfg['cycle_nos']}")
            log(f"  출력 경로   : {cfg['output_dir']}")
            log(f"  템플릿       : {cfg['template'] or '없음 (빈 PPT)'}")

            self.signals.stage.emit("📂 데이터 로드 중...", 10)

            if cfg['mode'] == 'parsing':
                cyc_df, cts_df = self._run_parsing_mode(cfg, log)
                if cyc_df is None:
                    self.signals.done.emit(False)
                    return
                stem = os.path.basename(os.path.normpath(cfg['raw_dir']))
            else:
                cyc_df, cts_df = self._run_csv_mode(cfg, log)
                if cyc_df is None and cts_df is None:
                    self.signals.done.emit(False)
                    return
                stem = os.path.basename(
                    os.path.dirname(os.path.abspath(cfg['csv_path']))
                )

            log(f"  ├── 출력 파일명: '{stem}'")

            self.signals.stage.emit("🔍 채널 필터 적용 중...", 30)
            selected_channels = cfg.get('selected_channels', [])
            if selected_channels and cyc_df is not None:
                cyc_df = cyc_df[
                    cyc_df['chNo'].isin(selected_channels)
                ].reset_index(drop=True)
                log(f"  ├── 채널 필터: {selected_channels}")
            if selected_channels and cts_df is not None:
                cts_df = cts_df[
                    cts_df['chNo'].isin(selected_channels)
                ].reset_index(drop=True)

            self.signals.stage.emit("📊 Origin 그래프 생성 중...", 50)

            run_pipeline(
                cyc_df     = cyc_df,
                cts_df     = cts_df,
                output_dir = cfg['output_dir'],
                stem       = stem,
                process    = cfg['process'],
                step_types = cfg['step_types'],
                cycle_nos  = cfg['cycle_nos'],
                template   = cfg['template'],
                log_fn     = log,
            )

            self.signals.stage.emit("✅ 완료", 100)
            HistoryManager.add({
                'datetime'   : datetime.now().strftime('%Y-%m-%d %H:%M'),
                'process'    : cfg['process'],
                'mode'       : cfg['mode'],
                'output_dir' : cfg['output_dir'],
                'stem'       : stem,
            })

            log(f"\n{'='*50}")
            log("✅ 전체 완료")
            log(f"  출력 → {cfg['output_dir']}")
            self.signals.done.emit(True)

        except Exception as e:
            import traceback
            msg = f"\n❌ 오류 발생:\n{traceback.format_exc()}"
            self.signals.log.emit(msg)
            self.signals.stage.emit("❌ 오류 발생", 0)
            if log_file:
                log_file.write(msg + '\n')
            self.signals.done.emit(False)

        finally:
            if log_file:
                log_file.close()

    def _run_parsing_mode(self, cfg, log):
        import pandas as pd
        from Parsing_01 import File_search, cyc_cts_sch_comb

        log("\n▶ [Parsing 모드] 파일 탐색 중...")
        file_search = File_search(cfg['raw_dir'])
        file_list   = file_search.integration_list()

        if not file_list:
            log("❌ .cyc/.cts/.sch 파일 쌍 없음")
            return None, None

        log(f"  └── {len(file_list)}개 파일 쌍 발견")
        all_cyc, all_cts = [], []
        total = len(file_list)

        for idx, file in enumerate(file_list):
            stem = os.path.splitext(os.path.basename(file['.cyc']))[0]
            log(f"\n  ├── [{idx+1}/{total}] {stem} 파싱 중...")
            parser = cyc_cts_sch_comb(
                file['.cyc'], file['.cts'], file['.sch']
            )
            cyc_result, cts_result, _ = parser.comb_data_preprocessing()
            cyc_result['source_file'] = stem
            cts_result['source_file'] = stem
            log(f"    ├── CYC: {len(cyc_result)}행")
            log(f"    └── CTS: {len(cts_result)}행")
            all_cyc.append(cyc_result)
            all_cts.append(cts_result)
            pct = 10 + int((idx + 1) / total * 20)
            self.signals.stage.emit(f"📂 파싱 중... [{idx+1}/{total}]", pct)

        combined_cyc = pd.concat(all_cyc, ignore_index=True)
        combined_cts = pd.concat(all_cts, ignore_index=True)

        folder_name = os.path.basename(os.path.normpath(cfg['raw_dir']))
        output_dir  = cfg['output_dir']
        os.makedirs(output_dir, exist_ok=True)

        cyc_csv = os.path.join(output_dir, f"{folder_name}_combined_cyc.csv")
        cts_csv = os.path.join(output_dir, f"{folder_name}_combined_cts.csv")
        combined_cyc.to_csv(cyc_csv, index=False, encoding='utf-8-sig')
        combined_cts.to_csv(cts_csv, index=False, encoding='utf-8-sig')
        log(f"  ├── CYC CSV 저장: {os.path.basename(cyc_csv)}")
        log(f"  └── CTS CSV 저장: {os.path.basename(cts_csv)}")

        return combined_cyc, combined_cts

    def _run_csv_mode(self, cfg, log):
        import pandas as pd

        log("\n▶ [CSV 모드] CSV 로드 중...")
        csv_path = cfg.get('csv_path', '').strip()

        if not csv_path or not os.path.exists(csv_path):
            log(f"❌ CSV 파일 없음: {csv_path}")
            return None, None

        basename = os.path.basename(csv_path).lower()
        detected = 'cyc' if '_cyc' in basename else \
                   'cts' if '_cts' in basename else 'cyc'
        if '_cyc' not in basename and '_cts' not in basename:
            log(f"  ⚠️ 파일명에서 cyc/cts 구분 불가 → cyc로 처리")

        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, encoding='cp949')

        log(f"  ├── 파일      : {os.path.basename(csv_path)}")
        log(f"  ├── 감지 소스 : {detected.upper()}")
        log(f"  └── 로드 완료 : {len(df)}행 × {len(df.columns)}컬럼")

        return (df, None) if detected == 'cyc' else (None, df)


# ══════════════════════════════════════════════════════════════
# 채널 선택 다이얼로그
# ══════════════════════════════════════════════════════════════
class ChannelDialog(QDialog):
    def __init__(self, channels, selected, font_family, parent=None):
        super().__init__(parent)
        self.setWindowTitle("채널 선택")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        lbl = QLabel("표시할 채널을 선택하세요:")
        lbl.setFont(QFont(font_family, 10, QFont.Weight.Bold))
        layout.addWidget(lbl)

        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont(font_family, 10))
        for ch in channels:
            item = QListWidgetItem(f"CH{int(ch):03d}")
            item.setData(Qt.ItemDataRole.UserRole, ch)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if ch in selected else Qt.CheckState.Unchecked
            )
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        btn_row  = QHBoxLayout()
        btn_all  = QPushButton("전체 선택")
        btn_none = QPushButton("전체 해제")
        btn_all.clicked.connect(self._select_all)
        btn_none.clicked.connect(self._select_none)
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        layout.addLayout(btn_row)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def _select_none(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def get_selected(self):
        result = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(item.data(Qt.ItemDataRole.UserRole))
        return result


# ══════════════════════════════════════════════════════════════
# 메인 UI
# ══════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("충방전 Data Processing Tool")
        self.setMinimumSize(1050, 920)
        self._settings          = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._all_channels      = []
        self._selected_channels = []
        self._load_lg_font()
        self._build_ui()
        self._apply_style()
        self._load_recent_paths()

    def _load_lg_font(self):
        self.lg_font_family = "Segoe UI"
        if os.path.exists(LG_FONT_PATH):
            font_id = QFontDatabase.addApplicationFont(LG_FONT_PATH)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    self.lg_font_family = families[0]

    # ══════════════════════════════════════════════════════════
    # UI 빌드
    # ══════════════════════════════════════════════════════════
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central_widget")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        root.addWidget(self._build_header())

        color_bar = QWidget()
        color_bar.setObjectName("color_bar")
        color_bar.setFixedHeight(4)
        root.addWidget(color_bar)

        body = QWidget()
        body.setObjectName("body_widget")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 12, 16, 12)
        body_layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setObjectName("main_splitter")

        top_widget = QWidget()
        top_widget.setObjectName("top_widget")
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        # [행1] 공정 선택 + 실행 모드
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(self._build_process_group(), stretch=1)
        row1.addWidget(self._build_mode_group(),    stretch=1)
        top_layout.addLayout(row1)

        # [행2] 파일 선택 + 그래프 설정
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(self._build_file_group(),  stretch=3)
        row2.addWidget(self._build_graph_group(), stretch=2)
        top_layout.addLayout(row2)

        # [행3] 설정 요약
        top_layout.addWidget(self._build_summary_group())

        splitter.addWidget(top_widget)
        splitter.addWidget(self._build_log_group())
        splitter.setSizes([580, 260])

        body_layout.addWidget(splitter)
        body_layout.addWidget(self._build_progress_section())
        body_layout.addLayout(self._build_btn_layout())

        root.addWidget(body)

    # ── 헤더 ───────────────────────────────────────────────────
    def _build_header(self):
        header = QWidget()
        header.setObjectName("header_widget")
        header.setFixedHeight(85)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 6, 20, 6)
        layout.setSpacing(0)

        left = QVBoxLayout()
        left.setSpacing(2)

        self.logo_label = QLabel()
        self.logo_label.setFixedSize(155, 42)
        self.logo_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        if os.path.exists(LG_LOGO_PATH):
            px = QPixmap(LG_LOGO_PATH).scaled(
                155, 42,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(px)
        else:
            self.logo_label.setText("LG Energy Solution")
            self.logo_label.setFont(
                QFont(self.lg_font_family, 10, QFont.Weight.Bold)
            )
            self.logo_label.setStyleSheet(
                "color:#A50034;background:transparent;"
            )
        left.addWidget(self.logo_label)

        created = QLabel("Created by 소듐이온전지PJT, 2026")
        created.setObjectName("created_label")
        created.setFont(QFont(self.lg_font_family, 7, QFont.Weight.Bold))
        left.addWidget(created)
        left.addStretch()
        layout.addLayout(left)

        title = QLabel("충방전 Data Processing Tool")
        title.setFont(QFont(self.lg_font_family, 25, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("title_label")
        layout.addWidget(title, stretch=1)

        right = QVBoxLayout()
        right.setSpacing(2)

        ver = QLabel("Tool version : v0.1")
        ver.setObjectName("version_label")
        ver.setFont(QFont(self.lg_font_family, 8, QFont.Weight.Bold))
        ver.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(ver)

        contact = QLabel(
            "Tool 관련 문의 : 소듐이온전지PJT 박상우 책임\n"
            "(tablrain@lgensol.com)"
        )
        contact.setObjectName("contact_label")
        contact.setFont(QFont(self.lg_font_family, 7, QFont.Weight.Bold))
        contact.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(contact)
        right.addStretch()

        rw = QWidget()
        rw.setFixedWidth(210)
        rw.setObjectName("right_widget")
        rw.setLayout(right)
        layout.addWidget(rw)

        return header

    # ── 공정 선택 ──────────────────────────────────────────────
    def _build_process_group(self):
        grp    = QGroupBox("공정 선택")
        layout = QHBoxLayout(grp)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)
        layout.addWidget(QLabel("공정 :"))

        self.process_combo = QComboBox()
        self.process_combo.addItem("Formation")
        for p in ["RPT", "CCA", "Cycle", "Storage", "CP"]:
            self.process_combo.addItem(f"{p}  (준비 중)")
        for i in range(1, self.process_combo.count()):
            self.process_combo.model().item(i).setEnabled(False)
        self.process_combo.setFixedWidth(180)

        # ★ 2. 위젯 직접 스타일 → Fusion 오버라이드
        self.process_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #FFFFFF;
                border: 2px solid #CCCCCC;
                border-radius: 6px;
                padding: 4px 8px;
                color: #1A1A1A;
                font-family: '{self.lg_font_family}';
                font-weight: bold;
                font-size: 11pt;
            }}
            QComboBox:hover {{ border: 2px solid #4BBDCF; }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid #EEEEEE;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #F5F5F5;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0; height: 0;
                border-style: solid;
                border-left:   6px solid transparent;
                border-right:  6px solid transparent;
                border-top:    8px solid #4BBDCF;
                border-bottom: 0px;
                margin: auto;
            }}
            QComboBox QAbstractItemView {{
                background-color: #FFFFFF;
                color: #1A1A1A;
                border: 2px solid #4BBDCF;
                border-radius: 4px;
                selection-background-color: #D0F0F5;
                selection-color: #1A1A1A;
                font-family: '{self.lg_font_family}';
                font-weight: bold;
                font-size: 11pt;
                outline: none;
            }}
        """)
        layout.addWidget(self.process_combo)
        layout.addStretch()
        return grp

    # ── 실행 모드 ──────────────────────────────────────────────
    def _build_mode_group(self):
        grp    = QGroupBox("실행 모드")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)

        self.chk_parsing = QCheckBox(
            "Parsing 모드  (.cyc / .cts / .sch → 파싱 → Origin → PPT)"
        )
        self.chk_csv = QCheckBox(
            "CSV 모드  (기존 파싱 결과 CSV → Origin → PPT)"
        )
        self.chk_parsing.setChecked(True)
        self.chk_parsing.stateChanged.connect(self._on_parsing_checked)
        self.chk_csv.stateChanged.connect(self._on_csv_checked)
        layout.addWidget(self.chk_parsing)
        layout.addWidget(self.chk_csv)
        return grp

    # ── 파일 선택 ──────────────────────────────────────────────
    def _build_file_group(self):
        grp    = QGroupBox("파일 선택")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(4)

        self.stack = QStackedWidget()
        self.stack.setObjectName("main_stack")

        # Parsing 페이지
        p_page = QWidget()
        p_page.setObjectName("parsing_page")
        p_grid = QGridLayout(p_page)
        p_grid.setContentsMargins(0, 0, 0, 0)
        p_grid.setSpacing(6)
        # ★ 3. 컬럼 stretch 설정 → 버튼 공간 확보
        p_grid.setColumnStretch(0, 0)
        p_grid.setColumnStretch(1, 1)
        p_grid.setColumnStretch(2, 0)

        self._parsing_edits = {}
        for r, (lbl_txt, key, is_file, filt) in enumerate([
            ("원시 데이터 폴더\n(.cyc/.cts/.sch):", "raw_dir",    False, ""),
            ("출력 폴더\n(CSV/OPJU/PPT):",          "output_dir", False, ""),
            ("PPT 템플릿\n(비우면 빈 PPT):",         "template",   True,
             "PowerPoint 파일 (*.pptx)"),
        ]):
            lbl = QLabel(lbl_txt)
            lbl.setWordWrap(True)
            lbl.setFixedWidth(145)
            p_grid.addWidget(lbl, r, 0)
            edit = QLineEdit()
            edit.setPlaceholderText("경로 선택...")
            edit.textChanged.connect(self._on_path_changed)
            self._parsing_edits[key] = edit
            p_grid.addWidget(edit, r, 1)
            btn = QPushButton("찾아보기")
            # ★ 3. 버튼 최소 너비로 텍스트 짤림 방지
            btn.setMinimumWidth(85)
            btn.setSizePolicy(
                btn.sizePolicy().horizontalPolicy(),
                btn.sizePolicy().verticalPolicy()
            )
            if is_file:
                btn.clicked.connect(
                    lambda _, e=edit, f=filt: self._browse_file(e, f)
                )
            else:
                btn.clicked.connect(lambda _, e=edit: self._browse_dir(e))
            p_grid.addWidget(btn, r, 2)
        self.stack.addWidget(p_page)

        # CSV 페이지
        c_page = QWidget()
        c_page.setObjectName("csv_page")
        c_grid = QGridLayout(c_page)
        c_grid.setContentsMargins(0, 0, 0, 0)
        c_grid.setSpacing(6)
        c_grid.setColumnStretch(0, 0)
        c_grid.setColumnStretch(1, 1)
        c_grid.setColumnStretch(2, 0)

        self._csv_edits = {}
        for r, (lbl_txt, key, is_file, filt) in enumerate([
            ("CSV 파일\n(_cyc/_cts 자동 인식):", "csv_path",   True,
             "CSV 파일 (*.csv)"),
            ("출력 폴더\n(OPJU/PPT):",           "output_dir", False, ""),
            ("PPT 템플릿\n(비우면 빈 PPT):",      "template",   True,
             "PowerPoint 파일 (*.pptx)"),
        ]):
            lbl = QLabel(lbl_txt)
            lbl.setWordWrap(True)
            lbl.setFixedWidth(145)
            c_grid.addWidget(lbl, r, 0)
            edit = QLineEdit()
            edit.setPlaceholderText("경로 선택...")
            edit.textChanged.connect(self._on_path_changed)
            self._csv_edits[key] = edit
            c_grid.addWidget(edit, r, 1)
            btn = QPushButton("찾아보기")
            btn.setMinimumWidth(85)
            if is_file:
                btn.clicked.connect(
                    lambda _, e=edit, f=filt: self._browse_file(e, f)
                )
            else:
                btn.clicked.connect(lambda _, e=edit: self._browse_dir(e))
            c_grid.addWidget(btn, r, 2)
        self.stack.addWidget(c_page)

        layout.addWidget(self.stack)
        return grp

    # ── 그래프 설정 ────────────────────────────────────────────
    def _build_graph_group(self):
        grp    = QGroupBox("그래프 설정")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        step_box  = QGroupBox("Step Type")
        step_vbox = QVBoxLayout(step_box)
        step_vbox.setContentsMargins(8, 4, 8, 4)
        step_vbox.setSpacing(4)
        self.chk_charge    = QCheckBox("Charge")
        self.chk_discharge = QCheckBox("Discharge")
        self.chk_charge.setChecked(True)
        self.chk_discharge.setChecked(True)
        self.chk_charge.stateChanged.connect(self._update_summary)
        self.chk_discharge.stateChanged.connect(self._update_summary)
        step_vbox.addWidget(self.chk_charge)
        step_vbox.addWidget(self.chk_discharge)
        layout.addWidget(step_box)

        cycle_box  = QGroupBox("사이클 번호")
        cycle_vbox = QVBoxLayout(cycle_box)
        cycle_vbox.setContentsMargins(8, 4, 8, 4)
        cycle_vbox.setSpacing(4)
        cycle_vbox.addWidget(QLabel("예) 1, 10, 50, 100"))
        self.cycle_edit = QLineEdit()
        self.cycle_edit.setPlaceholderText("예: 1, 10, 50")
        self.cycle_edit.setText("1")
        self.cycle_edit.textChanged.connect(self._update_summary)
        cycle_vbox.addWidget(self.cycle_edit)
        layout.addWidget(cycle_box)

        ch_box    = QGroupBox("채널 선택")
        ch_layout = QVBoxLayout(ch_box)
        ch_layout.setContentsMargins(8, 4, 8, 4)
        ch_layout.setSpacing(4)
        self.ch_status_label = QLabel("경로 선택 후 자동 감지")
        self.ch_status_label.setObjectName("ch_status")
        self.ch_status_label.setWordWrap(True)
        ch_layout.addWidget(self.ch_status_label)
        self.btn_ch_select = QPushButton("채널 선택...")
        self.btn_ch_select.setEnabled(False)
        self.btn_ch_select.clicked.connect(self._open_channel_dialog)
        ch_layout.addWidget(self.btn_ch_select)
        layout.addWidget(ch_box)

        layout.addStretch()
        return grp

    # ── 설정 요약 ──────────────────────────────────────────────
    def _build_summary_group(self):
        grp    = QGroupBox("실행 설정 요약")
        layout = QGridLayout(grp)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)

        self._summary_vals = {}
        items = [
            ("공정",       "process"),
            ("실행 모드",  "mode"),
            ("Step Type", "step_types"),
            ("사이클",     "cycle_nos"),
            ("채널",       "channels"),
            ("출력 경로",  "output_dir"),
            ("PPT 템플릿", "template"),
        ]

        # ★ 4. 좌/우 두 열로 배치, 라벨 너비 + stretch 조정
        mid = (len(items) + 1) // 2  # 4

        for i, (label, key) in enumerate(items):
            col_base = (i // mid) * 3  # 0 or 3
            row      = i % mid

            lbl = QLabel(f"{label} :")
            lbl.setObjectName("summary_key")
            lbl.setFixedWidth(90)            # ★ 90으로 확보
            layout.addWidget(lbl, row, col_base)

            val = QLabel("-")
            val.setObjectName("summary_val")
            val.setWordWrap(True)
            val.setMinimumWidth(100)         # ★ 최소 너비 확보
            self._summary_vals[key] = val
            layout.addWidget(val, row, col_base + 1)

        # 중앙 구분선
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setObjectName("summary_divider")
        layout.addWidget(line, 0, 2, mid, 1)

        # ★ 컬럼 stretch: 값 라벨이 충분히 늘어나도록
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 0)
        layout.setColumnStretch(3, 0)
        layout.setColumnStretch(4, 1)

        return grp

    # ── 로그 ───────────────────────────────────────────────────
    def _build_log_group(self):
        grp    = QGroupBox("실행 로그")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        hist_row = QHBoxLayout()
        hist_lbl = QLabel("최근 실행 이력:")
        hist_lbl.setStyleSheet("color: #000000; background: transparent;")  # ← 직접 지정 추가
        hist_row.addWidget(hist_lbl)
        hist_row.addStretch()
        self.btn_history = QPushButton("이력 보기")
        self.btn_history.setObjectName("btn_history")
        self.btn_history.setFixedHeight(26)
        self.btn_history.setStyleSheet("text-align: center;")
        self.btn_history.clicked.connect(self._show_history)
        hist_row.addWidget(self.btn_history)
        layout.addLayout(hist_row)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFont(QFont("Consolas", 9))

        # QSS color 속성이 viewport에 전달 안 되는 케이스 대응 → API로 직접 고정
        self.log_edit.setStyleSheet("")  # 이 위젯만 QSS 영향 제거
        self.log_edit.viewport().setStyleSheet(
            "background-color: #1A1A2E;"
        )
        pal = self.log_edit.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor("#1A1A2E"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#FFFFFF"))
        self.log_edit.setPalette(pal)

        layout.addWidget(self.log_edit)
        return grp

    # ── 진행 바 섹션 ───────────────────────────────────────────
    def _build_progress_section(self):
        widget = QWidget()
        widget.setObjectName("progress_widget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(3)

        self.stage_label = QLabel("")
        self.stage_label.setObjectName("stage_label")
        self.stage_label.setFont(
            QFont(self.lg_font_family, 9, QFont.Weight.Bold)
        )
        layout.addWidget(self.stage_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        layout.addWidget(self.progress_bar)

        return widget

    # ── 버튼 레이아웃 ──────────────────────────────────────────
    def _build_btn_layout(self):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.btn_clear = QPushButton("로그 지우기")
        self.btn_clear.setFixedHeight(38)
        self.btn_clear.setObjectName("btn_clear")
        self.btn_clear.clicked.connect(self.log_edit.clear)
        layout.addWidget(self.btn_clear)

        layout.addStretch()

        self.btn_stop = QPushButton("■  중단")
        self.btn_stop.setFixedHeight(38)
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)
        layout.addWidget(self.btn_stop)

        self.btn_run = QPushButton("▶  실행")
        self.btn_run.setFixedHeight(38)
        self.btn_run.setFont(QFont(self.lg_font_family, 11, QFont.Weight.Bold))
        self.btn_run.setObjectName("btn_run")
        self.btn_run.clicked.connect(self._run)
        layout.addWidget(self.btn_run)

        return layout

    # ══════════════════════════════════════════════════════════
    # 스타일
    # ══════════════════════════════════════════════════════════
    def _apply_style(self):
        BASE  = 11
        TITLE = 15

        BG    = "#F0F4F7"   # 전체 배경
        CARD  = "#F0F4F7"   # ★ 1. GroupBox 배경 = 전체 배경 (하얀 배경 제거)

        self.setStyleSheet(f"""
            * {{
                font-family: '{self.lg_font_family}';
                font-weight: bold;
                font-size: {BASE}pt;
            }}
            QMainWindow            {{ background-color: {BG}; }}
            QWidget#central_widget {{ background-color: {BG}; }}
            QWidget#body_widget    {{ background-color: {BG}; }}
            QWidget#top_widget     {{ background-color: transparent; }}
            QWidget#progress_widget {{ background-color: transparent; }}

            QWidget#header_widget {{
                background-color: #FFFFFF;
            }}
            QWidget#color_bar  {{ background-color: #4BBDCF; }}
            QWidget#right_widget {{ background-color: transparent; border: none; }}

            QLabel#title_label   {{ color:#1A1A1A; background:transparent; border:none; }}
            QLabel#created_label {{ color:#999999; background:transparent; font-size:7pt; }}
            QLabel#version_label {{ color:#4BBDCF; background:transparent; font-size:8pt; }}
            QLabel#contact_label {{ color:#999999; background:transparent; font-size:7pt; }}
            QLabel#stage_label   {{ color:#4BBDCF; background:transparent; }}
            QLabel#ch_status     {{ color:#888888; background:transparent; font-size:{BASE-1}pt; }}

            QLabel#summary_key {{
                color: #777777;
                background: transparent;
                font-size: {BASE-1}pt;
            }}
            QLabel#summary_val {{
                color: #1A1A1A;
                background: transparent;
                font-size: {BASE-1}pt;
            }}

            /* ★ 1. GroupBox: 배경을 전체 배경색과 동일하게 → 하얀 박스 사라짐 */
            QGroupBox {{
                border: 2px solid #4BBDCF;
                border-radius: 8px;
                margin-top: 12px;
                padding: 6px;
                color: #1A1A1A;
                background-color: {CARD};
                font-size: {BASE}pt;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #4BBDCF;
                font-size: {TITLE}pt;
                background-color: {CARD};
            }}
            QGroupBox QWidget {{ background-color: transparent; }}

            /* 내부 중첩 GroupBox */
            QGroupBox QGroupBox {{
                background-color: {CARD};
                border: 1px solid #C8E8EE;
                border-radius: 6px;
                margin-top: 8px;
            }}
            QGroupBox QGroupBox::title {{
                color: #4BBDCF;
                font-size: {BASE+1}pt;
                background-color: {CARD};
            }}

            QFrame#summary_divider {{
                color: #CCCCCC;
                background-color: #CCCCCC;
            }}

            QLineEdit {{
                background-color: #FFFFFF;
                border: 1px solid #DDDDDD;
                border-radius: 5px;
                padding: 4px 8px;
                color: #1A1A1A;
                font-size: {BASE}pt;
            }}
            QLineEdit:focus {{
                border: 2px solid #4BBDCF;
                background-color: #FFFFFF;
            }}

            QPushButton {{
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 3px 12px;
                color: #1A1A1A;
                font-size: {BASE}pt;
            }}
            QPushButton:hover {{
                background-color: #D0F0F5;
                border-color: #4BBDCF;
            }}
            QPushButton:pressed {{ background-color: #B0E0EA; }}
            QPushButton:disabled {{
                background-color: #F0F0F0;
                color: #BBBBBB;
                border-color: #DDDDDD;
            }}

            QPushButton#btn_run {{
                background-color: #4BBDCF;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                padding: 5px 24px;
                font-size: {BASE}pt;
            }}
            QPushButton#btn_run:hover    {{ background-color: #35A8BC; }}
            QPushButton#btn_run:disabled {{ background-color:#CCCCCC; color:#888888; }}

            QPushButton#btn_stop {{
                background-color: #FFFFFF;
                border: 1px solid #CC3333;
                border-radius: 5px;
                color: #CC3333;
                padding: 5px 18px;
            }}
            QPushButton#btn_stop:hover    {{ background-color: #FFE8E8; }}
            QPushButton#btn_stop:disabled {{ border-color:#CCCCCC; color:#AAAAAA; }}

            QPushButton#btn_clear {{
                border: 1px solid #AAAAAA;
                color: #666666;
            }}
            QPushButton#btn_history {{
                border: 1px solid #4BBDCF;
                color: #4BBDCF;
                background-color: transparent;
                font-size: {BASE-2}pt;
                padding: 2px 8px;
            }}
            QPushButton#btn_history:hover {{ background-color: #D0F0F5; }}

            QTextEdit {{
                background-color: #1A1A2E;
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                color: #E8E8E8;
                font-family: 'Consolas';
                font-size: 9pt;
                font-weight: normal;
            }}

            QProgressBar {{
                background-color: #E0E0E0;
                border: none;
                border-radius: 5px;
                text-align: center;
                font-size: 8pt;
                color: #1A1A1A;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4BBDCF, stop:1 #35A8BC
                );
                border-radius: 5px;
            }}

            QCheckBox {{
                color: #1A1A1A;
                font-size: {BASE}pt;
                spacing: 8px;
                background-color: transparent;
            }}
            QCheckBox::indicator {{
                width: 20px; height: 20px;
                border: 2px solid #CCCCCC;
                border-radius: 4px;
                background-color: #FFFFFF;
            }}
            QCheckBox::indicator:hover  {{ border: 2px solid #4BBDCF; }}
            QCheckBox::indicator:checked {{
                background-color: qradialgradient(
                    cx:0.5, cy:0.5, radius:0.38, fx:0.5, fy:0.5,
                    stop:0 #4BBDCF, stop:0.38 #4BBDCF,
                    stop:0.39 #FFFFFF, stop:1 #FFFFFF
                );
                border: 2px solid #4BBDCF;
            }}

            QSplitter::handle {{ background-color: #DDDDDD; height: 1px; }}
            QLabel {{ color:#1A1A1A; background-color:transparent; }}
            QStackedWidget {{ background-color: transparent; }}
            QStackedWidget > QWidget {{ background-color: transparent; }}

            QListWidget {{
                border: 1px solid #DDDDDD;
                border-radius: 5px;
                background-color: #FFFFFF;
                font-size: {BASE}pt;
            }}
            QListWidget::item {{ padding: 4px; }}
            QListWidget::item:selected {{
                background-color: #D0F0F5;
                color: #1A1A1A;
            }}
        """)
        self._update_summary()

    # ══════════════════════════════════════════════════════════
    # 이벤트 핸들러
    # ══════════════════════════════════════════════════════════

    def _on_parsing_checked(self, state):
        if state == Qt.CheckState.Checked.value:
            self.chk_csv.blockSignals(True)
            self.chk_csv.setChecked(False)
            self.chk_csv.blockSignals(False)
            self.stack.setCurrentIndex(0)
        else:
            if not self.chk_csv.isChecked():
                self.chk_parsing.blockSignals(True)
                self.chk_parsing.setChecked(True)
                self.chk_parsing.blockSignals(False)
        self._update_summary()

    def _on_csv_checked(self, state):
        if state == Qt.CheckState.Checked.value:
            self.chk_parsing.blockSignals(True)
            self.chk_parsing.setChecked(False)
            self.chk_parsing.blockSignals(False)
            self.stack.setCurrentIndex(1)
        else:
            if not self.chk_parsing.isChecked():
                self.chk_csv.blockSignals(True)
                self.chk_csv.setChecked(True)
                self.chk_csv.blockSignals(False)
        self._update_summary()

    def _on_path_changed(self):
        self._update_summary()
        self._try_detect_channels()

    def _try_detect_channels(self):
        import pandas as pd
        mode     = 'parsing' if self.chk_parsing.isChecked() else 'csv'
        csv_path = ""

        if mode == 'csv':
            csv_path = self._csv_edits['csv_path'].text().strip()
        else:
            out_dir = self._parsing_edits['output_dir'].text().strip()
            if out_dir and os.path.exists(out_dir):
                for f in os.listdir(out_dir):
                    if '_combined_cyc.csv' in f:
                        csv_path = os.path.join(out_dir, f)
                        break

        if not csv_path or not os.path.exists(csv_path):
            self.ch_status_label.setText("경로 선택 후 자동 감지")
            self.btn_ch_select.setEnabled(False)
            return

        try:
            df       = pd.read_csv(csv_path, usecols=['chNo'], encoding='utf-8-sig')
            channels = sorted(df['chNo'].dropna().unique().tolist())
            self._all_channels = channels
            if not self._selected_channels:
                self._selected_channels = channels[:]
            self.ch_status_label.setText(
                f"감지된 채널: {len(channels)}개  |  "
                f"선택: {len(self._selected_channels)}개"
            )
            self.btn_ch_select.setEnabled(True)
            self._update_summary()
        except Exception:
            self.ch_status_label.setText("채널 감지 실패")
            self.btn_ch_select.setEnabled(False)

    def _open_channel_dialog(self):
        dlg = ChannelDialog(
            self._all_channels,
            self._selected_channels,
            self.lg_font_family,
            self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._selected_channels = dlg.get_selected()
            self.ch_status_label.setText(
                f"감지된 채널: {len(self._all_channels)}개  |  "
                f"선택: {len(self._selected_channels)}개"
            )
            self._update_summary()

    def _update_summary(self):
        mode = 'Parsing 모드' if self.chk_parsing.isChecked() else 'CSV 모드'
        if self.chk_parsing.isChecked():
            out  = self._parsing_edits['output_dir'].text().strip() or '-'
            tmpl = self._parsing_edits['template'].text().strip() or '없음'
        else:
            out  = self._csv_edits['output_dir'].text().strip() or '-'
            tmpl = self._csv_edits['template'].text().strip() or '없음'

        ch_txt = (
            f"{len(self._selected_channels)} / {len(self._all_channels)}개"
            if self._all_channels else "자동 (전체)"
        )

        self._summary_vals['process'].setText(self._get_process())
        self._summary_vals['mode'].setText(mode)
        self._summary_vals['step_types'].setText(
            ', '.join(self._get_step_types()) or '-'
        )
        self._summary_vals['cycle_nos'].setText(
            ', '.join(map(str, self._parse_cycle_nos()))
        )
        self._summary_vals['channels'].setText(ch_txt)
        self._summary_vals['output_dir'].setText(
            os.path.basename(out) if out != '-' else '-'
        )
        self._summary_vals['template'].setText(
            os.path.basename(tmpl) if tmpl != '없음' else '없음'
        )

    def _show_history(self):
        records = HistoryManager.load()
        dlg     = QDialog(self)
        dlg.setWindowTitle("실행 이력")
        dlg.setMinimumSize(520, 360)
        layout = QVBoxLayout(dlg)

        if not records:
            layout.addWidget(QLabel("실행 이력이 없습니다."))
        else:
            lw = QListWidget()
            lw.setFont(QFont("Consolas", 9))
            for r in reversed(records):
                text = (
                    f"[{r.get('datetime','')}]  "
                    f"{r.get('process','')}  |  "
                    f"{r.get('mode','')}  |  "
                    f"출력: {os.path.basename(r.get('output_dir',''))}"
                )
                lw.addItem(QListWidgetItem(text))
            layout.addWidget(lw)

        btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn.rejected.connect(dlg.reject)
        layout.addWidget(btn)
        dlg.exec()

    # ── 경로 기억 ──────────────────────────────────────────────
    def _load_recent_paths(self):
        for key in ['raw_dir', 'output_dir', 'template']:
            val = self._settings.value(f"parsing/{key}", "")
            if val:
                self._parsing_edits[key].setText(val)
        for key in ['csv_path', 'output_dir', 'template']:
            val = self._settings.value(f"csv/{key}", "")
            if val:
                self._csv_edits[key].setText(val)
        if self._settings.value("mode", "parsing") == 'csv':
            self.chk_csv.setChecked(True)

    def _save_recent_paths(self):
        for key, edit in self._parsing_edits.items():
            self._settings.setValue(f"parsing/{key}", edit.text())
        for key, edit in self._csv_edits.items():
            self._settings.setValue(f"csv/{key}", edit.text())
        mode = 'parsing' if self.chk_parsing.isChecked() else 'csv'
        self._settings.setValue("mode", mode)

    def closeEvent(self, event):
        self._save_recent_paths()
        super().closeEvent(event)

    # ── 유틸 ───────────────────────────────────────────────────
    def _browse_dir(self, edit):
        path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if path:
            edit.setText(path)

    def _browse_file(self, edit, filt):
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", filt)
        if path:
            edit.setText(path)

    def _log(self, msg):
        cursor = self.log_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = cursor.charFormat()
        fmt.setForeground(QColor("#FFFFFF"))
        cursor.setCharFormat(fmt)
        cursor.insertText(msg + "\n")
        self.log_edit.setTextCursor(cursor)
        self.log_edit.moveCursor(QTextCursor.MoveOperation.End)

    def _on_stage(self, stage_name, pct):
        self.stage_label.setText(stage_name)
        self.progress_bar.setValue(pct)

    def _parse_cycle_nos(self):
        result = []
        for part in self.cycle_edit.text().strip().split(','):
            part = part.strip()
            if part.isdigit():
                result.append(int(part))
        return result if result else [1]

    def _get_step_types(self):
        types = []
        if self.chk_charge.isChecked():
            types.append('CHARGE')
        if self.chk_discharge.isChecked():
            types.append('DISCHARGE')
        return types if types else ['CHARGE', 'DISCHARGE']

    def _get_process(self):
        return self.process_combo.currentText().split("  ")[0]

    def _stop(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self._log("⛔ 사용자에 의해 중단됐습니다.")
            self.btn_run.setEnabled(True)
            self.btn_run.setText("▶  실행")
            self.btn_stop.setEnabled(False)
            self.stage_label.setText("중단됨")

    def _run(self):
        mode = 'parsing' if self.chk_parsing.isChecked() else 'csv'

        if mode == 'parsing':
            if not self._parsing_edits['raw_dir'].text().strip():
                self._log("❌ 원시 데이터 폴더를 선택해주세요.")
                return
            if not self._parsing_edits['output_dir'].text().strip():
                self._log("❌ 출력 폴더를 선택해주세요.")
                return
            output_dir = self._parsing_edits['output_dir'].text().strip()
            template   = self._parsing_edits['template'].text().strip() or None
            csv_path   = ""
            raw_dir    = self._parsing_edits['raw_dir'].text().strip()
        else:
            if not self._csv_edits['csv_path'].text().strip():
                self._log("❌ CSV 파일을 선택해주세요.")
                return
            if not self._csv_edits['output_dir'].text().strip():
                self._log("❌ 출력 폴더를 선택해주세요.")
                return
            output_dir = self._csv_edits['output_dir'].text().strip()
            template   = self._csv_edits['template'].text().strip() or None
            csv_path   = self._csv_edits['csv_path'].text().strip()
            raw_dir    = ""

        config = {
            'mode'             : mode,
            'process'          : self._get_process(),
            'raw_dir'          : raw_dir,
            'csv_path'         : csv_path,
            'output_dir'       : output_dir,
            'template'         : template,
            'step_types'       : self._get_step_types(),
            'cycle_nos'        : self._parse_cycle_nos(),
            'selected_channels': self._selected_channels or [],
        }

        os.makedirs(output_dir, exist_ok=True)
        self._save_recent_paths()

        self.btn_run.setEnabled(False)
        self.btn_run.setText("실행 중...")
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)
        self.stage_label.setText("시작 중...")
        self.log_edit.clear()

        self.worker = Worker(config)
        self.worker.signals.log.connect(self._log)
        self.worker.signals.stage.connect(self._on_stage)
        self.worker.signals.done.connect(self._on_done)
        self.worker.start()

    def _on_done(self, success):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶  실행")
        self.btn_stop.setEnabled(False)
        if success:
            self.progress_bar.setValue(100)
            self.stage_label.setText("✅ 완료")
            self._log("✅ 모든 작업 완료!")
        else:
            self.stage_label.setText("❌ 오류 발생")
            self._log("❌ 작업 중 오류 발생. 로그를 확인해주세요.")

# ══════════════════════════════════════════════════════════════
# 진입점
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())