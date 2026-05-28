import os
import time
import pandas as pd
import originpro as op
import win32com.client


# ============================================================
class CSV_Preprocessor:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path, index_col=0)
        print(f"CSV 로드 완료: {csv_path}")
        print(f"컬럼 목록: {list(self.df.columns)}")

    def preview(self):
        print(self.df.head())
        return self

    def extract(self, x_col, y_cols, output_path=None):
        cols = [x_col] + y_cols
        extracted = self.df[cols]

        if output_path is None:
            output_path = self.csv_path.replace(".csv", "_extracted.csv")

        extracted.to_csv(output_path, index=False)
        print(f"추출 완료: {cols} → {output_path}")
        return output_path


# ============================================================
class Origin_Export:
    def __init__(self, CSV_PATH, TEMPLATE_PATH, OPJU_PATH, IMG_PATH, PPT_PATH,
                 COL_X, COL_Y,
                 OLE_LEFT=50, OLE_TOP=100, OLE_WIDTH=500, OLE_HEIGHT=350,
                 SLIDE_NUM=1, GRAPH_TYPE="LINE"):

        self.CSV_PATH      = CSV_PATH
        self.TEMPLATE_PATH = TEMPLATE_PATH
        self.OPJU_PATH     = OPJU_PATH
        self.IMG_PATH      = IMG_PATH
        self.PPT_PATH      = PPT_PATH
        self.COL_X         = COL_X
        self.COL_Y         = COL_Y
        self.OLE_LEFT      = OLE_LEFT
        self.OLE_TOP       = OLE_TOP
        self.OLE_WIDTH     = OLE_WIDTH
        self.OLE_HEIGHT    = OLE_HEIGHT
        self.SLIDE_NUM     = SLIDE_NUM
        self.GRAPH_TYPE    = GRAPH_TYPE  # 템플릿 없을 때 사용

    def step1_create_origin_graph(self):
        """[1단계] CSV → Origin 그래프 생성 + 이미지/프로젝트 파일 저장"""
        print("\n[1단계] Origin 그래프 생성 중...")

        op.set_show(False)

        wks = op.new_sheet()
        wks.from_file(self.CSV_PATH, False)
        print(f"  CSV 로드: {self.CSV_PATH}")

        if self.TEMPLATE_PATH and os.path.exists(self.TEMPLATE_PATH):
            graph = op.new_graph(template=self.TEMPLATE_PATH)
            print(f"  템플릿 적용: {self.TEMPLATE_PATH}")
        else:
            graph = op.new_graph(template=self.GRAPH_TYPE)
            print(f"  기본 템플릿 사용: {self.GRAPH_TYPE}")

        gl = graph[0]
        gl.add_plot(wks, colx=self.COL_X, coly=self.COL_Y)
        gl.rescale()
        print("  그래프 생성 완료")

        graph.save_fig(self.IMG_PATH, width=800)
        print(f"  이미지 저장: {self.IMG_PATH}")

        op.save(self.OPJU_PATH)
        print(f"  Origin 프로젝트 저장: {self.OPJU_PATH}")

    def step2_insert_to_ppt(self):
        """[2단계] Origin OLE 객체 + 그래프 이미지 → PPT 삽입"""
        print("\n[2단계] PPT에 삽입 중...")

        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        powerpoint.Visible = True

        if os.path.exists(self.PPT_PATH):
            prs = powerpoint.Presentations.Open(self.PPT_PATH)
            print(f"  기존 PPT 열기: {self.PPT_PATH}")
        else:
            prs = powerpoint.Presentations.Add()
            prs.Slides.Add(1, 1)
            print("  새 PPT 생성")

        slide = prs.Slides(self.SLIDE_NUM)

        ole_shape = slide.Shapes.AddOLEObject(
            Left=self.OLE_LEFT,
            Top=self.OLE_TOP,
            Width=self.OLE_WIDTH,
            Height=self.OLE_HEIGHT,
            FileName=self.OPJU_PATH,
            Link=False,
            DisplayAsIcon=False
        )
        print("  OLE 객체 삽입 성공")

        try:
            ole_shape.Fill.UserPicture(self.IMG_PATH)
            print("  그래프 이미지 적용 성공")
        except Exception as e:
            print(f"  Fill 방식 실패 ({e}), 이미지 덮어씌우기로 대체")
            slide.Shapes.AddPicture(
                FileName=self.IMG_PATH,
                LinkToFile=False,
                SaveWithDocument=True,
                Left=self.OLE_LEFT,
                Top=self.OLE_TOP,
                Width=self.OLE_WIDTH,
                Height=self.OLE_HEIGHT
            )
            print("  이미지 덮어씌우기 성공")

        prs.SaveAs(self.PPT_PATH)
        print(f"  PPT 저장: {self.PPT_PATH}")

        time.sleep(1)
        try: prs.Close()
        except: pass
        try: powerpoint.Quit()
        except: pass

    def step3_cleanup(self):
        """[3단계] 임시 파일 정리"""
        print("\n[3단계] 임시 파일 정리 중...")
        for path in [self.OPJU_PATH, self.IMG_PATH]:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"  삭제: {path}")
            except Exception as e:
                print(f"  삭제 실패: {path} ({e})")


# ============================================================
# 설정값
# ============================================================
CSV_PATH      = r"C:\Users\tablrain\Desktop\개발\01_data\00206354_250624_AYH_TEST17_45oC cycle_101-200.csv"
TEMPLATE_PATH = r"C:\Users\tablrain\Desktop\개발\03_output\Capacity-Voltage.otpu"
IMG_PATH      = r"C:\Users\tablrain\Desktop\개발\05_image\graph.png"    # 파일명 포함
OPJU_PATH     = r"C:\Users\tablrain\Desktop\개발\07_OPJU\output.opju"   # 파일명 포함
PPT_PATH      = r"C:\Users\tablrain\Desktop\개발\04_ppt\output.pptx"


# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  CSV → Origin → PPT 자동화 시작")
    print("=" * 50)

    if not os.path.exists(CSV_PATH):
        print(f"\nCSV 파일을 찾을 수 없습니다: {CSV_PATH}")
        exit(1)

    origin_export = Origin_Export(
        CSV_PATH      = CSV_PATH,
        TEMPLATE_PATH = TEMPLATE_PATH,
        OPJU_PATH     = OPJU_PATH,
        IMG_PATH      = IMG_PATH,
        PPT_PATH      = PPT_PATH,
        COL_X         = 'PS_VOLTAGE',
        COL_Y         = 'PS_CAPACITY',
    )

    try:
        origin_export.step1_create_origin_graph()
        origin_export.step2_insert_to_ppt()
        # origin_export.step3_cleanup()  # 임시 파일 삭제 원하면 주석 해제

        print("\n" + "=" * 50)
        print("  🎉 완료! PPT 파일을 확인하세요.")
        print(f"  📁 {PPT_PATH}")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
