"""
スタンドアロンHTML財務レポート生成・エクスポートモジュール
ブラウザ単体で閲覧可能なインタラクティブHTMLレポートを出力します。
"""

from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
import plotly.io as pio

from .metrics import FinancialMetrics, evaluate_financial_health
from .charts import (
    plot_summary_trends,
    plot_roe_equity_trend,
    plot_eps_trend,
    plot_waterfall_pl,
    plot_margin_comparison,
    plot_cost_structure,
    plot_asset_stacked,
    plot_liab_stacked,
    plot_financial_health_ratios,
    plot_total_assets_trend,
    plot_dupont_factors,
    plot_bep_analysis,
    plot_health_radar
)


def generate_html_report(
    company_name: str,
    m: FinancialMetrics,
    df_pl: pd.DataFrame,
    df_bs: pd.DataFrame,
    df_summary: pd.DataFrame,
    ai_comments: Dict[str, Dict[str, Any]],
    health_eval: Dict[str, Any]
) -> str:
    """スタンドアロンHTMLレポートを文字列として生成"""
    now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    # チャートをHTMLスニペット化
    fig_trends = plot_summary_trends(df_summary)
    fig_roe = plot_roe_equity_trend(df_summary)
    fig_eps = plot_eps_trend(df_summary)
    fig_wf = plot_waterfall_pl(df_pl, m.period_curr)
    fig_margins = plot_margin_comparison(df_pl, m.period_prev, m.period_curr)
    fig_cost = plot_cost_structure(df_pl, m.period_curr)
    fig_asset = plot_asset_stacked(df_bs, m.period_prev, m.period_curr)
    fig_liab = plot_liab_stacked(df_bs, m.period_prev, m.period_curr)
    fig_health = plot_financial_health_ratios(m)
    fig_total_assets = plot_total_assets_trend(df_summary)
    fig_dupont = plot_dupont_factors(m)
    fig_bep = plot_bep_analysis(m)
    fig_radar = plot_health_radar(health_eval["scores"])

    h_trends = pio.to_html(fig_trends, full_html=False, include_plotlyjs="cdn")
    h_roe = pio.to_html(fig_roe, full_html=False, include_plotlyjs=False)
    h_eps = pio.to_html(fig_eps, full_html=False, include_plotlyjs=False)
    h_wf = pio.to_html(fig_wf, full_html=False, include_plotlyjs=False)
    h_margins = pio.to_html(fig_margins, full_html=False, include_plotlyjs=False)
    h_cost = pio.to_html(fig_cost, full_html=False, include_plotlyjs=False)
    h_asset = pio.to_html(fig_asset, full_html=False, include_plotlyjs=False)
    h_liab = pio.to_html(fig_liab, full_html=False, include_plotlyjs=False)
    h_health = pio.to_html(fig_health, full_html=False, include_plotlyjs=False)
    h_total_assets = pio.to_html(fig_total_assets, full_html=False, include_plotlyjs=False)
    h_dupont = pio.to_html(fig_dupont, full_html=False, include_plotlyjs=False)
    h_bep = pio.to_html(fig_bep, full_html=False, include_plotlyjs=False)
    h_radar = pio.to_html(fig_radar, full_html=False, include_plotlyjs=False)

    def render_ai_box(comment_dict: Optional[Dict[str, Any]], title: str) -> str:
        if not comment_dict:
            return ""
        text = comment_dict.get("text", "")
        source = comment_dict.get("source", "")
        return f"""
        <div style="background:#eef6fb; border-left:4px solid #2c7bb6; padding:16px 20px; border-radius:6px; margin:16px 0; font-size:14px; line-height:1.8;">
            <div style="font-weight:bold; color:#1f5380; font-size:15px; margin-bottom:8px;">🤖 {title}</div>
            <div style="white-space:pre-wrap; color:#2c3e50;">{text}</div>
            <div style="margin-top:10px; font-size:11px; color:#7f8c8d;">出典: {source}</div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>財務分析ダッシュボード｜{company_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", "Meiryo", sans-serif;
            background-color: #f8f9fa;
            color: #333;
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1240px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #1f4068, #162447);
            color: white;
            padding: 24px 32px;
            border-radius: 10px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header .subtitle {{ opacity: 0.85; font-size: 13px; margin-top: 4px; }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: white;
            padding: 16px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border-top: 4px solid #2c7bb6;
        }}
        .kpi-card.sub {{ border-top-color: #f77f00; }}
        .kpi-card.pos {{ border-top-color: #1a9641; }}
        .kpi-title {{ font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 6px; }}
        .kpi-value {{ font-size: 24px; font-weight: bold; color: #222; }}
        .section {{
            background: white;
            padding: 24px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            margin-bottom: 24px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: bold;
            color: #162447;
            border-bottom: 2px solid #eaeaea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .chart-grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 900px) {{
            .chart-grid-2 {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>📊 財務分析ダッシュボード｜{company_name}</h1>
                <div class="subtitle">比較対象期: 前期 ({m.period_prev}) → 当期 ({m.period_curr}) ｜ 作成日時: {now_str}</div>
            </div>
            <div>
                <span style="background: rgba(255,255,255,0.2); padding: 6px 14px; border-radius: 20px; font-size: 12px;">総合診断: {health_eval['grade']}</span>
            </div>
        </div>

        <!-- KPI グリッド -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">当期売上高</div>
                <div class="kpi-value">{m.rev_curr/100000:.1f}億円</div>
            </div>
            <div class="kpi-card sub">
                <div class="kpi-title">売上総利益率</div>
                <div class="kpi-value">{m.gp_margin_curr:.1f}%</div>
            </div>
            <div class="kpi-card pos">
                <div class="kpi-title">営業利益率</div>
                <div class="kpi-value">{m.op_margin_curr:.1f}%</div>
            </div>
            <div class="kpi-card pos">
                <div class="kpi-title">当期純利益率</div>
                <div class="kpi-value">{m.ni_margin_curr:.1f}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">自己資本比率</div>
                <div class="kpi-value">{m.equity_ratio_curr:.1f}%</div>
            </div>
            <div class="kpi-card sub">
                <div class="kpi-title">ROE</div>
                <div class="kpi-value">{m.roe_curr:.1f}%</div>
            </div>
        </div>

        <!-- 業績サマリー -->
        <div class="section">
            <div class="section-title">1. 業績サマリー & トレンド</div>
            {render_ai_box(ai_comments.get('summary'), 'AI アナリスト総合コメント（業績サマリー）')}
            <div class="chart-grid-2">
                <div>{h_trends}</div>
                <div>{h_roe}</div>
            </div>
            <div style="margin-top: 20px;">{h_eps}</div>
        </div>

        <!-- 損益計算書 (PL) -->
        <div class="section">
            <div class="section-title">2. 損益計算書 (P/L) 分析</div>
            {render_ai_box(ai_comments.get('pl'), 'AI 損益アナリストコメント')}
            <div class="chart-grid-2">
                <div>{h_wf}</div>
                <div>{h_margins}</div>
            </div>
            <div style="margin-top: 20px;">{h_cost}</div>
        </div>

        <!-- 貸借対照表 (BS) -->
        <div class="section">
            <div class="section-title">3. 貸借対照表 (B/S) 分析</div>
            {render_ai_box(ai_comments.get('bs'), 'AI 貸借対照表コメント')}
            <div class="chart-grid-2">
                <div>{h_asset}</div>
                <div>{h_liab}</div>
            </div>
            <div class="chart-grid-2" style="margin-top: 20px;">
                <div>{h_health}</div>
                <div>{h_total_assets}</div>
            </div>
        </div>

        <!-- デュポン分析 & 健全性格付け -->
        <div class="section">
            <div class="section-title">4. デュポン分析 & 財務健全性スコア診断</div>
            <div class="chart-grid-2">
                <div>{h_dupont}</div>
                <div>{h_radar}</div>
            </div>
            <div style="margin-top: 20px;">{h_bep}</div>
            <div style="background:#f1f8e9; border-left:4px solid #689f38; padding:16px; border-radius:6px; margin-top:20px;">
                <div style="font-weight:bold; color:#33691e; margin-bottom:8px;">📋 ルールベース自動財務診断レポート（スコア: {health_eval['total_score']}点 / 判定: {health_eval['grade']}）</div>
                <div style="white-space:pre-wrap; line-height:1.7;">{health_eval['summary_text']}</div>
            </div>
        </div>

        <div style="text-align: center; color: #888; font-size: 12px; margin-top: 30px;">
            財務AIダッシュボード (Life Science Financial Analytics) ｜ Generated by Python + Plotly
        </div>
    </div>
</body>
</html>
"""
    return html
