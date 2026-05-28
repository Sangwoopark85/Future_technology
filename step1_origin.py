"""
step1_origin.py
CSV → Origin 그래프 생성 → IMG, OPJU 저장
실행: python step1_origin.py
"""

import os
import originpro as op

# ============================================================
# 설정값
# ============================================================
CSV_PATH      = r"C:\Users\tablrain\Desktop\origin_dev\01_data\00206354_250624_AYH_TEST17_45oC cycle_101-200.csv"
TEMPLATE_PATH = r"C:\Users\tablrain\Desktop\origin_dev\02_template\Capacity-Voltage.otpu"
OPJU_PATH     = r"C:\Users\tablrain\Desktop\origin_dev\03_OPJU\output.opju"
IMG_PATH      = r"C:\Users\tablrain\Desktop\origin_dev\04_image\graph.png"
COL_X         = 0   # PS_VOLTAGE
COL_Y         = 1   # PS_CAPACITY
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("  [step1] Origin 그래프 생성 시작")
    print("=" * 50)

    # 파일 존재 확인
    if not os.path.exists(CSV_PATH):
        print(f"❌ CSV 파일 없음: {CSV_PATH}")
        exit(1)
    if not os.path.exists(TEMPLATE_PATH):
        print(f"❌ 템플릿 파일 없음: {TEMPLATE_PATH}")
        exit(1)

    # 출력 폴더 자동 생성
    os.makedirs(os.path.dirname(OPJU_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(IMG_PATH), exist_ok=True)

    try:
        op.set_show(True)

        wks = op.new_sheet()
        wks.from_file(CSV_PATH, False)
        print("1. CSV 로드 완료")

        graph = op.new_graph(template=TEMPLATE_PATH)
        gl = graph[0]
        gl.add_plot(wks, colx=COL_X, coly=COL_Y)
        gl.rescale()
        print("2. 그래프 생성 완료")

        graph.save_fig(IMG_PATH, width=800)
        print(f"3. IMG 저장 완료: {os.path.exists(IMG_PATH)}")

        op.save(OPJU_PATH)
        print(f"4. OPJU 저장 완료: {os.path.exists(OPJU_PATH)}")

        print("\n" + "=" * 50)
        print("  ✅ step1 완료! step2_ppt.py 를 실행하세요.")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
