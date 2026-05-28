"""
csv_preprocessor.py
CSV에서 원하는 컬럼만 추출해서 저장
"""

import pandas as pd
import os


class CSV_Preprocessor:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path, index_col=0)
        print(f"CSV 로드 완료: {csv_path}")
        print(f"컬럼 목록: {list(self.df.columns)}")

    def preview(self):
        """컬럼 목록과 샘플 데이터 확인"""
        print(self.df.head())
        return self

    def extract(self, x_col, y_cols, output_path=None):
        """
        원하는 X, Y 컬럼만 추출해서 CSV로 저장

        x_col       : X축 컬럼명 (문자열)
        y_cols      : Y축 컬럼명 리스트 (예: ["PS_CAPACITY"])
        output_path : 저장 경로 (None이면 자동 생성)
        """
        cols = [x_col] + y_cols
        extracted = self.df[cols]

        if output_path is None:
            output_path = self.csv_path.replace(".csv", "_extracted.csv")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        extracted.to_csv(output_path, index=False)
        print(f"추출 완료: {cols} → {output_path}")
        return output_path


if __name__ == "__main__":
    # ============================================================
    # 설정값
    # ============================================================
    CSV_PATH    = r"C:\Users\tablrain\Desktop\origin_dev\01_data\00206354_250624_AYH_TEST17_45oC cycle_101-200.csv"
    OUTPUT_PATH = r"C:\Users\tablrain\Desktop\origin_dev\06_modified_csv\00206354_250624_AYH_TEST17_45oC cycle_101-200_extracted.csv"
    X_COL       = "PS_VOLTAGE"
    Y_COLS      = ["PS_CAPACITY"]
    # ============================================================

    pre = CSV_Preprocessor(CSV_PATH)
    # pre.preview()  # 컬럼 목록 확인 시 주석 해제

    extracted_path = pre.extract(
        x_col=X_COL,
        y_cols=Y_COLS,
        output_path=OUTPUT_PATH
    )
    print(f"✅ 완료: {extracted_path}")
