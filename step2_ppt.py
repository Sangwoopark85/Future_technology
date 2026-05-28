"""
step2_ppt.py
OPJU + IMG → PPT OLE 삽입
실행: python step2_ppt.py  (step1 완료 후 Origin 닫고 실행)
"""

import os
import time
import win32com.client

# ============================================================
# 설정값
# ============================================================
OPJU_PATH  = r"C:\Users\tablrain\Desktop\origin_dev\03_OPJU\output.opju"
IMG_PATH   = r"C:\Users\tablrain\Desktop\origin_dev\04_image\graph.png"
PPT_PATH   = r"C:\Users\tablrain\Desktop\origin_dev\05_ppt\output.pptx"
SLIDE_NUM  = 1

# OLE 객체 위치/크기 (포인트 단위, 1인치=72pt)
OLE_LEFT   = 50
OLE_TOP    = 100
OLE_WIDTH  = 500
OLE_HEIGHT = 350
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("  [step2] PPT 삽입 시작")
    print("=" * 50)

    # 파일 존재 확인
    if not os.path.exists(OPJU_PATH):
        print(f"❌ OPJU 파일 없음: {OPJU_PATH}")
        print("   step1_origin.py 를 먼저 실행하세요.")
        exit(1)
    if not os.path.exists(IMG_PATH):
        print(f"❌ IMG 파일 없음: {IMG_PATH}")
        print("   step1_origin.py 를 먼저 실행하세요.")
        exit(1)

    # 출력 폴더 자동 생성
    os.makedirs(os.path.dirname(PPT_PATH), exist_ok=True)

    try:
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        powerpoint.Visible = True
        print("1. PowerPoint 실행 완료")

        # PPT 열기 또는 새로 생성
        if os.path.exists(PPT_PATH):
            prs = powerpoint.Presentations.Open(PPT_PATH)
            print(f"2. 기존 PPT 열기 완료: {PPT_PATH}")
        else:
            prs = powerpoint.Presentations.Add()
            prs.Slides.Add(1, 1)
            print("2. 새 PPT 생성 완료")

        slide = prs.Slides(SLIDE_NUM)
        print(f"3. 슬라이드 {SLIDE_NUM} 접근 완료")

        # OLE 삽입
        ole_shape = slide.Shapes.AddOLEObject(
            Left=OLE_LEFT,
            Top=OLE_TOP,
            Width=OLE_WIDTH,
            Height=OLE_HEIGHT,
            FileName=OPJU_PATH,
            Link=False,
            DisplayAsIcon=False
        )
        print("4. OLE 삽입 완료")

        # 그래프 이미지 적용
        try:
            ole_shape.Fill.UserPicture(IMG_PATH)
            print("5. 이미지 적용 완료 (Fill 방식)")
        except Exception as e:
            print(f"5. Fill 실패 ({e}), 이미지 덮어씌우기로 대체")
            slide.Shapes.AddPicture(
                FileName=IMG_PATH,
                LinkToFile=False,
                SaveWithDocument=True,
                Left=OLE_LEFT,
                Top=OLE_TOP,
                Width=OLE_WIDTH,
                Height=OLE_HEIGHT
            )
            print("5. 이미지 덮어씌우기 완료")

        prs.SaveAs(PPT_PATH)
        print(f"6. PPT 저장 완료: {PPT_PATH}")

        time.sleep(1)
        try: prs.Close()
        except: pass
        try: powerpoint.Quit()
        except: pass

        print("\n" + "=" * 50)
        print("  🎉 step2 완료! PPT 파일을 확인하세요.")
        print(f"  📁 {PPT_PATH}")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
