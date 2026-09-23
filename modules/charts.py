"""
Plotlyによる財務データ可視化モジュール
bidashのグラフを忠実に再現し、さらにデュポン分析・損益分岐点・財務レーダーなどの新チャートを提供します。
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from .metrics import FinancialMetrics
from .data_loader import get_pl_val, get_bs_val

# カラーパレットの統一（bidash / Rmd と同一）
COL_MAIN = "#2c7bb6"       # メインブルー
COL_SUB = "#f77f00"        # オレンジ
COL_POS = "#1a9641"        # ポジティブグリーン
COL_NEG = "#d73027"        # ネガティブレッド
COL_NEUTRAL = "#999999"    # ニュートラルグレー
COL_LIGHT_BLUE = "#aec7e8" # ライトブルー
BG_PLOT = "rgba(0,0,0,0)"

TEMPLATE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Noto Sans JP, Meiryo, sans-serif", size=12),
    margin=dict(t=35, b=25, l=40, r=20),
    hovermode="x unified",
)


def plot_summary_trends(df_summary: pd.DataFrame) -> go.Figure:
    """売上高・利益トレンド（棒グラフ＋折れ線グラフ）"""
    fig = go.Figure()
    
    x_vals = df_summary["決算年月"] if "決算年月" in df_summary.columns else df_summary.iloc[:, 0]
    
    if "売上高" in df_summary.columns:
        fig.add_trace(go.Bar(
            x=x_vals, y=df_summary["売上高"],
            name="売上高",
            marker=dict(color=COL_MAIN)
        ))
    if "経常利益" in df_summary.columns:
        fig.add_trace(go.Scatter(
            x=x_vals, y=df_summary["経常利益"],
            name="経常利益",
            mode="lines+markers",
            line=dict(color=COL_SUB, width=3),
            marker=dict(size=8)
        ))
    if "当期純利益" in df_summary.columns:
        fig.add_trace(go.Scatter(
            x=x_vals, y=df_summary["当期純利益"],
            name="当期純利益",
            mode="lines+markers",
            line=dict(color=COL_POS, width=3),
            marker=dict(size=8)
        ))
        
    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>売上高・利益トレンド</b>", font=dict(size=14)),
        yaxis=dict(title="千円", tickformat=",d", gridcolor="#e5e5e5"),
        xaxis=dict(gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
    )
    return fig


def plot_roe_equity_trend(df_summary: pd.DataFrame) -> go.Figure:
    """ROE・自己資本比率トレンド"""
    fig = go.Figure()
    x_vals = df_summary["決算年月"] if "決算年月" in df_summary.columns else df_summary.iloc[:, 0]
    
    if "ROE" in df_summary.columns:
        fig.add_trace(go.Scatter(
            x=x_vals, y=df_summary["ROE"],
            name="ROE (%)",
            mode="lines+markers",
            line=dict(color=COL_SUB, width=3),
            marker=dict(size=8)
        ))
    if "自己資本比率" in df_summary.columns:
        fig.add_trace(go.Scatter(
            x=x_vals, y=df_summary["自己資本比率"],
            name="自己資本比率 (%)",
            mode="lines+markers",
            line=dict(color=COL_MAIN, width=3),
            marker=dict(size=8)
        ))
        
    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>ROE・自己資本比率トレンド</b>", font=dict(size=14)),
        yaxis=dict(title="%", range=[0, 100], gridcolor="#e5e5e5"),
        xaxis=dict(gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
    )
    return fig


def plot_eps_trend(df_summary: pd.DataFrame) -> go.Figure:
    """EPS（1株当たり利益）トレンド"""
    fig = go.Figure()
    x_vals = df_summary["決算年月"] if "決算年月" in df_summary.columns else df_summary.iloc[:, 0]
    
    if "EPS" in df_summary.columns:
        fig.add_trace(go.Bar(
            x=x_vals, y=df_summary["EPS"],
            name="EPS",
            marker=dict(color=COL_MAIN)
        ))
    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>EPSトレンド</b>", font=dict(size=14)),
        yaxis=dict(title="円", gridcolor="#e5e5e5"),
        xaxis=dict(gridcolor="#e5e5e5"),
        showlegend=False
    )
    return fig


def plot_waterfall_pl(df_pl: pd.DataFrame, period_curr: str) -> go.Figure:
    """当期利益構造ウォーターフォール"""
    rev = get_pl_val(df_pl, "売上高", period_curr)
    cogs = get_pl_val(df_pl, "売上原価", period_curr)
    sga = get_pl_val(df_pl, "販売費及び一般管理費", period_curr)
    non_op_inc = get_pl_val(df_pl, "営業外収益合計", period_curr)
    non_op_exp = get_pl_val(df_pl, "営業外費用合計", period_curr)
    non_op_net = non_op_inc - non_op_exp
    sp_inc = get_pl_val(df_pl, "特別利益合計", period_curr)
    sp_exp = get_pl_val(df_pl, "特別損失合計", period_curr)
    sp_net = sp_inc - sp_exp

    x_labels = [
        "売上高", "売上原価", "売上総利益", "販管費", "営業利益",
        "営業外(純)", "経常利益", "特別損益(純)", "純利益"
    ]
    y_vals = [
        rev, -cogs, 0, -sga, 0,
        non_op_net, 0, sp_net, 0
    ]
    measures = [
        "absolute", "relative", "total", "relative", "total",
        "relative", "total", "relative", "total"
    ]

    fig = go.Figure(go.Waterfall(
        name="利益構造",
        orientation="v",
        measure=measures,
        x=x_labels,
        y=y_vals,
        connector=dict(line=dict(color="#aaaaaa")),
        increasing=dict(marker=dict(color=COL_POS)),
        decreasing=dict(marker=dict(color=COL_NEG)),
        totals=dict(marker=dict(color=COL_MAIN)),
        textposition="outside",
        texttemplate="%{y:,.0f}"
    ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text=f"<b>利益構造ウォーターフォール（{period_curr}）</b>", font=dict(size=14)),
        yaxis=dict(title="千円", tickformat=",d", gridcolor="#e5e5e5"),
        showlegend=False
    )
    return fig


def plot_margin_comparison(df_pl: pd.DataFrame, period_prev: str, period_curr: str) -> go.Figure:
    """利益率比較（前期→当期 水平バー）"""
    rev_prev = get_pl_val(df_pl, "売上高", period_prev)
    rev_curr = get_pl_val(df_pl, "売上高", period_curr)
    
    labels = ["売上総利益率", "営業利益率", "経常利益率", "純利益率"]
    items = ["売上総利益", "営業利益", "経常利益", "当期純利益"]
    
    prev_rates = [(get_pl_val(df_pl, i, period_prev) / rev_prev * 100.0) if rev_prev != 0 else 0.0 for i in items]
    curr_rates = [(get_pl_val(df_pl, i, period_curr) / rev_curr * 100.0) if rev_curr != 0 else 0.0 for i in items]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=prev_rates,
        name=period_prev,
        orientation="h",
        marker=dict(color=COL_NEUTRAL),
        text=[f"{r:.1f}%" for r in prev_rates],
        textposition="auto"
    ))
    fig.add_trace(go.Bar(
        y=labels, x=curr_rates,
        name=period_curr,
        orientation="h",
        marker=dict(color=COL_MAIN),
        text=[f"{r:.1f}%" for r in curr_rates],
        textposition="auto"
    ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>利益率比較（前期 vs 当期）</b>", font=dict(size=14)),
        barmode="group",
        xaxis=dict(title="%", ticksuffix="%", gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
    )
    return fig


def plot_cost_structure(df_pl: pd.DataFrame, period_curr: str) -> go.Figure:
    """費用構造ドーナツチャート"""
    cogs = get_pl_val(df_pl, "売上原価", period_curr)
    sga = get_pl_val(df_pl, "販売費及び一般管理費", period_curr)
    op = get_pl_val(df_pl, "営業利益", period_curr)

    labels = ["売上原価", "販管費", "営業利益"]
    values = [max(cogs, 0), max(sga, 0), max(op, 0)]
    colors = [COL_NEG, COL_NEUTRAL, COL_POS]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors),
        textinfo="label+percent"
    ))
    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text=f"<b>費用構造（{period_curr}）</b>", font=dict(size=14)),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center")
    )
    return fig


def plot_asset_stacked(df_bs: pd.DataFrame, period_prev: str, period_curr: str) -> go.Figure:
    """資産構成の変化（スタックバー）"""
    items = ["現金及び預金", "売掛金", "その他流動資産", "有形固定資産", "無形固定資産", "投資その他の資産"]
    palette = ["#2166ac", "#4393c3", "#92c5de", "#f4a582", "#d6604d", "#b2182b"]
    
    fig = go.Figure()
    for idx, item in enumerate(items):
        v_prev = get_bs_val(df_bs, item, period_prev)
        v_curr = get_bs_val(df_bs, item, period_curr)
        fig.add_trace(go.Bar(
            x=[period_prev, period_curr],
            y=[v_prev, v_curr],
            name=item,
            marker=dict(color=palette[idx % len(palette)])
        ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>資産構成の変化</b>", font=dict(size=14)),
        barmode="stack",
        yaxis=dict(title="千円", tickformat=",d", gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center")
    )
    return fig


def plot_liab_stacked(df_bs: pd.DataFrame, period_prev: str, period_curr: str) -> go.Figure:
    """負債・純資産構成の変化（スタックバー）"""
    items = ["流動負債合計", "固定負債合計", "株主資本合計", "新株予約権"]
    palette = ["#d73027", "#fc8d59", "#1a9641", "#fdae61"]

    fig = go.Figure()
    for idx, item in enumerate(items):
        v_prev = get_bs_val(df_bs, item, period_prev)
        v_curr = get_bs_val(df_bs, item, period_curr)
        fig.add_trace(go.Bar(
            x=[period_prev, period_curr],
            y=[v_prev, v_curr],
            name=item,
            marker=dict(color=palette[idx % len(palette)])
        ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>負債・純資産構成の変化</b>", font=dict(size=14)),
        barmode="stack",
        yaxis=dict(title="千円", tickformat=",d", gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center")
    )
    return fig


def plot_financial_health_ratios(m: FinancialMetrics) -> go.Figure:
    """財務健全性指標（水平バーチャート）"""
    labels = ["流動比率", "自己資本比率", "負債比率", "ROA", "ROE"]
    prev_vals = [m.cur_ratio_prev, m.equity_ratio_prev, m.debt_ratio_prev, m.roa_prev, m.roe_prev]
    curr_vals = [m.cur_ratio_curr, m.equity_ratio_curr, m.debt_ratio_curr, m.roa_curr, m.roe_curr]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=prev_vals,
        name=m.period_prev,
        orientation="h",
        marker=dict(color=COL_NEUTRAL),
        text=[f"{v:.1f}%" for v in prev_vals],
        textposition="auto"
    ))
    fig.add_trace(go.Bar(
        y=labels, x=curr_vals,
        name=m.period_curr,
        orientation="h",
        marker=dict(color=COL_MAIN),
        text=[f"{v:.1f}%" for v in curr_vals],
        textposition="auto"
    ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>財務健全性指標</b>", font=dict(size=14)),
        barmode="group",
        xaxis=dict(title="%", gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
    )
    return fig


def plot_total_assets_trend(df_summary: pd.DataFrame) -> go.Figure:
    """総資産・純資産トレンド（オーバーレイ棒グラフ）"""
    fig = go.Figure()
    x_vals = df_summary["決算年月"] if "決算年月" in df_summary.columns else df_summary.iloc[:, 0]
    
    if "総資産" in df_summary.columns:
        fig.add_trace(go.Bar(
            x=x_vals, y=df_summary["総資産"],
            name="総資産",
            marker=dict(color=COL_LIGHT_BLUE)
        ))
    if "純資産" in df_summary.columns:
        fig.add_trace(go.Bar(
            x=x_vals, y=df_summary["純資産"],
            name="純資産",
            marker=dict(color=COL_MAIN)
        ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>総資産・純資産トレンド</b>", font=dict(size=14)),
        barmode="overlay",
        yaxis=dict(title="千円", tickformat=",d", gridcolor="#e5e5e5"),
        xaxis=dict(gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
    )
    return fig


def plot_dupont_factors(m: FinancialMetrics) -> go.Figure:
    """デュポン分析（3要素比較チャート）"""
    factors = ["売上高当期純利益率 (%)", "総資産回転率 (回)", "財務レバレッジ (倍)"]
    prev_vals = [m.dupont_margin_prev, m.dupont_turnover_prev, m.dupont_leverage_prev]
    curr_vals = [m.dupont_margin_curr, m.dupont_turnover_curr, m.dupont_leverage_curr]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=factors, y=prev_vals,
        name=m.period_prev,
        marker=dict(color=COL_NEUTRAL),
        text=[f"{v:.2f}" for v in prev_vals],
        textposition="auto"
    ))
    fig.add_trace(go.Bar(
        x=factors, y=curr_vals,
        name=m.period_curr,
        marker=dict(color=COL_MAIN),
        text=[f"{v:.2f}" for v in curr_vals],
        textposition="auto"
    ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>デュポン分析（ROE分解要因: 収益性 × 効率性 × 財務体質）</b>", font=dict(size=14)),
        barmode="group",
        yaxis=dict(gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
    )
    return fig


def plot_bep_analysis(m: FinancialMetrics) -> go.Figure:
    """損益分岐点（BEP）と安全余裕率の可視化"""
    fig = go.Figure()
    
    # 売上高 vs 損益分岐点売上高
    fig.add_trace(go.Bar(
        x=["当期売上高", "損益分岐点売上高"],
        y=[m.rev_curr, m.bep_sales],
        marker=dict(color=[COL_MAIN, COL_SUB]),
        text=[f"{m.rev_curr:,.0f}千円", f"{m.bep_sales:,.0f}千円"],
        textposition="auto"
    ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text=f"<b>損益分岐点比較（安全余裕率: {m.safety_margin:.1f}%）</b>", font=dict(size=14)),
        yaxis=dict(title="千円", tickformat=",d", gridcolor="#e5e5e5"),
        showlegend=False
    )
    return fig


def plot_health_radar(scores: Dict[str, float]) -> go.Figure:
    """財務健全性レーダーチャート（4軸・各25点）"""
    categories = list(scores.keys())
    values = list(scores.values())
    
    # 閉じるために先頭を追加
    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor="rgba(44, 123, 182, 0.3)",
        line=dict(color=COL_MAIN, width=2),
        marker=dict(size=8, color=COL_MAIN)
    ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>財務総合スコア診断レーダー（各25点満点）</b>", font=dict(size=14)),
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 25], gridcolor="#e5e5e5")
        ),
        showlegend=False
    )
    return fig


def plot_comparison_radar(kpi_a: dict, kpi_b: dict) -> go.Figure:
    """2社財務5軸総合レーダーチャート（0-100スコア化）"""
    ma: FinancialMetrics = kpi_a["metrics"]
    mb: FinancialMetrics = kpi_b["metrics"]

    def normalize_scores(m: FinancialMetrics) -> List[float]:
        # 収益性: 営業利益率 (0% -> 20, 25%以上 -> 100)
        s_op = min(100.0, max(10.0, (m.op_margin_curr / 25.0) * 80.0 + 20.0))
        # 安全性: 自己資本比率 (0% -> 10, 80%以上 -> 100)
        s_eq = min(100.0, max(10.0, (m.equity_ratio_curr / 80.0) * 90.0 + 10.0))
        # 資本効率: ROE (0% -> 20, 18%以上 -> 100)
        s_roe = min(100.0, max(10.0, (m.roe_curr / 18.0) * 80.0 + 20.0))
        # 資産効率: 総資産回転率 (0 -> 10, 1.2回以上 -> 100)
        s_turn = min(100.0, max(10.0, (m.dupont_turnover_curr / 1.2) * 90.0 + 10.0))
        # 成長性: 売上成長率 (-10% -> 20, +20%以上 -> 100)
        s_grow = min(100.0, max(10.0, ((m.rev_growth_rate + 10.0) / 30.0) * 80.0 + 20.0))
        return [round(s_op, 1), round(s_eq, 1), round(s_roe, 1), round(s_turn, 1), round(s_grow, 1)]

    categories = ["収益性 (営業利益率)", "安全性 (自己資本比率)", "資本効率 (ROE)", "資産効率 (総資産回転率)", "成長性 (売上高成長率)"]
    
    vals_a = normalize_scores(ma)
    vals_b = normalize_scores(mb)
    
    cats_closed = categories + [categories[0]]
    vals_a_closed = vals_a + [vals_a[0]]
    vals_b_closed = vals_b + [vals_b[0]]

    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=vals_a_closed,
        theta=cats_closed,
        fill="toself",
        fillcolor="rgba(44, 123, 182, 0.35)",
        line=dict(color=COL_MAIN, width=2.5),
        name=kpi_a["name"],
        marker=dict(size=7, color=COL_MAIN)
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=vals_b_closed,
        theta=cats_closed,
        fill="toself",
        fillcolor="rgba(247, 127, 0, 0.35)",
        line=dict(color=COL_SUB, width=2.5),
        name=kpi_b["name"],
        marker=dict(size=7, color=COL_SUB)
    ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        title=dict(text="<b>⚔️ 2社 総合財務力レーダー比較（各軸100点換算）</b>", font=dict(size=14)),
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#e0e0e0")
        ),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center")
    )
    return fig


def plot_comparison_scale_bars(kpi_a: dict, kpi_b: dict) -> go.Figure:
    """2社の主要財務規模比較（売上・利益・資本）（億円換算）"""
    ma: FinancialMetrics = kpi_a["metrics"]
    mb: FinancialMetrics = kpi_b["metrics"]

    # 千円 -> 億円
    to_oku = lambda val: round(val / 100000.0, 1)

    labels = ["売上高", "営業利益", "当期純利益", "純資産 (自己資本)"]
    vals_a = [to_oku(ma.rev_curr), to_oku(ma.op_curr), to_oku(ma.ni_curr), to_oku(ma.eq_curr)]
    vals_b = [to_oku(mb.rev_curr), to_oku(mb.op_curr), to_oku(mb.ni_curr), to_oku(mb.eq_curr)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=vals_a,
        name=kpi_a["name"],
        marker=dict(color=COL_MAIN),
        text=[f"{v:,}億円" for v in vals_a],
        textposition="auto"
    ))
    fig.add_trace(go.Bar(
        x=labels, y=vals_b,
        name=kpi_b["name"],
        marker=dict(color=COL_SUB),
        text=[f"{v:,}億円" for v in vals_b],
        textposition="auto"
    ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        barmode="group",
        title=dict(text="<b>事業規模・利益創出力の直接比較（億円）</b>", font=dict(size=14)),
        yaxis=dict(title="億円", gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center")
    )
    return fig


def plot_comparison_margins(kpi_a: dict, kpi_b: dict) -> go.Figure:
    """2社の利益率・経営効率指標比較（%）"""
    ma: FinancialMetrics = kpi_a["metrics"]
    mb: FinancialMetrics = kpi_b["metrics"]

    labels = ["売上総利益率", "営業利益率", "当期純利益率", "自己資本比率", "ROE"]
    vals_a = [round(ma.gp_margin_curr, 1), round(ma.op_margin_curr, 1), round(ma.ni_margin_curr, 1), round(ma.equity_ratio_curr, 1), round(ma.roe_curr, 1)]
    vals_b = [round(mb.gp_margin_curr, 1), round(mb.op_margin_curr, 1), round(mb.ni_margin_curr, 1), round(mb.equity_ratio_curr, 1), round(mb.roe_curr, 1)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=vals_a,
        name=kpi_a["name"],
        marker=dict(color=COL_MAIN),
        text=[f"{v:+.1f}%" for v in vals_a],
        textposition="auto"
    ))
    fig.add_trace(go.Bar(
        x=labels, y=vals_b,
        name=kpi_b["name"],
        marker=dict(color=COL_SUB),
        text=[f"{v:+.1f}%" for v in vals_b],
        textposition="auto"
    ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        barmode="group",
        title=dict(text="<b>利益率・資本健全性指標の比較（%）</b>", font=dict(size=14)),
        yaxis=dict(title="%", gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center")
    )
    return fig


def plot_comparison_dupont(kpi_a: dict, kpi_b: dict) -> go.Figure:
    """2社のデュポン分析3要素比較"""
    ma: FinancialMetrics = kpi_a["metrics"]
    mb: FinancialMetrics = kpi_b["metrics"]

    fig = go.Figure()
    
    factors = ["① 売上高当期純利益率 (%)", "② 総資産回転率 (回)", "③ 財務レバレッジ (倍)"]
    vals_a = [round(ma.dupont_margin_curr, 1), round(ma.dupont_turnover_curr, 2), round(ma.dupont_leverage_curr, 2)]
    vals_b = [round(mb.dupont_margin_curr, 1), round(mb.dupont_turnover_curr, 2), round(mb.dupont_leverage_curr, 2)]

    fig.add_trace(go.Bar(
        name=kpi_a["name"],
        x=factors, y=vals_a,
        marker=dict(color=COL_MAIN),
        text=[f"{vals_a[0]}%", f"{vals_a[1]}回", f"{vals_a[2]}倍"],
        textposition="auto"
    ))
    fig.add_trace(go.Bar(
        name=kpi_b["name"],
        x=factors, y=vals_b,
        marker=dict(color=COL_SUB),
        text=[f"{vals_b[0]}%", f"{vals_b[1]}回", f"{vals_b[2]}倍"],
        textposition="auto"
    ))

    fig.update_layout(
        **TEMPLATE_LAYOUT,
        barmode="group",
        title=dict(text=f"<b>デュポン分析比較 (ROE: {ma.roe_curr:.1f}% vs {mb.roe_curr:.1f}%)</b>", font=dict(size=14)),
        yaxis=dict(gridcolor="#e5e5e5"),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center")
    )
    return fig

