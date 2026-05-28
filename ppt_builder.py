"""
ppt_builder.py
IMG → PPT 이미지 삽입 + OPJU 같은 폴더에 복사

실행:
    python ppt_builder.py   ← origin_export.py 완료 + Origin 창 닫은 후
    
주의:
    - origin_export.py 실행 후 Origin 창을 완전히 닫고 실행하세요.
    - 한글 경로 사용 불가 (COM 제한)
"""

import os
import time
import shutil
import win32com.client


class PPT_Builder:
    def __init__(self, OPJU_PATH, IMG_PATH, PPT_PATH,
                 SLIDE_NUM=1,
                 IMG_LEFT=50, IMG_TOP=100, IMG_WIDTH=500, IMG_HEIGHT=350):
        self.OPJU_PATH  = OPJU_PATH
        self.IMG_PATH   = IMG_PATH
        self.PPT_PATH   = PPT_PATH
        self.SLIDE_NUM  = SLIDE_NUM
        self.IMG_LEFT   = IMG_LEFT
        self.IMG_TOP    = IMG_TOP
        self.IMG_WIDTH  = IMG_WIDTH
        self.IMG_HEIGHT = IMG_HEIGHT

    def run(self):
        """IMG → PPT 삽입 + OPJU 복사"""
        print("=" * 50)
        print("  [PPT Builder] PPT 삽입 시작")
        print("=" * 50)

        # 입력 파일 확인
        if not os.path.exists(self.IMG_PATH):
            print(f"❌ IMG 파일 없음: {self.IMG_PATH}")
            print("   origin_export.py 를 먼저 실행하세요.")
            return False
        if not os.path.exists(self.OPJU_PATH):
            print(f"❌ OPJU 파일 없음: {self.OPJU_PATH}")
            print("   origin_export.py 를 먼저 실행하세요.")
            return False

        # 출력 폴더 자동 생성
        ppt_dir = os.path.dirname(self.PPT_PATH)
        os.makedirs(ppt_dir, exist_ok=True)

        try:
            powerpoint = win32com.client.Dispatch("PowerPoint.Application")
            powerpoint.Visible = True
            print("1. PowerPoint 실행 완료")

            # PPT 열기 또는 새로 생성
            if os.path.exists(self.PPT_PATH):
                prs = powerpoint.Presentations.Open(self.PPT_PATH)
                print("2. 기존 PPT 열기 완료")
            else:
                prs = powerpoint.Presentations.Add()
                prs.Slides.Add(1, 1)
                print("2. 새 PPT 생성 완료")

            slide = prs.Slides(self.SLIDE_NUM)
            print(f"3. 슬라이드 {self.SLIDE_NUM} 접근 완료")

            # 그래프 이미지 삽입
            slide.Shapes.AddPicture(
                FileName=self.IMG_PATH,
                LinkToFile=False,
                SaveWithDocument=True,
                Left=self.IMG_LEFT,
                Top=self.IMG_TOP,
                Width=self.IMG_WIDTH,
                Height=self.IMG_HEIGHT
            )
            print("4. 이미지 삽입 완료")

            prs.SaveAs(self.PPT_PATH)
            print("5. PPT 저장 완료")

            time.sleep(1)
            try: prs.Close()
            except: pass
            try: powerpoint.Quit()
            except: pass

            # OPJU를 PPT와 같은 폴더에 복사 (함께 배포용)
            opju_dest = os.path.join(ppt_dir, os.path.basename(self.OPJU_PATH))
            shutil.copy2(self.OPJU_PATH, opju_dest)
            print(f"6. OPJU 복사 완료: {opju_dest}")

            print("\n" + "=" * 50)
            print("  🎉 완료! 아래 두 파일을 함께 공유하세요.")
            print(f"  📊 PPT  : {self.PPT_PATH}")
            print(f"  📁 OPJU : {opju_dest}")
            print("=" * 50)
            return True

        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            return False


if __name__ == "__main__":
    # ============================================================
    # 설정값
    # ============================================================
    OPJU_PATH  = r"C:\Users\tablrain\Desktop\origin_dev\03_OPJU\output.opju"
    IMG_PATH   = r"C:\Users\tablrain\Desktop\origin_dev\04_image\graph.png"
    PPT_PATH   = r"C:\Users\tablrain\Desktop\origin_dev\05_ppt\output.pptx"
    SLIDE_NUM  = 1
    IMG_LEFT   = 50
    IMG_TOP    = 100
    IMG_WIDTH  = 500
    IMG_HEIGHT = 350
    # ============================================================

    builder = PPT_Builder(
        OPJU_PATH  = OPJU_PATH,
        IMG_PATH   = IMG_PATH,
        PPT_PATH   = PPT_PATH,
        SLIDE_NUM  = SLIDE_NUM,
        IMG_LEFT   = IMG_LEFT,
        IMG_TOP    = IMG_TOP,
        IMG_WIDTH  = IMG_WIDTH,
        IMG_HEIGHT = IMG_HEIGHT,
    )
    builder.run()
