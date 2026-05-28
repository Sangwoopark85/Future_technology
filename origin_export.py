"""
origin_export.py
CSV → Origin 그래프 생성 → IMG, OPJU 저장

실행:
    python origin_export.py
    
주의:
    - 완료 후 Origin 창을 닫고 ppt_builder.py 를 실행하세요.
    - 한글 경로 사용 불가 (Origin 제한)
"""

import os
import originpro as op


class Origin_Export:
    def __init__(self, CSV_PATH, TEMPLATE_PATH, OPJU_PATH, IMG_PATH,
                 COL_X=0, COL_Y=1, GRAPH_TYPE="LINE"):
        self.CSV_PATH      = CSV_PATH
        self.TEMPLATE_PATH = TEMPLATE_PATH
        self.OPJU_PATH     = OPJU_PATH
        self.IMG_PATH      = IMG_PATH
        self.COL_X         = COL_X
        self.COL_Y         = COL_Y
        self.GRAPH_TYPE    = GRAPH_TYPE  # 템플릿 없을 때 사용

    def run(self):
        """CSV → Origin 그래프 생성 + IMG, OPJU 저장"""
        print("=" * 50)
        print("  [Origin Export] 그래프 생성 시작")
        print("=" * 50)

        # 입력 파일 확인
        if not os.path.exists(self.CSV_PATH):
            print(f"❌ CSV 파일 없음: {self.CSV_PATH}")
            return False
        if not os.path.exists(self.TEMPLATE_PATH):
            print(f"❌ 템플릿 파일 없음: {self.TEMPLATE_PATH}")
            return False

        # 출력 폴더 자동 생성
        os.makedirs(os.path.dirname(self.OPJU_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(self.IMG_PATH), exist_ok=True)

        try:
            try:
                op.set_show(True)
                print("0. Origin 실행 완료")
            except Exception as e:
                print(f"0. set_show 오류 무시하고 진행: {e}")

            wks = op.new_sheet()
            wks.from_file(self.CSV_PATH, False)
            print(f"1. CSV 로드 완료: {self.CSV_PATH}")

            if self.TEMPLATE_PATH and os.path.exists(self.TEMPLATE_PATH):
                graph = op.new_graph(template=self.TEMPLATE_PATH)
                print(f"2. 템플릿 적용: {self.TEMPLATE_PATH}")
            else:
                graph = op.new_graph(template=self.GRAPH_TYPE)
                print(f"2. 기본 템플릿 사용: {self.GRAPH_TYPE}")

            gl = graph[0]
            gl.add_plot(wks, colx=self.COL_X, coly=self.COL_Y)
            gl.rescale()
            print("3. 그래프 생성 완료")

            graph.save_fig(self.IMG_PATH, width=800)
            print(f"4. IMG 저장 완료: {os.path.exists(self.IMG_PATH)}")

            op.save(self.OPJU_PATH)
            print(f"5. OPJU 저장 완료: {os.path.exists(self.OPJU_PATH)}")

            print("\n" + "=" * 50)
            print("  ✅ 완료! Origin 창을 닫고 ppt_builder.py 를 실행하세요.")
            print("=" * 50)
            return True

        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            return False

    def cleanup(self):
        """임시 파일 정리 (선택)"""
        print("\n[임시 파일 정리 중...]")
        for path in [self.OPJU_PATH, self.IMG_PATH]:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"  삭제: {path}")
            except Exception as e:
                print(f"  삭제 실패: {path} ({e})")


if __name__ == "__main__":
    # ============================================================
    # 설정값
    # ============================================================
    CSV_PATH      = r"C:\Users\tablrain\Desktop\origin_dev\06_modified_csv\00206354_250624_AYH_TEST17_45oC cycle_101-200_extracted.csv"
    TEMPLATE_PATH = r"C:\Users\tablrain\Desktop\origin_dev\02_template\Capacity-Voltage.otpu"
    OPJU_PATH     = r"C:\Users\tablrain\Desktop\origin_dev\03_OPJU\output.opju"
    IMG_PATH      = r"C:\Users\tablrain\Desktop\origin_dev\04_image\graph.png"
    COL_X         = 0   # PS_VOLTAGE
    COL_Y         = 1   # PS_CAPACITY
    # ============================================================

    exporter = Origin_Export(
        CSV_PATH      = CSV_PATH,
        TEMPLATE_PATH = TEMPLATE_PATH,
        OPJU_PATH     = OPJU_PATH,
        IMG_PATH      = IMG_PATH,
        COL_X         = COL_X,
        COL_Y         = COL_Y,
    )
    exporter.run()
