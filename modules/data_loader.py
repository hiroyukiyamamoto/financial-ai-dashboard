"""
データ読み込み・検証・ヘルパーモジュール
CSVファイルの読み込み（UTF-8, UTF-8-BOM, CP932対応）、期名の抽出、バリデーションを提供します。
"""

import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd

# デフォルトパスの定義
BASE_DIR = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = BASE_DIR / "data" / "examples"
TEMPLATES_DIR = BASE_DIR / "data" / "templates"


def read_csv_flexible(source: Union[str, Path, io.BytesIO, io.StringIO]) -> pd.DataFrame:
    """
    文字コード（utf-8-sig, utf-8, cp932）を順次試行してCSVを読み込みます。
    ファイルパスおよびStreamlitのUploadedFileに対応。
    """
    encodings = ["utf-8-sig", "utf-8", "cp932"]
    
    if isinstance(source, (str, Path)):
        for enc in encodings:
            try:
                return pd.read_csv(source, encoding=enc)
            except (UnicodeDecodeError, Exception):
                continue
        # フォールバック
        return pd.read_csv(source, encoding="utf-8-sig", errors="replace")
    else:
        # UploadedFile または BytesIO の場合
        if hasattr(source, "getvalue"):
            raw_bytes = source.getvalue()
        elif hasattr(source, "read"):
            raw_bytes = source.read()
            if hasattr(source, "seek"):
                source.seek(0)
        else:
            raw_bytes = bytes(source)

        for enc in encodings:
            try:
                text = raw_bytes.decode(enc)
                return pd.read_csv(io.StringIO(text))
            except (UnicodeDecodeError, Exception):
                continue

        text = raw_bytes.decode("utf-8", errors="replace")
        return pd.read_csv(io.StringIO(text))


def get_periods_from_pl(df_pl: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """損益計算書から前期・当期のカラム名を抽出（最後の2期分）"""
    cols = [c for c in df_pl.columns if str(c).strip() != "項目"]
    if len(cols) >= 2:
        return cols[-2], cols[-1]
    elif len(cols) == 1:
        return None, cols[0]
    return None, None


def get_periods_from_bs(df_bs: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """貸借対照表から前期・当期のカラム名を抽出（最後の2期分）"""
    cols = [c for c in df_bs.columns if str(c).strip() not in ["区分", "項目"]]
    if len(cols) >= 2:
        return cols[-2], cols[-1]
    elif len(cols) == 1:
        return None, cols[0]
    return None, None


def get_pl_val(df_pl: pd.DataFrame, item: str, period: str) -> float:
    """指定された項目の損益計算書数値を安全に取得"""
    if df_pl is None or period not in df_pl.columns or "項目" not in df_pl.columns:
        return 0.0
    matched = df_pl[df_pl["項目"].astype(str).str.strip() == item.strip()]
    if not matched.empty:
        val = matched[period].values[0]
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def get_bs_val(df_bs: pd.DataFrame, item: str, period: str) -> float:
    """指定された項目の貸借対照表数値を安全に取得"""
    if df_bs is None or period not in df_bs.columns or "項目" not in df_bs.columns:
        return 0.0
    matched = df_bs[df_bs["項目"].astype(str).str.strip() == item.strip()]
    if not matched.empty:
        val = matched[period].values[0]
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def format_currency_oku(val: float) -> str:
    """千円単位の数値を「〇.〇億円」に整形"""
    if pd.isna(val):
        return "N/A"
    oku = val / 100000.0
    return f"{oku:,.1f}億円"


def format_currency_sen_yen(val: float) -> str:
    """千円単位の数値をカンマ区切りに整形"""
    if pd.isna(val):
        return "N/A"
    return f"{int(round(val)):,}千円"


def format_percent(val: float, digits: int = 1) -> str:
    """パーセント表示に整形"""
    if pd.isna(val):
        return "N/A"
    return f"{val:.{digits}f}%"


def load_example_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """同梱のサンプルデータ（株式会社サンプルテック）を読み込む"""
    pl_path = EXAMPLES_DIR / "input_pl.csv"
    bs_path = EXAMPLES_DIR / "input_bs.csv"
    sum_path = EXAMPLES_DIR / "input_summary.csv"
    
    df_pl = read_csv_flexible(pl_path)
    df_bs = read_csv_flexible(bs_path)
    df_summary = read_csv_flexible(sum_path)
    return df_pl, df_bs, df_summary


def load_template_bytes() -> Dict[str, bytes]:
    """空のテンプレートCSVのバイナリ（ダウンロード用、UTF-8 BOM付き）を取得"""
    templates = {}
    for filename in ["input_pl.csv", "input_bs.csv", "input_summary.csv"]:
        path = TEMPLATES_DIR / filename
        if path.exists():
            templates[filename] = path.read_bytes()
        else:
            templates[filename] = b""
    return templates


def validate_data(df_pl: pd.DataFrame, df_bs: pd.DataFrame, df_summary: pd.DataFrame) -> List[str]:
    """データ構造の検証。不足している必須項目や形式異常があれば警告メッセージリストを返す"""
    warnings = []
    
    # PL チェック
    if "項目" not in df_pl.columns:
        warnings.append("損益計算書 (P/L) に '項目' カラムが見つかりません。")
    else:
        req_pl_items = ["売上高", "営業利益", "当期純利益"]
        items_pl = df_pl["項目"].astype(str).str.strip().tolist()
        for item in req_pl_items:
            if item not in items_pl:
                warnings.append(f"損益計算書に主要項目 '{item}' が含まれていません。")
                
    # BS チェック
    if "項目" not in df_bs.columns or "区分" not in df_bs.columns:
        warnings.append("貸借対照表 (B/S) に '区分' または '項目' カラムが見つかりません。")
    else:
        req_bs_items = ["資産合計", "負債合計", "純資産合計"]
        items_bs = df_bs["項目"].astype(str).str.strip().tolist()
        for item in req_bs_items:
            if item not in items_bs:
                warnings.append(f"貸借対照表に主要項目 '{item}' が含まれていません。")
                
    # Summary チェック
    req_summary_cols = ["決算年月", "売上高", "経常利益", "当期純利益", "純資産", "総資産"]
    for col in req_summary_cols:
        if col not in df_summary.columns:
            warnings.append(f"複数期サマリーにカラム '{col}' が含まれていません。")
            
    return warnings
