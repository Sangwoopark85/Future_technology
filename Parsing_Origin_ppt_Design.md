# 충방전 Data Processing Tool — 설계 문서

> 대상 파일: `Parsing_01.py`, `Origin_ppt_pipeline_02.py`, `Main_ui_03.py`
> 작성 기준: 2026-06-22 시점 코드

---

## 1. 전체 개요

이 도구는 PNE Solution 충방전기에서 나오는 바이너리 원시 파일(`.cyc`, `.cts`, `.sch`)을 파싱하여, OriginLab으로 그래프를 생성하고, 그 그래프를 PowerPoint 보고서에 자동으로 삽입하는 일련의 파이프라인을 PySide6 GUI로 감싼 프로그램이다.

### 1.1 전체 데이터 흐름

```
[원시 데이터]                    [파싱 단계]              [그래프/보고서 단계]
.cyc/.cts/.sch 파일들    →    Parsing_01.py        →    Origin_ppt_pipeline_02.py
(PNE 충방전기 출력)            (바이너리 → DataFrame)      (DataFrame → Origin 그래프
                                                            → PPT 삽입)
                                      ↑                            ↑
                                      └──────── Main_ui_03.py ──────┘
                                          (PySide6 GUI, 두 모듈을
                                           오케스트레이션하는 진입점)
```

세 파일의 역할은 명확히 분리되어 있다.

| 파일 | 책임 | 의존 관계 |
|---|---|---|
| `Parsing_01.py` | 바이너리 파일 탐색 + 파싱 + 전처리 | 독립적 (pandas, struct, sqlite3) |
| `Origin_ppt_pipeline_02.py` | DataFrame → Origin 그래프 → PPT 삽입 | 독립적 (win32com, matplotlib) |
| `Main_ui_03.py` | GUI, 사용자 입력 수집, 위 두 모듈 호출 | 위 두 모듈을 런타임에 import |

`Main_ui_03.py`는 두 모듈을 직접 import하지 않고, `Worker.run()` 내부에서 **지연 import**(lazy import)로 불러온다. 이는 GUI 시작 속도를 빠르게 하고, 무거운 의존성(pandas, win32com)을 실제 작업 시작 시점에만 로드하기 위한 설계다.

---

## 2. Parsing_01.py — 바이너리 파일 파서

### 2.1 책임

PNE Solution 충방전기가 만드는 세 종류의 바이너리 파일을 파싱하여 pandas DataFrame으로 변환한다.

| 파일 확장자 | 내용 | 파서 클래스 |
|---|---|---|
| `.cyc` | 전체 사이클 데이터 (모든 레코드, 시계열) | `CycParser` |
| `.cts` | Step 종료 시점 데이터 (StepEnd 레코드 단위) | `CtsParser` |
| `.sch` | 스케줄/스텝 조건 설정 (전압/전류 제한, 종료 조건 등) | `SchParser` |

### 2.2 클래스 구조

```
File_search
  └─ 폴더를 재귀 탐색하여 .cyc/.cts/.sch 3종 세트를 찾아 페어링

Version
  └─ 파일 버전(16개 버전 지원)에 따라 RECORD_ITEM_MAP을 동적으로 구성
     (버전마다 레코드 항목 ID → 컬럼명 매핑이 다름)

CycParser
  ├─ cyc_parser()           : 바이너리 → (raw_data, col_names, 메타정보)
  └─ data_preprocessing()   : raw_data → DataFrame, 단위변환/시간포맷 적용

CtsParser
  ├─ cts_parser()           : 바이너리 → (rows, stepends, col_names, 메타정보)
  ├─ parse_records()        : StepEnd + 데이터 레코드를 번갈아 읽는 루프
  ├─ get_stepend_size()     : 버전별 StepEnd 구조체 크기 반환
  ├─ build_struct_format()  : item_struct → struct 포맷 문자열
  └─ data_preprocessing()   : DataFrame 생성 + StepEnd 정보 결합 + 단위변환

SchParser
  ├─ sch_parser()                      : 전체 파일 파싱 진입점
  ├─ _parse_file_id_header()           : 파일 식별 헤더 (328 bytes)
  ├─ _parse_file_test_information()    : 테스트 메타데이터 (392 bytes × 2)
  ├─ _parse_file_cell_check_param()    : 셀 체크 파라미터 + 패딩
  ├─ _parse_file_grade()               : 등급 판정 기준 (100 bytes)
  ├─ _parse_step_common()              : 스텝 1개의 공통 필드 파싱
  ├─ _detect_step_size()               : 다음 스텝 시작 위치를 휴리스틱으로 탐지
  ├─ _parse_file_step_condition()      : 스텝 1개 전체 파싱 (위 함수들 조합)
  └─ data_preprocessing()              : 단위변환 + csvStepNo 복원

cyc_cts_sch_comb
  ├─ load_data()                : 세 파서를 모두 실행해 3개 DataFrame 획득
  ├─ calc_dqdv()                 : dQ/dV 미분값 계산 (이동평균 스무딩 포함)
  └─ comb_data_preprocessing()  : 핵심 결합 로직 (2.4절 참조)

DW_load()  — 모듈 레벨 함수, SQLite DB 적재용 (메인 파이프라인에서는 미사용)
```

### 2.3 바이너리 파싱의 핵심 패턴

세 파서 모두 다음 공통 패턴을 따른다.

1. **고정 크기 헤더를 순서대로 `struct.unpack`** — `PS_FILE_ID_HEADER`(328 bytes) 등 파일 공통 헤더를 먼저 읽는다.
2. **버전 식별 → 컬럼 맵 결정** — 헤더에서 읽은 `szFileVersion`을 `Version` 클래스에 넘겨, 그 버전에 맞는 `RECORD_ITEM_MAP`(레코드 항목 ID → 컬럼명/타입)을 가져온다. 같은 의미의 데이터라도 펌웨어 버전에 따라 레코드 구조가 달라지기 때문에 이 매핑이 필수다.
3. **동적 struct 포맷 생성** — 컬럼 수와 타입이 버전마다 다르므로, 고정된 `struct.unpack` 포맷 문자열을 쓰지 않고 `'<' + ''.join(dtype for _, dtype in item_struct)` 형태로 런타임에 조립한다.
4. **레코드를 파일 끝까지 반복 읽기** — `record_size`만큼씩 읽고, 읽은 바이트 수가 모자라면 종료.
5. **DataFrame 변환 후 전처리** — 단위 변환(`/1000`로 m단위 → 단위), 시간 포맷 변환(초 → `HH:MM:SS.xx`), 날짜 파싱(`PS_REALDATE`/`PS_REALCLOCK` 같은 정수 인코딩 날짜를 datetime으로).

### 2.4 `.cts` 파일의 특수성 — 가변 크기 StepEnd

`.cts` 파일은 다른 두 파일과 달리 **레코드 앞에 오는 메타데이터(StepEnd) 블록의 크기가 첫 번째와 그 이후가 다르다**:

- 첫 번째 StepEnd: 34 bytes
- 두 번째 이후 StepEnd: 44 bytes (REALDATE/REALCLOCK 필드가 추가됨)

`CtsParser.parse_records()`는 `first` 플래그로 이 분기를 처리하며, StepEnd에서 채널 번호·스텝 타입·사이클 번호 등 메타 정보를 추출하고 그 바로 뒤에 오는 데이터 레코드를 읽는 구조다.

### 2.5 `.sch` 파일의 특수성 — 스텝 크기 자동 탐지

`.sch` 파일의 가장 까다로운 부분은 **스텝(`FILE_STEP_CONDITION`)마다 크기가 고정되어 있지 않다**는 점이다. 공식 스펙에 고정 크기가 없어, `SchParser._detect_step_size()`는 다음 휴리스틱으로 다음 스텝의 시작 위치를 탐지한다:

```python
# 조건: 4바이트 정렬 위치에서
#   - chStepNo == 현재스텝번호 + 1
#   - chReserved[3] == 0x000000  (예약 영역이 0으로 채워짐)
#   - chType이 유효한 스텝 타입 값 중 하나
```

이 방식은 "다음 스텝이 시작될 것 같은 신호"를 찾는 패턴 매칭이며, 정형 스펙 파싱이 아니라 실측 기반 역공학 결과로 보인다. `VALID_STEP_TYPES` 집합에 없는 `chType` 값이 우연히 매칭 조건을 만족하면 오탐 가능성이 있다는 점이 구조적 제약이다.

### 2.6 세 데이터의 결합 — `comb_data_preprocessing()`

`cyc_cts_sch_comb.comb_data_preprocessing()`이 전체 파싱 파이프라인의 핵심 결합 로직이다.

```
1. cts_df ↔ sch_df 결합
   merge 키: (chStepNo, chStepType) ↔ (chStepNo, chTypeName)
   목적: cts의 각 Step에 sch에서 정의한 종료조건(fVref, fEndV 등)을 부여

2. cyc_df에 cts_df의 메타데이터를 인덱스 범위 기반으로 매핑
   - cts_df 각 행은 ulIndexFrom~ulIndexTo 범위를 가짐
   - cyc_df의 PS_DATA_SEQ(-1)가 그 범위에 속하면, 해당 cts 행의
     chNo, chStepType, ulCurrentCycleNum 등을 cyc_df에 복사
   → cyc(연속 시계열) 레벨에 cts(스텝 단위) 메타데이터를 끌어내림

3. column_rename()으로 PS_ 접두사 내부 코드명을 사용자 친화적 이름으로 변환
   (예: PS_VOLTAGE → Voltage, PS_IMPEDANCE_30S → Impedance_30s)

4. calc_dqdv()로 dQ/dV 컬럼 추가
   - (chNo, ulCurrentCycleNum, chStepType) 그룹별로 dQ/dV = diff(Capacity)/diff(Voltage)
   - rolling(window=10, center=True)로 이동평균 스무딩
```

이 단계가 끝나면 `Origin_ppt_pipeline_02.py`가 바로 사용할 수 있는 형태(컬럼명, 채널/스텝/사이클 정보가 모두 갖춰진 평탄한 DataFrame)가 완성된다.

### 2.7 알아둘 점 / 잠재 리스크

- **`__main__` 블록의 경로는 개발용 하드코딩**이다(`/project/work/temp_venv/...`). 실제 GUI 실행 경로(`Main_ui_03.py`)에서는 이 블록이 호출되지 않으므로 영향 없음.
- **버전 미지원 시 fallback** — `RECORD_ITEM_MAP`에 없는 `item_id`는 `UNKNOWN_0x{id}`라는 컬럼명으로 float 처리되어 경고만 출력하고 진행한다. 데이터 손실 없이 동작은 계속되지만, 알려지지 않은 필드의 의미는 알 수 없다.
- **`sqlite3` 의존성** — 파일 상단에 `import sqlite3`가 있으나 실제로는 `DW_load()`와 `__main__` 블록에서만 사용된다. GUI 경로(Parsing 모드)에서는 이 함수가 호출되지 않지만, **모듈 임포트 시점에 `sqlite3`가 무조건 로드**되므로, PyInstaller로 패키징할 때 `_sqlite3.pyd`가 필요로 하는 DLL이 함께 포함되어야 한다.

---

## 3. Origin_ppt_pipeline_02.py — Origin/PowerPoint 자동화 파이프라인

### 3.1 책임

파싱이 끝난 DataFrame을 받아서:
1. OriginLab을 COM으로 구동해 그래프(라인/박스플롯)를 생성
2. 그 그래프를 클립보드로 복사 → PowerPoint에 OLE 객체로 붙여넣기
3. matplotlib으로 동일한 그래프의 PNG도 백업 저장
4. 최종 `.opju`(Origin 프로젝트), `.pptx`(완성 보고서) 저장

### 3.2 설정 중심 구조 — `PROCESS_CONFIGS`

이 파일의 가장 중요한 설계 결정은 **"공정별로 어떤 그래프를 어디에 그릴지"를 코드가 아니라 딕셔너리로 선언**한 것이다.

```python
PROCESS_CONFIGS = {
    "Formation": {
        "graphs": [ {x, y, title, slide}, ... ],
        "step_types": [...], "cycle_nos": [...]
    },
    "RPT": {
        "slide_9":  {"layout": [2, 3], "graphs": [...]},
        "slide_10": {"layout": [3, 3], "graphs": [...]},
    },
}
```

새로운 공정(`CCA`, `Cycle`, `Storage`, `CP` — 현재 `Main_ui_03.py`에서 "준비 중"으로 비활성화된 항목들)을 추가할 때, 이 딕셔너리에 항목을 추가하고 그에 맞는 처리 분기를 `run_pipeline()`에 넣는 식으로 확장하도록 의도된 구조다. 현재는 `Formation`과 `RPT` 두 공정만 실제 처리 로직(`_run_formation`, `_process_rpt_slide`)을 갖고 있다.

### 3.3 그래프 생성 — Line vs Box 두 경로

| | Line 그래프 | Box 그래프 |
|---|---|---|
| 빌드 함수 | `_build_graph()` | `_build_boxplot()` |
| 워크시트 구조 | col1=X(공통), col2~=Y(채널별) | 채널마다 별도 컬럼, 값은 행으로 나열 |
| Origin 플롯 명령 | `worksheet -p 200` (자동 색상 순환) | `worksheet -p 206` (Box Chart, Y Range) |
| X축 의미 | 실제 데이터(Capacity, Voltage 등) | 채널 카테고리(CH001, CH002...) |

두 함수 모두 공통 마무리 단계(`origin.Execute("doc -uw;")`로 갱신, `layer -a`로 레이어 자동맞춤, 축 타이틀 설정)를 거친다. `worksheet -s all` + `worksheet -p {id}`로 워크시트 전체를 한 번에 플롯하는 방식은, 컬럼 하나씩 따로 그리는 대신 Origin이 자동으로 색상을 순환시키도록 하기 위한 선택이다(메모리에 기록된 "Origin COM API 색상 제어 한계" 문제의 해결책).

### 3.4 OLE 클립보드 복사의 까다로움 — `copy_graph_to_clipboard()`

이 함수는 이 파일에서 가장 깨지기 쉬운 부분이다. Origin 그래프를 OLE 객체로 PPT에 붙여넣기 위해 **`Ctrl+J`라는 Origin 전용 단축키를 키보드 이벤트로 직접 흘려보내는** 방식을 쓰고 있다.

```
순서:
1. PySide6 UI 윈도우 최소화 (포커스 경쟁 제거)
2. PowerPoint 윈도우도 최소화
3. win -a {graph_name} 으로 Origin 해당 그래프 창 활성화
4. win32gui로 포커스가 진짜 Origin인지 확인
   └─ 아니면 RuntimeError 발생 (조용히 실패하지 않도록)
5. win32api.keybd_event로 Ctrl+J 키 입력 시뮬레이션
6. PySide6 UI 윈도우 복구
```

`Execute()`로 COM 명령을 보내는 대신 실제 키보드 이벤트를 흘리는 이유는, **Origin의 OLE 클립보드 복사 기능이 COM API로는 노출되지 않고 단축키로만 트리거되기 때문**으로 보인다(이전 작업 기록에 남겨진 "OLE 삽입은 VS Code 터미널이 아니라 PySide6 UI 컨텍스트에서 실행해야 한다"는 제약과 같은 맥락 — 키보드 포커스가 의도한 창에 가 있어야만 동작).

이 설계의 트레이드오프는 명확하다.
- **장점**: PNG 변환 없이 Origin 데이터 자체가 PPT에 살아있어, 더블클릭으로 데이터 테이블 접근 가능 (요구사항상 필수 조건)
- **단점**: 타이밍(`time.sleep`)에 의존하는 취약한 자동화. 다른 창이 포커스를 가로채면 실패한다.

### 3.5 그리드 배치 — `calc_grid_positions()`

여러 그래프를 슬라이드에 격자로 배치하기 위한 순수 함수다. `layout=[2, 3]`처럼 "행마다 몇 개씩"을 받아서, 각 셀의 `(left_pt, top_pt, width_pt, height_pt)`를 cm 기준으로 계산한 뒤 pt로 변환해 반환한다.

```
파라미터 의미:
  left_margin_cm / right_margin_cm  : 슬라이드 좌/우 여백 (분리되어 있어 그리드를
                                        좌우로 이동시킬 수 있음)
  top_margin_cm / bottom_margin_cm  : 슬라이드 상/하 여백
  gap_cm     : 같은 행 안에서 그래프 사이 가로 간격
  row_gap_cm : 행과 행 사이 세로 간격

계산 순서:
  1. max_cols = layout 중 가장 칸 수가 많은 행 (셀 너비를 모든 행에 동일 적용)
  2. cell_width  = (사용가능폭 - 간격합) / max_cols
  3. cell_height = (사용가능높이 - 행간격합) / 행 개수
  4. 각 (행, 열)에 대해 left/top 좌표를 누적 계산
```

좌/우 마진을 분리해둔 것은 설계상 의도적 선택으로, 슬라이드 안에서 그리드 전체의 수평 위치를 그래프 "크기"는 건드리지 않고 옮길 수 있게 하기 위함이다(실제로 PPT 좌표계와 자(ruler) 표시 단위 차이로 그래프가 우측에 쏠려 잘리는 문제를 해결할 때 이 분리 구조가 활용됨).

### 3.6 RPT 공정의 동적 슬롯 — `_process_rpt_slide()`

RPT 공정은 슬라이드 10에 **고정 그래프 2개 + 사용자가 UI에서 선택한 컬럼 최대 4개**가 들어가는 구조다.

```python
graph_cfgs = list(slide_cfg["graphs"])          # 고정 그래프(2개)로 시작
for extra_col in selected_extra_columns:        # UI에서 받은 컬럼 리스트
    graph_cfgs.append({"type": "box", "y": extra_col, ...})
```

`selected_extra_columns`는 `Main_ui_03.py`의 드롭다운 4개에서 사용자가 고른 컬럼명 리스트로, `run_pipeline()` → `_process_rpt_slide()`까지 인자로 전달된다. 슬롯 수(`n_expected = sum(layout)`)를 넘으면 초과분을 무시하고, 모자라면 빈 칸으로 남기는 방어적 처리가 들어가 있다.

각 그래프는 `ws_prefix{idx+1}` 형식의 고유한 Origin 워크시트 이름을 받는다(`RptNine1`, `RptNine2`, ... / `RptTen1`, `RptTen2`, ...). 슬라이드 9와 10이 별도 prefix를 쓰는 이유는 같은 실행 안에서 워크시트 이름이 충돌하지 않게 하기 위함이다.

### 3.7 통합 파이프라인 — `run_pipeline()`

```
[1] 데이터 필터링      filter_data() — step_types, cycle_nos로 DataFrame 축소
[2] PowerPoint 실행    win32.Dispatch("PowerPoint.Application")
                       template 있으면 그걸 열고, 없으면 빈 PPT 생성
[3] Origin 실행        win32.Dispatch("Origin.Application")
                       origin.NewProject()로 깨끗한 프로젝트 시작
[4] 공정 분기
       Formation → _run_formation()      (그래프 2개를 슬라이드 1장에 나란히)
       RPT       → _process_rpt_slide() × 2  (슬라이드 9, 10)
                   + .opju 저장
[finally] Origin 종료 (origin.Exit(), COM 객체 명시적 release)
[마지막] PPT를 .pptx로 저장 후 Close, PowerPoint Quit
```

`try/finally`로 Origin 종료를 보장하는 점, COM 객체를 `del origin`으로 명시적으로 릴리즈하는 점은 COM 자동화에서 흔한 좀비 프로세스(작업 끝나고도 Origin.exe가 백그라운드에 남는 문제)를 막기 위한 방어 코드다.

### 3.8 Formation과 RPT의 구조적 차이

| | Formation | RPT |
|---|---|---|
| 그래프 수 | 고정 2개 | 슬라이드9: 5개, 슬라이드10: 2~6개(가변) |
| 배치 방식 | 좌우 나란히 (1행) | 그리드 (2~3행) |
| 그래프 타입 | Line만 | Line + Box 혼합 |
| 처리 함수 | `_run_formation()` (전용) | `_process_rpt_slide()` (범용, 재사용) |

Formation은 RPT보다 먼저 구현된 "원형" 구조로, 그래프를 좌우로 나란히 놓는 로직(`graph_configs_side`)이 `_run_formation()` 안에 직접 박혀있다. RPT는 이후 더 복잡한 그리드 요구사항(가변 레이아웃, 그래프 타입 혼합)을 만족시키기 위해 `_process_rpt_slide()`라는 더 범용적인 함수로 분리해서 작성된 것으로 보인다. 향후 공정이 더 추가된다면, Formation도 `_process_rpt_slide()`와 유사한 범용 함수로 통합할 여지가 있다.

### 3.9 알아둘 점 / 잠재 리스크

- **`OTPU_DIR`, `BOX_TEMPLATE_PATH`는 죽은 코드**다. 파일 상단에 선언되어 있지만 본문 어디서도 참조되지 않는다. 향후 Origin 템플릿(.otpu) 적용 기능을 위해 남겨둔 것으로 추정되며, 실제로 쓰게 되면 하드코딩된 절대경로(`C:\Users\tablrain\...`)를 배포 환경에 맞게 고쳐야 한다.
- **`time.sleep()` 의존도가 높다.** COM 호출과 키보드 이벤트 사이 동기화를 시간 지연으로 처리하고 있어, 느린 PC에서는 타이밍이 부족해 실패할 수 있고, 빠른 PC에서는 불필요하게 느릴 수 있다. 향후 개선 여지가 있는 부분.
- **matplotlib PNG는 백업용이며 PPT에는 들어가지 않는다.** `export_graph_png()`, `export_boxplot_png()`는 Origin 라이선스 문제나 OLE 실패 시를 대비한 별도 산출물로, `output_dir`에 파일로만 저장되고 실제 PPT 삽입은 항상 OLE 경로(`paste_ole_to_slide()`)를 사용한다.

---

## 4. Main_ui_03.py — PySide6 GUI

### 4.1 책임

사용자가 입력(파일 경로, 공정 종류, 채널/사이클 선택 등)을 GUI로 채우면, 이를 `config` 딕셔너리로 모아서 백그라운드 스레드(`Worker`)에 넘겨 `Parsing_01.py` + `Origin_ppt_pipeline_02.py`를 실행시키고, 진행 상황과 로그를 화면에 보여준다.

### 4.2 클래스 구조

```
HistoryManager (정적 메서드만 가짐)
  └─ run_history.json에 최근 실행 20건을 기록/조회

WorkerSignals (QObject)
  └─ log, done, stage 시그널 정의 — 스레드→UI 통신 채널

Worker (QThread)
  ├─ run()                  : 전체 실행 흐름 (파싱 → 필터 → run_pipeline)
  ├─ _run_parsing_mode()    : Parsing_01.py 호출, CSV로 캐싱 저장
  └─ _run_csv_mode()        : 이미 파싱된 CSV를 그대로 로드

ChannelDialog (QDialog)
  └─ 채널 다중 선택 팝업 (전체선택/해제 버튼 포함)

MainWindow (QMainWindow)
  ├─ _build_*()   : UI 위젯 생성 메서드들 (헤더/공정선택/파일선택/그래프설정/...)
  ├─ _apply_style() : 전체 QSS 스타일시트 적용
  ├─ _on_*()      : 이벤트 핸들러들
  ├─ _try_detect_channels()      : CSV에서 chNo 컬럼을 읽어 채널 목록 자동 감지
  ├─ _refresh_numeric_columns()  : RPT용 추가 컬럼 드롭다운 자동 채움
  └─ _run() / _stop() / _on_done() : 실행 제어
```

### 4.3 PyInstaller 배포 대응 — 경로 처리 3종 함수

파일 최상단에 있는 세 함수는 "exe로 패키징됐을 때도 리소스를 못 찾는 일이 없게" 만들기 위한 설계다.

```python
def get_base_dir():
    """실행 환경별 기준 경로
       - exe(onefile) : sys._MEIPASS (임시 압축해제 폴더)
       - exe(onedir)  : exe가 있는 폴더
       - python 직접 실행 : 이 .py 파일이 있는 폴더
    """

def resource_path(*parts):
    """get_base_dir() + 'resources' 하위 경로 — 폰트/로고 등 읽기 전용 리소스용"""

def writable_base_dir():
    """실행 이력(run_history.json) 등 '쓰기'가 필요한 파일의 기준 경로
       _MEIPASS는 임시폴더라 쓰기에 부적합하므로 exe 폴더 자체를 사용
    """
```

이 구분이 필요한 이유는 PyInstaller가 만드는 실행 환경의 특성 때문이다. `sys.frozen` 속성이 있으면(exe로 패키징된 상태) `_MEIPASS`(onefile일 때 압축이 풀리는 임시 폴더) 또는 exe가 위치한 폴더를 기준으로 삼고, 일반 `python Main_ui_03.py` 실행이면 스크립트 파일 위치를 기준으로 삼는다. **읽기 전용 리소스(폰트, 로고)와 쓰기 가능한 파일(이력)의 기준 경로를 분리**한 것이 핵심 설계 의도다.

### 4.4 Worker 스레드 — UI가 멈추지 않는 구조

`run_pipeline()` 호출은 Origin/PowerPoint COM 자동화 때문에 수 분이 걸릴 수 있다. 이를 GUI 메인 스레드에서 직접 실행하면 창이 멈춘("응답 없음") 상태가 되므로, `QThread`를 상속한 `Worker` 클래스가 별도 스레드에서 실행하고, `Signal`로 결과를 메인 스레드에 비동기 전달한다.

```
MainWindow._run()
   └─ Worker(config) 생성, 시그널 연결, .start()
         │
         ▼ (별도 스레드에서 실행)
Worker.run()
   ├─ signals.stage.emit(...)   ← 진행률 업데이트
   ├─ signals.log.emit(...)     ← 로그 한 줄씩 전송
   └─ signals.done.emit(bool)   ← 최종 성공/실패
         │
         ▼ (Qt가 자동으로 메인 스레드 슬롯 호출)
MainWindow._on_stage() / _log() / _on_done()
```

`log()` 내부 클로저가 `self.signals.log.emit(msg)`와 동시에 파일(`log.txt`)에도 같은 메시지를 쓰는 점이 눈에 띈다 — 화면에 보이는 로그와 디스크에 남는 로그가 항상 동일하게 보장된다.

### 4.5 Parsing 모드 vs CSV 모드

`Main_ui_03.py`는 같은 작업을 시작하는 두 가지 입구를 제공한다.

| | Parsing 모드 | CSV 모드 |
|---|---|---|
| 입력 | 원시 데이터 폴더(.cyc/.cts/.sch 세트) | 이미 파싱되어 저장된 CSV 1개 |
| 내부 처리 | `Parsing_01.py`를 호출해 바이너리부터 파싱 | CSV를 `pd.read_csv`로 바로 로드 |
| 부가 동작 | 파싱 결과를 CSV로 자동 저장(캐싱) | 없음 (이미 캐시를 쓰는 것이므로) |
| 적합한 상황 | 새 데이터셋을 처음 처리할 때 | 같은 데이터셋으로 그래프/PPT만 다시 만들 때 |

이 두 모드는 상호 배타적 체크박스(`chk_parsing`, `chk_csv`)로 토글되며, `_on_parsing_checked`/`_on_csv_checked`가 서로의 상태를 강제로 맞춰준다(하나를 켜면 다른 하나는 자동으로 꺼짐 — 라디오버튼처럼 동작하도록 체크박스 두 개로 구현).

Parsing 모드에서 한 번 처리한 데이터를 CSV로 캐싱해두는 것은, 같은 원시 데이터로 그래프 설정만 바꿔서 PPT를 다시 만들 때 매번 무거운 바이너리 파싱을 반복하지 않게 하려는 의도다.

### 4.6 RPT 전용 동적 UI — 컬럼 자동 감지

RPT 공정을 선택하면, `_build_rpt_extra_group()`이 만든 드롭다운 4개가 나타난다. 이 드롭다운의 선택지는 고정되어 있지 않고, **선택된 CSV/파싱 결과를 읽어서 동적으로 채워진다**:

```python
def _refresh_numeric_columns(self):
    df = pd.read_csv(csv_path, nrows=500)        # 앞 500행만 읽어 빠르게 컬럼 타입 추론
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    exclude = {'Capacity', 'Voltage', ...}        # 이미 슬라이드9/10에 고정으로 들어가는 컬럼
    numeric_cols = [c for c in numeric_cols if c not in exclude]
    # 드롭다운 4개에 채워 넣기 (기존 선택값 보존 시도)
```

`exclude` 집합으로 이미 고정 슬롯에 들어가는 컬럼(`Origin_ppt_pipeline_02.py`의 `PROCESS_CONFIGS["RPT"]`에 하드코딩된 것과 동일한 컬럼명)을 제외하는 부분은, **두 파일 사이에 암묵적인 계약**이 있다는 뜻이다. 한쪽(`PROCESS_CONFIGS`)의 고정 컬럼 목록이 바뀌면, 다른 쪽(`exclude` 집합)도 같이 바뀌어야 하는데 이 동기화는 코드로 강제되어 있지 않고 수동 관리에 의존한다.

### 4.7 채널 자동 감지 — `_try_detect_channels()`

CSV/파싱 경로가 바뀔 때마다(`_on_path_changed` 트리거), `chNo` 컬럼만 읽어서(`usecols=['chNo']`로 전체 로드 비용을 줄임) 채널 목록을 갱신한다. 흥미로운 처리는 **기존 선택값과 새로 감지된 채널이 전혀 겹치지 않으면, 다른 데이터셋으로 바뀐 것으로 간주해 선택값을 전체로 리셋**하는 부분이다:

```python
valid_selection = [ch for ch in self._selected_channels if ch in channels]
if not valid_selection:
    self._selected_channels = channels[:]   # 완전히 다른 데이터셋 → 전체 선택으로 리셋
else:
    self._selected_channels = valid_selection  # 겹치는 부분만 유지
```

이는 사용자가 경로를 바꿨을 때 "이전 데이터셋에서 선택했던 채널 번호가 새 데이터셋에는 존재하지 않는데 그대로 남아있는" 혼란을 막기 위한 처리다.

### 4.8 설정 요약 패널의 역할

`_build_summary_group()`이 만드는 패널은 실행에 영향을 주지 않는 **순수 읽기용 패널**이다. 사용자가 입력을 바꿀 때마다 `_update_summary()`가 호출되어 현재 설정(공정/모드/스텝타입/사이클/채널/출력경로/템플릿)을 한눈에 보여준다. 모든 입력 위젯의 `textChanged`/`stateChanged` 시그널이 `_update_summary`로 연결되어 있어, 실행 버튼을 누르기 전에 "지금 이 설정으로 돌아갈 것"이라는 확인을 시각적으로 제공하는 역할이다.

### 4.9 실행 시점 데이터 흐름 — `_run()`부터 끝까지

```
사용자가 "실행" 버튼 클릭
  │
  ▼
MainWindow._run()
  ├─ 입력 검증 (필수 경로 비었는지 체크)
  ├─ config 딕셔너리 구성
  │    {mode, process, raw_dir/csv_path, output_dir, template,
  │     step_types, cycle_nos, selected_channels,
  │     selected_extra_columns(RPT만)}
  ├─ 경로 기억 저장 (QSettings)
  └─ Worker(config) 생성 → start()
        │
        ▼ (백그라운드 스레드)
Worker.run()
  ├─ Origin_ppt_pipeline_02 임포트 (지연 임포트)
  ├─ mode에 따라 _run_parsing_mode() 또는 _run_csv_mode() 호출
  │    → cyc_df, cts_df 획득
  ├─ selected_channels로 두 DataFrame 필터링
  └─ run_pipeline(cyc_df, cts_df, ..., selected_extra_columns=...)
        │
        ▼ (Origin_ppt_pipeline_02.py로 제어 이동)
        [3장에서 설명한 파이프라인 실행]
        │
        ▼ 완료 후
  HistoryManager.add(...) 로 이력 기록
  signals.done.emit(True/False)
        │
        ▼ (메인 스레드)
MainWindow._on_done()
  └─ 버튼/진행률 상태 복구, 완료/오류 로그 표시
```

### 4.10 알아둘 점 / 잠재 리스크

- **`Worker.terminate()`의 위험성** — `_stop()`에서 중단 시 `QThread.terminate()`를 호출하는데, 이는 스레드를 즉시 강제 종료하는 방식이라 Origin/PowerPoint COM 객체가 정리되지 않은 채 프로세스가 남을 수 있다(`run_pipeline()`의 `try/finally`가 끝까지 실행되지 못함). 사용자가 "중단"을 누르면 Origin.exe가 좀비로 남는 시나리오가 있을 수 있다.
- **`exclude` 집합과 `PROCESS_CONFIGS`의 암묵적 동기화** (4.6절) — 코드 두 곳에 같은 정보가 따로 적혀있어 유지보수 시 누락 위험이 있다.
- **`HistoryManager`가 정적 메서드만 가지므로 사실상 모듈 수준 함수 모음**이다. 클래스로 감싼 이유는 네임스페이스 정리 목적으로 보이며, 인스턴스 상태는 갖지 않는다.

---

## 5. 세 파일이 공유하는 데이터 계약 (Schema Contract)

코드로 강제되지 않지만 실질적으로 지켜져야 하는 약속들을 정리한다. 향후 어느 한쪽을 수정할 때 다른 쪽도 같이 봐야 하는 지점이다.

| 계약 내용 | 정의하는 곳 | 의존하는 곳 |
|---|---|---|
| 컬럼명 (`Capacity`, `Voltage`, `Impedance_30s` 등) | `Parsing_01.py`의 `column_rename()` | `Origin_ppt_pipeline_02.py`의 `PROCESS_CONFIGS` |
| `chNo`, `ulCurrentCycleNum`, `chStepType` 필드명 | `CtsParser.data_preprocessing()` | `filter_data()`, `get_channel_list()` 등 거의 모든 필터링 로직 |
| RPT 고정 슬롯 컬럼 목록 | `PROCESS_CONFIGS["RPT"]` | `Main_ui_03.py`의 `exclude` 집합 |
| 윈도우 타이틀 문자열 `"충방전 Data Processing Tool"` | `Main_ui_03.py`의 `setWindowTitle()` | `Origin_ppt_pipeline_02.py`의 `copy_graph_to_clipboard()` (이 창을 찾아 최소화하기 위해 제목 문자열로 검색) |
| 모듈 파일명 (`Origin_ppt_pipeline_02`, `Parsing_01`) | 파일명 자체 | `Main_ui_03.py`의 `from X import Y` 문 (파일명을 바꾸면 import 깨짐) |

마지막 두 항목은 특히 취약한 지점이다 — **문자열 매칭으로 연결되어 있어, 리팩토링 시 컴파일 타임에 잡히지 않고 런타임에야 실패가 드러난다.**

---

## 6. 요약 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                         Main_ui_03.py                           │
│  (PySide6 GUI — 사용자 입력 수집 + Worker 스레드로 비동기 실행)   │
└───────────────────────────┬───────────────────────────────────┘
                            │ config dict
                            ▼
                  ┌─────────────────┐
                  │  Worker.run()    │
                  └────┬───────┬────┘
          mode='parsing'│       │mode='csv'
                  ▼      │       ▼
     ┌──────────────────┐│ ┌──────────────────┐
     │  Parsing_01.py   ││ │ pd.read_csv(...)  │
     │  ┌─────────────┐ ││ └──────────────────┘
     │  │File_search   │ ││
     │  │CycParser     │ ││         (캐싱된 CSV를
     │  │CtsParser     │ ││          그대로 로드)
     │  │SchParser     │ ││
     │  │cyc_cts_sch_  │ ││
     │  │  comb        │ ││
     │  └─────────────┘ ││
     └────────┬─────────┘│
              │ cyc_df, cts_df
              └──────┬────┘
                     ▼
        ┌────────────────────────────┐
        │ Origin_ppt_pipeline_02.py   │
        │ run_pipeline()              │
        │  ├─ filter_data()           │
        │  ├─ PowerPoint COM 실행      │
        │  ├─ Origin COM 실행          │
        │  ├─ Formation/RPT 분기       │
        │  │   ├─ _build_graph/box    │
        │  │   ├─ copy_graph_to_      │
        │  │   │   clipboard()        │
        │  │   └─ paste_ole_to_       │
        │  │       slide()            │
        │  └─ .opju / .pptx 저장       │
        └────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  결과물                     │
        │  - {stem}_{process}.pptx   │
        │  - {stem}_{process}.opju   │
        │  - 그래프별 .png (백업)     │
        │  - log.txt                 │
        └────────────────────────────┘
```
