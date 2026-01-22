# -*- coding: utf-8 -*-
"""
PPM.py (통합 추출판)

목표
- for_extract/ 폴더에 넣어둔 SAP 산출 파일에서 데이터를 추출하여 CSV DB에 누적 저장
  1) DB_product.csv : 월별 × 품목별 (품목별_제조이익.xlsx, 41행 반복 블록)
  2) DB.csv         : 월별 (공장별_제조이익.xlsx + 제조원가명세서.xls)

사용법
- PPM.py와 같은 폴더에 for_extract/ 폴더 생성
- for_extract/ 안에 아래 파일들을 넣고 PPM.py 실행
  - 품목별_제조이익*.xlsx
  - 공장별_제조이익*.xlsx
  - 제조원가명세서*.xls   (SAP 리스트가 .xls 확장자지만 실제는 탭 구분 텍스트인 경우 포함)

메모
- SAP 포맷이 고정(41행 반복)이라는 전제 하에 작성됨
- 기존 PPM.py 로직(41행 오프셋)은 유지하되, 기준기간 위치는 조금 더 유연하게 파싱함
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ---------------------------
# 기본 유틸
# ---------------------------

def _to_int(x) -> int:
    """콤마/공백/NaN 포함 값을 int로 변환 (실패 시 0)."""
    if x is None or (isinstance(x, float) and pd.isna(x)) or (isinstance(x, str) and x.strip() == ""):
        return 0
    try:
        if isinstance(x, str):
            s = x.strip().replace(",", "")
            # 괄호 음수 (1,234) 스타일이 들어오는 경우
            if s.startswith("(") and s.endswith(")"):
                s = "-" + s[1:-1]
            return int(float(s))
        if isinstance(x, (int,)):
            return int(x)
        if isinstance(x, float):
            if pd.isna(x):
                return 0
            return int(x)
        return int(float(x))
    except Exception:
        return 0


def _extract_yyyymm_from_text(text: str) -> Optional[Tuple[int, int]]:
    """
    텍스트에서 (년,월)을 추출.
    지원 예:
    - '기준기간 [2025.12 ~2025.12]'
    - '1.기준기간(2025년12월~2025년12월)'
    """
    if not text:
        return None

    # 2025.12
    m = pd.Series([text]).astype(str).str.extract(r'(\d{4})\.(\d{1,2})').dropna()
    if not m.empty:
        y = int(m.iloc[0, 0]); mm = int(m.iloc[0, 1])
        return (y, mm)

    # 2025년12월
    m2 = pd.Series([text]).astype(str).str.extract(r'(\d{4})\s*년\s*(\d{1,2})\s*월').dropna()
    if not m2.empty:
        y = int(m2.iloc[0, 0]); mm = int(m2.iloc[0, 1])
        return (y, mm)

    return None


def _read_cost_statement_xls(path: Path) -> pd.DataFrame:
    """
    제조원가명세서.xls
    - 진짜 엑셀일 수도 있고(legacy xls)
    - SAP 리스트를 .xls로 저장했지만 실제는 '탭 구분 UTF-16 텍스트'일 수도 있어 둘 다 대응
    """
    # 1) 엑셀로 시도
    try:
        return pd.read_excel(path, header=None)
    except Exception:
        pass

    # 2) 탭구분 텍스트(UTF-16)로 시도
    for enc in ("utf-16", "utf-16le", "cp949", "utf-8"):
        try:
            return pd.read_csv(path, sep="\t", header=None, encoding=enc, engine="python")
        except Exception:
            continue

    # 3) 최후: 빈 DF
    return pd.DataFrame()


def _upsert_csv(db_path: Path, new_df: pd.DataFrame, key_cols: List[str]) -> None:
    """
    CSV DB에 업서트(키 중복이면 덮어쓰기, 신규면 추가)
    """
    if new_df is None or new_df.empty:
        return

    if db_path.exists():
        old = pd.read_csv(db_path, dtype=str)
        # 숫자 컬럼은 저장 시 문자열일 수 있으니 그대로 병합 후 나중에 사용 측에서 캐스팅
        merged = pd.concat([old, new_df.astype(str)], ignore_index=True)
        merged = merged.drop_duplicates(subset=key_cols, keep="last")
    else:
        merged = new_df.astype(str)

    merged.to_csv(db_path, index=False, encoding="utf-8-sig")
 

# ---------------------------
# 1) 품목별_제조이익.xlsx (월별 × 품목별)
# ---------------------------

def _parse_product_code_name(cell0: str) -> Tuple[str, str]:
    """
    '...제품코드(명) :1010000576 / ... (제품명) : ABC...' 같은 문자열에서 코드/명을 추출
    """
    s = "" if cell0 is None else str(cell0)
    # 1) '제품코드(명) :<code>/<name>' (가장 흔한 케이스)
    m = pd.Series([s]).str.extract(r"제품코드\(명\)\s*:\s*([0-9A-Za-z_-]+)\s*/\s*(.+)$")
    code = "" if m.empty or pd.isna(m.iloc[0, 0]) else str(m.iloc[0, 0]).strip()
    name = "" if m.empty or pd.isna(m.iloc[0, 1]) else str(m.iloc[0, 1]).strip()
    
    # 2) 폴백: '(제품명) :' 라벨
    if not name:
        m_name = pd.Series([s]).str.extract(r"\(제품명\)\s*:\s*(.+)$").iloc[0, 0]
        name = "" if pd.isna(m_name) else str(m_name).strip()
        
    return code, name


def _extract_product_yyyymm(df: pd.DataFrame, block_start: int) -> Tuple[int, int]:
    """
    블록 근처에서 기준기간 텍스트를 찾아 (년,월)을 반환.
    """
    # SAP 포맷상 보통 row block_start+1, col 3에 "기준기간(...)"가 있음 (샘플 기준)
    candidates = []
    for r in range(block_start, min(block_start + 6, df.shape[0])):
        for c in range(0, min(8, df.shape[1])):
            v = df.iat[r, c]
            if isinstance(v, str) and ("기준기간" in v or "기준기간" in str(v)):
                candidates.append(str(v))
    # 후보가 없으면 기존 방식(col0)도 시도
    if not candidates:
        v = df.iat[block_start + 1, 0] if df.shape[0] > block_start + 1 else ""
        candidates.append("" if pd.isna(v) else str(v))

    for t in candidates:
        ym = _extract_yyyymm_from_text(t)
        if ym:
            return ym
    # 못 찾으면 0
    return (0, 0)


def extract_products(download_xlsx: Path) -> pd.DataFrame:
    df = pd.read_excel(download_xlsx, header=None)

    out_rows: List[Dict[str, object]] = []

    # 41행 고정 반복 (기존 로직 유지)
    for i in range(1, len(df), 41):
        cell0 = df.iat[i, 0] if df.shape[0] > i else ""
        code, name = _parse_product_code_name(cell0)
        if not code:
            continue

        y, m = _extract_product_yyyymm(df, i)

        def val(row_offset: int, col: int = 7) -> int:
            r = i + row_offset
            if r < 0 or r >= df.shape[0] or col >= df.shape[1]:
                return 0
            return _to_int(df.iat[r, col])

        row = {
            "년": y,
            "월": m,
            "제품코드": code,
            "제품명": name,

            "합계_재료비": val(4, 7),
            "합계_노무비": val(9, 7),
            "합계_제조경비": val(20, 7),
            "유틸리티": val(23, 7),

            "합계_제조원가": val(31, 7),
            "합계_생산금액": val(33, 7),
            "생산량(EA)": val(35, 7),
        }
        out_rows.append(row)

    return pd.DataFrame(out_rows)


# ---------------------------
# 2) 공장별_제조이익.xlsx (월별 1행) - 사용자 지정 추출 항목
# ---------------------------

def extract_factory_monthly(factory_xlsx: Path) -> Dict[str, object]:
    df = pd.read_excel(factory_xlsx, header=None)

    # 기준기간 파싱 (샘플: row2 col3)
    header_cell = df.iat[2, 3] if (df.shape[0] > 2 and df.shape[1] > 3) else ""
    ym = _extract_yyyymm_from_text("" if pd.isna(header_cell) else str(header_cell))
    y, m = ym if ym else (0, 0)

    def _cell_str(v) -> str:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        return str(v).strip()

    def pick(path: Tuple[Optional[str], Optional[str], Optional[str]], value_col: int = 9) -> int:
        """
        path 예:
          ("재료비","합계",None)  -> col0 contains '재료비' AND col1 contains '합계'
          (None,"원재료비",None)  -> col1 contains '원재료비'
          (None,"직접비","합계")  -> col1 contains '직접비' AND col2 contains '합계'
        """
        p0, p1, p2 = path
        for r in range(df.shape[0]):
            c0 = _cell_str(df.iat[r, 0]) if df.shape[1] > 0 else ""
            c1 = _cell_str(df.iat[r, 1]) if df.shape[1] > 1 else ""
            c2 = _cell_str(df.iat[r, 2]) if df.shape[1] > 2 else ""
            ok = True
            if p0 is not None and p0 not in c0:
                ok = False
            if p1 is not None and p1 not in c1:
                ok = False
            if p2 is not None and p2 not in c2:
                ok = False
            if ok:
                return _to_int(df.iat[r, value_col]) if df.shape[1] > value_col else 0
        return 0

    result = {
        "년": y,
        "월": m,

        # 재료비
        "재료비_합계": pick(("재료비", "합계", None)),
        "재료비_원재료비": pick((None, "원재료비", None)),
        "재료비_부재료비": pick((None, "부재료비", None)),

        # 노무비
        "노무비_합계": pick(("노무비", "합계", None)),
        "노무비_직접비_합계": pick((None, "직접비", "합계")),
        "노무비_간접비_합계": pick((None, "간접비", "합계")),

        # 제조경비
        "제조경비_합계": pick(("제조경비", "합계", None)),
        "제조경비_유틸리티_합계": pick((None, "유틸리티", "합계")),
        "제조경비_감가상각_합계": pick((None, "감가상각", "합계")),

        # 제조이익/생산
        "제조이익": pick(("제조이익", None, None)),
        "생산금액": pick(("생산금액", None, None)),
        "생산량(KG)": pick(("생산량(KG)", None, None)),
        "생산량(EA)": pick(("생산량(EA)", None, None)),
    }

    return result


# ---------------------------
# 3) 제조원가명세서.xls (월별 1행) - (기존 PPM_new 기본형 유지)
# ---------------------------

def _extract_yyyymm_from_filename(path: Path) -> Optional[Tuple[int, int]]:
    """
    파일명에서 (년,월) 추출:
    - 202512 / 2025-12 / 2025.12 / 2025_12 등의 패턴 지원
    """
    name = path.stem
    m = pd.Series([name]).astype(str).str.extract(r'(\d{4})[.\-_]?\s*(\d{2})').dropna()
    if not m.empty:
        y = int(m.iloc[0, 0]); mm = int(m.iloc[0, 1])
        return (y, mm)
    return None


def extract_cost_statement_monthly(cost_xls: Path) -> Dict[str, object]:
    """
    제조원가명세서.xls에서 KPI 항목 추출 (사용자 지정)
    - 추출 컬럼: H열 (= 8번째 컬럼, 0-index 7)
    - 추출 항목:
        * KPI_노무비                : col0='2.노무비' & (col1,col2 None)
        * KPI_경비                  : col0='3.경비' & (col1,col2 None)
        * KPI_경비_수도광열비        : col0='3.경비' & col1='1)수도광열비' & (계정열 None)
        * KPI_경비_감가상각비        : col0='3.경비' & col1='4)감가상각비' & (계정열 None)
    """
    df = _read_cost_statement_xls(cost_xls)

    # 기간: 파일 내에서 찾기 어려운 경우가 많아서 filename → 그래도 없으면 0
    y, mth = 0, 0
    ym = _extract_yyyymm_from_filename(cost_xls)
    if ym:
        y, mth = ym

    def norm(s) -> str:
        if s is None or (isinstance(s, float) and pd.isna(s)):
            return ""
        # 모든 공백 제거(예: '2.노  무  비' → '2.노무비')
        return "".join(str(s).split())

    H = 7  # H열 (0-index)

    def pick_total(col0_key: str, col1_key: Optional[str]) -> int:
        """
        col0, col1을 기준으로 '합계/소계' 행(계정/설명 없음)을 찾아 H열 값을 반환.
        - col0_key: 예) '2.노무비', '3.경비'
        - col1_key: 예) '1)수도광열비', '4)감가상각비', 또는 None(대분류 합계)
        """
        if df.empty:
            return 0

        for r in range(df.shape[0]):
            c0 = norm(df.iat[r, 0]) if df.shape[1] > 0 else ""
            c1 = norm(df.iat[r, 1]) if df.shape[1] > 1 else ""
            c2 = norm(df.iat[r, 2]) if df.shape[1] > 2 else ""

            if col0_key not in c0:
                continue
            if col1_key is None:
                # 대분류 합계: col1, col2가 비어있는 행
                if c1 != "" or c2 != "":
                    continue
                return _to_int(df.iat[r, H]) if df.shape[1] > H else 0
            else:
                # 중분류 합계: col1이 해당 키워드이고, 계정/내역(보통 col3/col4)이 비어있는 행을 우선
                if col1_key not in c1:
                    continue
                # 계정/내역이 비어있는지 확인(포맷 차이를 고려해 col3, col4 둘 다 체크)
                c3 = norm(df.iat[r, 3]) if df.shape[1] > 3 else ""
                c4 = norm(df.iat[r, 4]) if df.shape[1] > 4 else ""
                if c3 == "" and c4 == "":
                    return _to_int(df.iat[r, H]) if df.shape[1] > H else 0

        # 못 찾으면 0
        return 0

    return {
        "KPI_노무비": pick_total("2.노무비", None),
        "KPI_경비": pick_total("3.경비", None),
        "KPI_경비_수도광열비": pick_total("3.경비", "1)수도광열비"),
        "KPI_경비_감가상각비": pick_total("3.경비", "4)감가상각비"),
    }


# ---------------------------
# 4) 메인 실행
# ---------------------------

def main() -> None:
    base_dir = Path(__file__).resolve().parent
    extract_dir = base_dir / "for_extract"
    extract_dir.mkdir(exist_ok=True)

    db_monthly = base_dir / "DB.csv"
    db_product = base_dir / "DB_product.csv"

    # 파일 탐색
    downloads = sorted(extract_dir.glob("품목별_제조이익*.xlsx"))
    factories = sorted(extract_dir.glob("공장별_제조이익*.xlsx"))
    cost_statements = sorted(list(extract_dir.glob("제조원가명세서*.xls")) + list(extract_dir.glob("제조원가명세서*.xlsx")))

    # 1) 품목별_제조이익 = 월 기준 마스터
    for f in downloads:
        df_prod = extract_products(f)
        _upsert_csv(db_product, df_prod, key_cols=["년", "월", "제품코드"])

    monthly_map = {}  # (년,월) -> dict
    
    # 2) 공장별_제조이익 = 월 기준 마스터
    for f in factories:
        row = extract_factory_monthly(f)
        key = (row["년"], row["월"])
        monthly_map[key] = row

    # 3) 제조원가명세서 = KPI 보조 (같은 달에 붙임)
    for f in cost_statements:
        kpi = extract_cost_statement_monthly(f)
        for key in monthly_map:
            monthly_map[key].update(kpi)
  
    # DB 저장
    if monthly_map:
        df_monthly = pd.DataFrame(monthly_map.values())
        _upsert_csv(db_monthly, df_monthly, key_cols=["년", "월"])


if __name__ == "__main__":
    main()
