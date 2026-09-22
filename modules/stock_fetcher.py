"""
企業名・銘柄コードからの財務データ自動取得モジュール
Yahoo Finance (yfinance) および検索を活用し、実在企業の財務データを自動整形して提供します。
"""

import re
from typing import Optional, Tuple
import pandas as pd
import requests
import yfinance as yf


def resolve_ticker(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    入力文字列（4桁数字、7203.T、または企業名）から銘柄シンボルと企業名を特定します。
    戻り値: (ticker_symbol, detected_name)
    """
    if not query or not query.strip():
        return None, None
        
    q = query.strip()
    
    # 1. 4桁の日本銘柄コード（例: 7203, 4502, 4519）
    if re.match(r"^\d{4}$", q):
        return f"{q}.T", None
        
    # 2. すでに .T 付き（例: 7203.T）
    if re.match(r"^\d{4}\.[tT]$", q):
        return q.upper(), None
        
    # 3. 米国株シンボル（例: AAPL, MSFT, PFE）
    if re.match(r"^[A-Za-z]{1,5}$", q):
        return q.upper(), None

    # 4. 文字列中に4桁コードが含まれている場合（例: "トヨタ (7203)"）
    code_match = re.search(r"\b(\d{4})\b", q)
    if code_match:
        return f"{code_match.group(1)}.T", None

    # 5. 日本語企業名検索（Yahoo!ファイナンス検索から抽出）
    try:
        url = "https://finance.yahoo.co.jp/search/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, params={"query": q}, headers=headers, timeout=5)
        if resp.status_code == 200:
            matches = re.findall(r"/quote/(\d{4}\.T)", resp.text)
            if matches:
                return matches[0], None
    except Exception:
        pass

    # 6. yfinance.Search によるフォールバック検索
    try:
        s = yf.Search(q)
        if s.quotes:
            symbol = s.quotes[0].get("symbol")
            shortname = s.quotes[0].get("shortname")
            return symbol, shortname
    except Exception:
        pass

    return None, None


def fetch_company_financials(query: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], str]:
    """
    銘柄コードまたは企業名から P/L, B/S, Summary データを生成して返します。
    戻り値: (df_pl, df_bs, df_summary, display_name)
    """
    symbol, detected_name = resolve_ticker(query)
    if not symbol:
        raise ValueError(f"『{query}』に対応する銘柄コードを特定できませんでした。4桁の証券コード（例: 7203, 4502）等をお試しください。")


    t = yf.Ticker(symbol)
    fin = t.financials
    bs = t.balance_sheet
    info = t.info or {}

    if fin is None or fin.empty or bs is None or bs.empty:
        raise ValueError(f"銘柄『{symbol}』の財務諸表データを取得できませんでした。上場企業かご確認ください。")

    # 企業名の決定
    comp_name = (
        info.get("longName")
        or info.get("shortName")
        or detected_name
        or query
    )
    # 日本企業の場合はコードも添える
    if symbol.endswith(".T"):
        code = symbol.replace(".T", "")
        display_name = f"{comp_name} ({code})"
    else:
        display_name = f"{comp_name} ({symbol})"

    # 共通の期カラム（日付）を古い順（昇順）に並べ替え
    common_cols = [c for c in fin.columns if c in bs.columns]
    if len(common_cols) < 2:
        common_cols = list(fin.columns)
    common_cols = sorted(common_cols)

    # 過去データで全てゼロのカラムは除外
    valid_cols = []
    for c in common_cols:
        rev = fin.loc["Total Revenue", c] if "Total Revenue" in fin.index else 0
        if pd.notnull(rev) and rev > 0:
            valid_cols.append(c)
    if len(valid_cols) >= 2:
        common_cols = valid_cols

    period_names = [c.strftime("%Y年%m月期") for c in common_cols]

    def get_val(df: pd.DataFrame, keys: list, col, default=0.0) -> float:
        for k in keys:
            if k in df.index and col in df.columns:
                val = df.loc[k, col]
                if pd.notnull(val):
                    # yfinanceは円単位。bidashは千円単位のため1,000で割る
                    return float(val) / 1000.0
        return default

    # 1. 損益計算書 (df_pl) の作成
    pl_definitions = [
        ("売上高", ["Total Revenue", "Operating Revenue"]),
        ("売上原価", ["Cost Of Revenue", "Reconciled Cost Of Revenue"]),
        ("売上総利益", ["Gross Profit"]),
        ("販売費及び一般管理費", ["Operating Expense"]),
        ("営業利益", ["Operating Income", "Total Operating Income As Reported"]),
        ("営業外収益合計", ["Interest Income Non Operating"]),
        ("営業外費用合計", ["Interest Expense Non Operating"]),
        ("経常利益", ["Pretax Income"]),
        ("特別利益合計", ["Special Income Charges"]),
        ("特別損失合計", ["Write Off", "Other Special Charges"]),
        ("税金等調整前当期純利益", ["Pretax Income"]),
        ("法人税等合計", ["Tax Provision"]),
        ("当期純利益", ["Net Income", "Net Income Common Stockholders"]),
    ]

    pl_rows = []
    for item_name, keys in pl_definitions:
        row = {"項目": item_name}
        for col, pname in zip(common_cols, period_names):
            val = get_val(fin, keys, col)
            row[pname] = val
        pl_rows.append(row)

    df_pl = pd.DataFrame(pl_rows)

    # 補正: 売上総利益がゼロなら 売上 - 原価
    for pname in period_names:
        rev = df_pl.loc[df_pl["項目"] == "売上高", pname].values[0]
        cogs = df_pl.loc[df_pl["項目"] == "売上原価", pname].values[0]
        gp = df_pl.loc[df_pl["項目"] == "売上総利益", pname].values[0]
        if gp == 0 and rev > 0 and cogs > 0:
            df_pl.loc[df_pl["項目"] == "売上総利益", pname] = rev - cogs

        # 販管費がゼロなら 粗利 - 営業利益
        op = df_pl.loc[df_pl["項目"] == "営業利益", pname].values[0]
        sga = df_pl.loc[df_pl["項目"] == "販売費及び一般管理費", pname].values[0]
        if sga == 0 and gp > 0 and op != 0:
            df_pl.loc[df_pl["項目"] == "販売費及び一般管理費", pname] = max(gp - op, 0)

    # 2. 貸借対照表 (df_bs) の作成
    bs_definitions = [
        ("資産", "流動資産合計", ["Current Assets"]),
        ("資産", "現金及び預金", ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"]),
        ("資産", "売掛金", ["Accounts Receivable", "Gross Accounts Receivable"]),
        ("資産", "その他流動資産", ["Other Current Assets"]),
        ("資産", "固定資産合計", ["Total Non Current Assets"]),
        ("資産", "有形固定資産", ["Net PPE"]),
        ("資産", "無形固定資産", ["Goodwill And Other Intangible Assets"]),
        ("資産", "投資その他の資産", ["Other Non Current Assets", "Investmentin Financial Assets"]),
        ("資産", "資産合計", ["Total Assets"]),
        ("負債", "流動負債合計", ["Current Liabilities"]),
        ("負債", "固定負債合計", ["Total Non Current Liabilities Net Minority Interest"]),
        ("負債", "負債合計", ["Total Liabilities Net Minority Interest"]),
        ("純資産", "株主資本合計", ["Stockholders Equity", "Common Stock Equity"]),
        ("純資産", "新株予約権", ["Other Equity Interest"]),
        ("純資産", "純資産合計", ["Stockholders Equity", "Total Equity Gross Minority Interest"]),
        ("純資産", "負債純資産合計", ["Total Assets"]),
    ]

    bs_rows = []
    for cat, item_name, keys in bs_definitions:
        row = {"区分": cat, "項目": item_name}
        for col, pname in zip(common_cols, period_names):
            val = get_val(bs, keys, col)
            row[pname] = val
        bs_rows.append(row)

    df_bs = pd.DataFrame(bs_rows)

    # 3. 複数期サマリー (df_summary) の作成
    summary_rows = []
    for idx, (col, pname) in enumerate(zip(common_cols, period_names), 1):
        ym = col.strftime("%Y/%m")
        rev = get_val(fin, ["Total Revenue", "Operating Revenue"], col)
        ord_inc = get_val(fin, ["Pretax Income"], col)
        ni = get_val(fin, ["Net Income", "Net Income Common Stockholders"], col)
        ta = get_val(bs, ["Total Assets"], col)
        eq = get_val(bs, ["Stockholders Equity", "Common Stock Equity"], col)
        
        eq_ratio = (eq / ta * 100.0) if ta > 0 else 0.0
        roe = (ni / eq * 100.0) if eq > 0 else 0.0

        # EPS (yfinanceは円単位)
        eps = 0.0
        if "Diluted EPS" in fin.index and col in fin.columns and pd.notnull(fin.loc["Diluted EPS", col]):
            eps = float(fin.loc["Diluted EPS", col])
        elif "Basic EPS" in fin.index and col in fin.columns and pd.notnull(fin.loc["Basic EPS", col]):
            eps = float(fin.loc["Basic EPS", col])
        elif eq > 0 and ni != 0:
            eps = roe # 近似

        summary_rows.append({
            "期": f"第{idx}期",
            "決算年月": ym,
            "売上高": rev,
            "経常利益": ord_inc,
            "当期純利益": ni,
            "純資産": eq,
            "総資産": ta,
            "自己資本比率": round(eq_ratio, 1),
            "ROE": round(roe, 1),
            "EPS": round(eps, 2)
        })

    df_summary = pd.DataFrame(summary_rows)

    return df_pl, df_bs, df_summary, display_name
