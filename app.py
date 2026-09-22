"""
財務AIダッシュボード (Life Science Financial AI Dashboard)
aidash + bidash の完全統合 ＋ 新機能（デュポン分析、What-Ifシミュレーター、自動診断、HTMLレポート出力）
"""

import os
from pathlib import Path
import streamlit as st
import pandas as pd

from modules.data_loader import (
    load_example_data,
    load_template_bytes,
    read_csv_flexible,
    get_periods_from_pl,
    get_periods_from_bs,
    validate_data,
    format_currency_oku,
    format_currency_sen_yen,
    format_percent,
)
from modules.metrics import (
    calculate_metrics,
    evaluate_financial_health,
)
from modules.charts import (
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
    plot_health_radar,
)
from modules.ai_service import (
    generate_all_comments,
    RECOMMENDED_MODELS,
    DEFAULT_MODEL,
)
from modules.stock_fetcher import fetch_company_financials
import re

from modules.report_exporter import generate_html_report

# ── ページ設定 ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="財務AIダッシュボード｜Life Science Financial AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── カスタムCSSスタイル ──────────────────────────────────────────────────
st.markdown("""
<style>
    /* 全体フォント・ヘッダー */
    .main-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a365d;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #4a5568;
        font-size: 0.95rem;
        margin-bottom: 1.2rem;
    }
    /* KPIカード */
    .kpi-container {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 20px;
    }
    .kpi-box {
        flex: 1 1 150px;
        background: #ffffff;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border-top: 4px solid #2c7bb6;
    }
    .kpi-box.sub { border-top-color: #f77f00; }
    .kpi-box.pos { border-top-color: #1a9641; }
    .kpi-label {
        font-size: 0.8rem;
        color: #718096;
        margin-bottom: 4px;
        font-weight: 600;
    }
    .kpi-val {
        font-size: 1.5rem;
        font-weight: 700;
        color: #2d3748;
    }
    .kpi-diff {
        font-size: 0.8rem;
        margin-top: 4px;
    }
    /* AIアナリストボックス */
    .ai-box {
        background-color: #f0f7fc;
        border-left: 4px solid #2c7bb6;
        padding: 14px 18px;
        border-radius: 6px;
        margin-bottom: 18px;
    }
    .ai-box-title {
        font-weight: 700;
        color: #1f4e78;
        font-size: 0.95rem;
        margin-bottom: 6px;
    }
    .ai-box-content {
        font-size: 0.92rem;
        line-height: 1.7;
        color: #2d3748;
        white-space: pre-wrap;
    }
    .ai-box-meta {
        font-size: 0.75rem;
        color: #718096;
        margin-top: 8px;
    }
    /* バッジ */
    .badge-grade {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        color: white;
        font-weight: bold;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ── セッションステートの初期化 ──────────────────────────────────────────
if "df_pl" not in st.session_state:
    pl_init, bs_init, sum_init = load_example_data()
    st.session_state.df_pl = pl_init
    st.session_state.df_bs = bs_init
    st.session_state.df_summary = sum_init
    st.session_state.company_name = "株式会社サンプルテック (9999)"
    st.session_state.ai_comments = {}
    st.session_state.data_version = 0

# ── サイドバー ────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 財務AI設定")

    # 1. 会社名・銘柄コードの選択と取得
    st.subheader("🏢 銘柄・企業データの取得")

    PRESET_STOCKS = [
        "-- 代表銘柄から選択 --",
        "トヨタ自動車 (7203)",
        "武田薬品工業 (4502)",
        "中外製薬 (4519)",
        "第一三共 (4568)",
        "エーザイ (4523)",
        "アステラス製薬 (4503)",
        "ソニーグループ (6758)",
        "任天堂 (7974)",
        "キーエンス (6861)",
        "ソフトバンクグループ (9984)"
    ]

    preset_choice = st.selectbox(
        "代表銘柄から選ぶ",
        PRESET_STOCKS,
        index=0,
        key="preset_stock_selector",
        help="東証上場の代表的な製薬・バイオ・大手企業の財務諸表を1クリックでロードします。"
    )

    stock_query_input = st.text_input(
        "または銘柄コード・企業名を入力",
        value="",
        placeholder="例: 7203, 武田薬品, 4519, 6758",
        key="stock_query_text",
        help="4桁の証券コード（例: 7203, 4502）や日本語の企業名を入力して「🔍 データを取得」をクリックしてください。"
    )

    col_fetch, col_sample = st.columns([1.5, 1])
    with col_fetch:
        fetch_clicked = st.button("🔍 データを取得", type="primary", use_container_width=True)
    with col_sample:
        reset_clicked = st.button("🔄 サンプル復元", use_container_width=True)

    if fetch_clicked:
        target = None
        if stock_query_input and stock_query_input.strip():
            target = stock_query_input.strip()
        elif preset_choice != "-- 代表銘柄から選択 --":
            m_code = re.search(r"\((\d{4})\)", preset_choice)
            target = m_code.group(1) if m_code else preset_choice

        if target:
            with st.spinner(f"『{target}』の財務諸表データを取得中..."):
                try:
                    pl_f, bs_f, sum_f, disp_name = fetch_company_financials(target)
                    st.session_state.df_pl = pl_f
                    st.session_state.df_bs = bs_f
                    st.session_state.df_summary = sum_f
                    st.session_state.company_name = disp_name
                    st.session_state.ai_comments = {}
                    st.session_state.data_version = st.session_state.get("data_version", 0) + 1
                    st.session_state.flash_success = f"🎉 {disp_name} の財務データを取得しました！"
                    st.rerun()
                except Exception as e:
                    st.session_state.flash_error = f"⚠️ 取得エラー: {str(e)}"
                    st.rerun()
        else:
            st.warning("企業名・銘柄コードを入力するか、代表銘柄を選択してください。")

    if reset_clicked:
        pl_init, bs_init, sum_init = load_example_data()
        st.session_state.df_pl = pl_init
        st.session_state.df_bs = bs_init
        st.session_state.df_summary = sum_init
        st.session_state.company_name = "株式会社サンプルテック (9999)"
        st.session_state.ai_comments = {}
        st.session_state.data_version = st.session_state.get("data_version", 0) + 1
        st.session_state.flash_success = "サンプルデータを復元しました。"
        st.rerun()

    # フラッシュメッセージ表示
    if st.session_state.get("flash_success"):
        st.success(st.session_state.flash_success)
        st.session_state.flash_success = None
    if st.session_state.get("flash_error"):
        st.error(st.session_state.flash_error)
        st.session_state.flash_error = None

    # 2. 自社CSVファイルアップロード（任意）
    st.markdown("---")
    with st.expander("📂 自社CSVファイルの直接アップロード"):
        st.caption("P/L, B/S, サマリーの独自CSVファイルを使用したい場合に指定します。")
        up_pl = st.file_uploader("損益計算書 (input_pl.csv)", type=["csv"], key="uploader_pl")
        up_bs = st.file_uploader("貸借対照表 (input_bs.csv)", type=["csv"], key="uploader_bs")
        up_sum = st.file_uploader("複数期サマリー (input_summary.csv)", type=["csv"], key="uploader_sum")

        if up_pl is not None:
            st.session_state.df_pl = read_csv_flexible(up_pl)
            st.session_state.data_version = st.session_state.get("data_version", 0) + 1
        if up_bs is not None:
            st.session_state.df_bs = read_csv_flexible(up_bs)
            st.session_state.data_version = st.session_state.get("data_version", 0) + 1
        if up_sum is not None:
            st.session_state.df_summary = read_csv_flexible(up_sum)
            st.session_state.data_version = st.session_state.get("data_version", 0) + 1



    # 3. AI（Hugging Face API）設定
    st.markdown("---")
    st.subheader("🤖 AI設定 (Hugging Face)")
    hf_token = st.text_input(
        "HF API トークン",
        value=os.environ.get("HF_API_TOKEN", ""),
        type="password",
        help="huggingface.co/settings/tokens で無料取得可能。未入力の場合はオフライン自動診断が機能します。"
    )
    
    model_choice = st.selectbox(
        "LLMモデル選択",
        RECOMMENDED_MODELS + ["その他（カスタム指定）"],
        index=0
    )
    if model_choice == "その他（カスタム指定）":
        model_id = st.text_input("モデルIDを入力", value=DEFAULT_MODEL)
    else:
        model_id = model_choice

    col_btn, col_rst = st.columns([2, 1])
    with col_btn:
        generate_ai_btn = st.button("✨ AIコメント生成", type="primary", use_container_width=True)
    with col_rst:
        if st.button("クリア", use_container_width=True):
            st.session_state.ai_comments = {}
            st.rerun()

    # 4. テンプレートダウンロード
    st.markdown("---")
    st.subheader("📥 テンプレートダウンロード")
    st.caption("自社データ作成用のUTF-8-BOM形式CSVテンプレートです。")
    tpls = load_template_bytes()
    for fname, data_bytes in tpls.items():
        if data_bytes:
            st.download_button(
                label=f"📄 {fname}",
                data=data_bytes,
                file_name=fname,
                mime="text/csv",
                use_container_width=True
            )

# ── データ検証・財務指標計算 ─────────────────────────────────────────────
company_name = st.session_state.company_name
df_pl = st.session_state.df_pl
df_bs = st.session_state.df_bs
df_summary = st.session_state.df_summary


# 前期・当期の取得
pl_prev, pl_curr = get_periods_from_pl(df_pl)
bs_prev, bs_curr = get_periods_from_bs(df_bs)
period_prev = pl_prev or (bs_prev or "前期")
period_curr = pl_curr or (bs_curr or "当期")

# 指標計算
m = calculate_metrics(df_pl, df_bs, df_summary, period_prev, period_curr)
health_eval = evaluate_financial_health(m)

# AIコメント生成リクエスト時の処理
if generate_ai_btn:
    with st.spinner("AIアナリストが財務データを精査・コメント生成中..."):
        st.session_state.ai_comments = generate_all_comments(
            m=m,
            token=hf_token,
            model_id=model_id
        )
    st.success("AIコメントの生成が完了しました！")

ai_comments = st.session_state.ai_comments

# ── メインヘッダー ────────────────────────────────────────────────────────
st.markdown(f'<div class="main-title">📈 財務分析ダッシュボード｜{company_name}</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-title">'
    f'比較期間: <b>{period_prev}</b> → <b>{period_curr}</b> ｜ '
    f'財務健全性スコア: <span class="badge-grade" style="background-color:{health_eval["color"]}">{health_eval["grade"]} ({health_eval["total_score"]}点/100点)</span>'
    f'</div>',
    unsafe_allow_html=True
)

# ── エグゼクティブ KPI カード ────────────────────────────────────────────
kpi_cols = st.columns(6)
with kpi_cols[0]:
    st.metric(
        label="当期売上高",
        value=format_currency_oku(m.rev_curr),
        delta=f"{m.rev_growth_rate:+.1f}% (YoY)"
    )
with kpi_cols[1]:
    st.metric(
        label="売上総利益率",
        value=format_percent(m.gp_margin_curr),
        delta=f"{(m.gp_margin_curr - m.gp_margin_prev):+.1f} pt"
    )
with kpi_cols[2]:
    st.metric(
        label="営業利益率",
        value=format_percent(m.op_margin_curr),
        delta=f"{(m.op_margin_curr - m.op_margin_prev):+.1f} pt"
    )
with kpi_cols[3]:
    st.metric(
        label="当期純利益率",
        value=format_percent(m.ni_margin_curr),
        delta=f"{(m.ni_margin_curr - m.ni_margin_prev):+.1f} pt"
    )
with kpi_cols[4]:
    st.metric(
        label="自己資本比率",
        value=format_percent(m.equity_ratio_curr),
        delta=f"{(m.equity_ratio_curr - m.equity_ratio_prev):+.1f} pt"
    )
with kpi_cols[5]:
    st.metric(
        label="ROE",
        value=format_percent(m.roe_curr),
        delta=f"{(m.roe_curr - m.roe_prev):+.1f} pt"
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── タブナビゲーション ────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 業績サマリー",
    "📈 損益計算書 (P/L)",
    "🏛️ 貸借対照表 (B/S)",
    "🔬 デュポン分析 & 健全性診断",
    "🔮 経営What-Ifシミュレーター",
    "📁 データ管理 & レポート出力"
])

# ── ヘルパー: AIコメントカード描画 ───────────────────────────────────────
def render_ai_comment_box(key: str, default_title: str):
    info = ai_comments.get(key)
    if info:
        st.markdown(f"""
        <div class="ai-box">
            <div class="ai-box-title">🤖 {default_title}</div>
            <div class="ai-box-content">{info['text']}</div>
            <div class="ai-box-meta">情報源: {info['source']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("💡 サイドバーの「✨ AIコメント生成」ボタンを押すと、最新AIによる分析コメントが表示されます。（トークン未設定時はオフライン自動診断が機能します）")

# ─────────────────────────────────────────────────────────────────────────
# TAB 1: 業績サマリー
# ─────────────────────────────────────────────────────────────────────────
with tab1:
    render_ai_comment_box("summary", "AI アナリスト総合コメント（業績サマリー）")
    
    col_t1, col_t2 = st.columns([1.6, 1])
    with col_t1:
        st.plotly_chart(plot_summary_trends(df_summary), use_container_width=True)
    with col_t2:
        st.plotly_chart(plot_roe_equity_trend(df_summary), use_container_width=True)
        
    st.plotly_chart(plot_eps_trend(df_summary), use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────
# TAB 2: 損益計算書 (P/L)
# ─────────────────────────────────────────────────────────────────────────
with tab2:
    render_ai_comment_box("pl", "AI 損益アナリストコメント")

    col_pl1, col_pl2 = st.columns([1.5, 1])
    with col_pl1:
        st.plotly_chart(plot_waterfall_pl(df_pl, period_curr), use_container_width=True)
    with col_pl2:
        st.plotly_chart(plot_margin_comparison(df_pl, period_prev, period_curr), use_container_width=True)

    col_pl3, col_pl4 = st.columns([1, 1.6])
    with col_pl3:
        st.plotly_chart(plot_cost_structure(df_pl, period_curr), use_container_width=True)
    with col_pl4:
        st.subheader("📋 損益計算書 詳細データ")
        # 表示用テーブル作成
        df_pl_disp = df_pl.copy()
        if period_prev in df_pl_disp.columns and period_curr in df_pl_disp.columns:
            df_pl_disp["増減額 (千円)"] = df_pl_disp[period_curr] - df_pl_disp[period_prev]
            df_pl_disp["増減率 (%)"] = df_pl_disp.apply(
                lambda r: (f"{((r[period_curr] - r[period_prev]) / abs(r[period_prev]) * 100):+.1f}%"
                           if r[period_prev] != 0 else "N/A"), axis=1
            )
            # 数値フォーマット
            for c in [period_prev, period_curr, "増減額 (千円)"]:
                df_pl_disp[c] = df_pl_disp[c].apply(lambda x: f"{int(round(x)):,}" if pd.notnull(x) else "")
        st.dataframe(df_pl_disp, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────
# TAB 3: 貸借対照表 (B/S)
# ─────────────────────────────────────────────────────────────────────────
with tab3:
    render_ai_comment_box("bs", "AI 貸借対照表コメント")

    col_bs1, col_bs2 = st.columns(2)
    with col_bs1:
        st.plotly_chart(plot_asset_stacked(df_bs, period_prev, period_curr), use_container_width=True)
    with col_bs2:
        st.plotly_chart(plot_liab_stacked(df_bs, period_prev, period_curr), use_container_width=True)

    col_bs3, col_bs4 = st.columns([1, 1])
    with col_bs3:
        st.plotly_chart(plot_financial_health_ratios(m), use_container_width=True)
    with col_bs4:
        st.plotly_chart(plot_total_assets_trend(df_summary), use_container_width=True)

    st.subheader("📋 貸借対照表 詳細データ")
    df_bs_disp = df_bs.copy()
    if period_prev in df_bs_disp.columns and period_curr in df_bs_disp.columns:
        df_bs_disp["増減額 (千円)"] = df_bs_disp[period_curr] - df_bs_disp[period_prev]
        for c in [period_prev, period_curr, "増減額 (千円)"]:
            df_bs_disp[c] = df_bs_disp[c].apply(lambda x: f"{int(round(x)):,}" if pd.notnull(x) else "")
    st.dataframe(df_bs_disp, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────
# TAB 4: デュポン分析 & 健全性診断
# ─────────────────────────────────────────────────────────────────────────
with tab4:
    st.subheader("🔬 デュポンシステムによるROE分解分析")
    st.markdown("""
    **ROE（自己資本利益率）** を3要素に分解して、収益力・資産の運用効率・レバレッジ効果のどこに強み・弱みがあるかを診断します：
    $$\\text{ROE} = \\underbrace{\\frac{\\text{当期純利益}}{\\text{売上高}}}_{\\text{純利益率 (収益性)}} \\times \\underbrace{\\frac{\\text{売上高}}{\\text{総資産}}}_{\\text{総資産回転率 (効率性)}} \\times \\underbrace{\\frac{\\text{総資産}}{\\text{自己資本}}}_{\\text{財務レバレッジ (資本構成)}}$$
    """)

    dp_cols = st.columns(3)
    with dp_cols[0]:
        st.metric(
            label="当期純利益率 (収益性)",
            value=f"{m.dupont_margin_curr:.2f}%",
            delta=f"{(m.dupont_margin_curr - m.dupont_margin_prev):+.2f} pt"
        )
    with dp_cols[1]:
        st.metric(
            label="総資産回転率 (効率性)",
            value=f"{m.dupont_turnover_curr:.2f} 回",
            delta=f"{(m.dupont_turnover_curr - m.dupont_turnover_prev):+.2f} 回"
        )
    with dp_cols[2]:
        st.metric(
            label="財務レバレッジ (資本構成)",
            value=f"{m.dupont_leverage_curr:.2f} 倍",
            delta=f"{(m.dupont_leverage_curr - m.dupont_leverage_prev):+.2f} 倍"
        )

    col_dp1, col_dp2 = st.columns([1.4, 1])
    with col_dp1:
        st.plotly_chart(plot_dupont_factors(m), use_container_width=True)
    with col_dp2:
        st.plotly_chart(plot_health_radar(health_eval["scores"]), use_container_width=True)

    st.markdown("---")
    st.subheader("⚖️ 損益分岐点 (BEP) & 安全余裕率分析")
    col_bep1, col_bep2 = st.columns([1.2, 1])
    with col_bep1:
        st.plotly_chart(plot_bep_analysis(m), use_container_width=True)
    with col_bep2:
        st.markdown(f"""
        <div style="background:#f8f9fa; border:1px solid #e2e8f0; border-radius:8px; padding:18px;">
            <div style="font-weight:bold; font-size:16px; margin-bottom:12px; color:#2b6cb0;">📊 BEP 分析指標</div>
            <p><b>当期売上高:</b> {m.rev_curr:,.0f} 千円</p>
            <p><b>推定損益分岐点売上高:</b> {m.bep_sales:,.0f} 千円</p>
            <p><b>限界利益率:</b> {m.marginal_profit_ratio*100:.1f}%</p>
            <p><b>損益分岐点比率:</b> {m.bep_ratio:.1f}%</p>
            <p><b>経営安全余裕率:</b> <span style="font-size:18px; font-weight:bold; color:#1a9641;">{m.safety_margin:.1f}%</span></p>
            <small style="color:#718096;">※ 売上高が安全余裕率（{m.safety_margin:.1f}%）以上低下しない限り赤字には転落しません。</small>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 ルールベース自動財務診断レポート")
    st.markdown(f"""
    <div style="background:#f0fff4; border-left:4px solid #38a169; padding:18px; border-radius:6px;">
        <div style="font-weight:bold; color:#22543d; font-size:16px; margin-bottom:10px;">
            総合評価: {health_eval['grade']} (合計スコア: {health_eval['total_score']}点 / 100点)
        </div>
        <div style="white-space:pre-wrap; line-height:1.8; color:#1a202c;">{health_eval['summary_text']}</div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────
# TAB 5: 経営What-Ifシミュレーター
# ─────────────────────────────────────────────────────────────────────────
with tab5:
    st.subheader("🔮 経営What-Ifシミュレーター（感応度分析）")
    st.caption("売上増やコスト削減施策を実行した場合の、翌期営業利益および利益率への影響をリアルタイムに試算できます。")

    col_sim_ctrl, col_sim_res = st.columns([1, 1.4])
    with col_sim_ctrl:
        st.markdown("##### 🎛️ パラメータ調整")
        sim_rev_pct = st.slider("売上高の変動率 (%)", min_value=-30.0, max_value=30.0, value=5.0, step=0.5)
        sim_cogs_pct = st.slider("売上原価率の改善幅 (pt)", min_value=-10.0, max_value=10.0, value=-1.0, step=0.2, help="マイナスで原価率改善（利益増）")
        sim_sga_pct = st.slider("販管費の増減率 (%)", min_value=-20.0, max_value=20.0, value=-2.0, step=0.5, help="マイナスで固定費削減")

    # 試算ロジック
    base_rev = m.rev_curr
    base_cogs_ratio = (m.cogs_curr / m.rev_curr) if m.rev_curr > 0 else 0.5
    base_sga = m.sga_curr

    sim_rev = base_rev * (1.0 + sim_rev_pct / 100.0)
    sim_cogs_ratio = max(0.0, base_cogs_ratio + sim_cogs_pct / 100.0)
    sim_cogs = sim_rev * sim_cogs_ratio
    sim_gp = sim_rev - sim_cogs
    sim_sga = base_sga * (1.0 + sim_sga_pct / 100.0)
    sim_op = sim_gp - sim_sga
    sim_op_margin = (sim_op / sim_rev * 100.0) if sim_rev > 0 else 0.0

    op_diff = sim_op - m.op_curr
    op_diff_pct = (op_diff / abs(m.op_curr) * 100.0) if m.op_curr != 0 else 0.0

    with col_sim_res:
        st.markdown("##### 🎯 試算結果")
        r_cols = st.columns(3)
        with r_cols[0]:
            st.metric("試算売上高", f"{sim_rev/100000:.1f}億円", f"{sim_rev_pct:+.1f}%")
        with r_cols[1]:
            st.metric("試算営業利益", f"{sim_op/100000:.2f}億円", f"{op_diff_pct:+.1f}%")
        with r_cols[2]:
            st.metric("試算営業利益率", f"{sim_op_margin:.1f}%", f"{sim_op_margin - m.op_margin_curr:+.1f} pt")

        # 試算比較棒グラフ
        import plotly.graph_objects as go
        fig_sim = go.Figure()
        fig_sim.add_trace(go.Bar(
            name="実績（当期）",
            x=["売上高", "売上総利益", "営業利益"],
            y=[m.rev_curr, m.gp_curr, m.op_curr],
            marker=dict(color="#999999"),
            text=[f"{m.rev_curr:,.0f}", f"{m.gp_curr:,.0f}", f"{m.op_curr:,.0f}"],
            textposition="auto"
        ))
        fig_sim.add_trace(go.Bar(
            name="シミュレーション試算",
            x=["売上高", "売上総利益", "営業利益"],
            y=[sim_rev, sim_gp, sim_op],
            marker=dict(color="#1a9641"),
            text=[f"{sim_rev:,.0f}", f"{sim_gp:,.0f}", f"{sim_op:,.0f}"],
            textposition="auto"
        ))
        fig_sim.update_layout(
            barmode="group",
            title="<b>実績 vs シミュレーション比較（千円）</b>",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#e5e5e5"),
            margin=dict(t=30, b=20, l=40, r=20),
            legend=dict(orientation="h", y=-0.2)
        )
        st.plotly_chart(fig_sim, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────
# TAB 6: データ管理・エディタ & レポート出力
# ─────────────────────────────────────────────────────────────────────────
with tab6:
    st.subheader("📁 データ直接編集 & スタンドアロンレポート出力")
    
    st.markdown("#### 1. 画面上でのデータ直接編集（Data Editor）")
    st.caption("セルをダブルクリックして値を直接変更できます。編集後は「💾 反映」ボタンを押すとダッシュボード全体に適用されます。")
    
    dv = st.session_state.get("data_version", 0)
    tab_e1, tab_e2, tab_e3 = st.tabs(["損益計算書 (P/L)", "貸借対照表 (B/S)", "複数期サマリー"])
    with tab_e1:
        edited_pl = st.data_editor(df_pl, num_rows="dynamic", use_container_width=True, key=f"editor_pl_{dv}")
        if st.button("💾 P/Lの変更をダッシュボードに反映", key=f"btn_save_pl_{dv}"):
            st.session_state.df_pl = edited_pl
            st.session_state.ai_comments = {}
            st.session_state.flash_success = "P/Lの編集内容をダッシュボードに反映しました！"
            st.rerun()
    with tab_e2:
        edited_bs = st.data_editor(df_bs, num_rows="dynamic", use_container_width=True, key=f"editor_bs_{dv}")
        if st.button("💾 B/Sの変更をダッシュボードに反映", key=f"btn_save_bs_{dv}"):
            st.session_state.df_bs = edited_bs
            st.session_state.ai_comments = {}
            st.session_state.flash_success = "B/Sの編集内容をダッシュボードに反映しました！"
            st.rerun()
    with tab_e3:
        edited_sum = st.data_editor(df_summary, num_rows="dynamic", use_container_width=True, key=f"editor_sum_{dv}")
        if st.button("💾 サマリーの変更をダッシュボードに反映", key=f"btn_save_sum_{dv}"):
            st.session_state.df_summary = edited_sum
            st.session_state.ai_comments = {}
            st.session_state.flash_success = "サマリーの編集内容をダッシュボードに反映しました！"
            st.rerun()


    st.markdown("---")
    st.markdown("#### 2. スタンドアロンHTMLレポートのエクスポート")
    st.caption("元の `bidash` / `aidash` と同様に、オフラインでもブラウザ単体で開いてプレゼンや社内配布ができる完全自立型のHTMLレポートを出力します。")

    html_content = generate_html_report(
        company_name=company_name,
        m=m,
        df_pl=st.session_state.df_pl,
        df_bs=st.session_state.df_bs,
        df_summary=st.session_state.df_summary,
        ai_comments=ai_comments,
        health_eval=health_eval
    )

    st.download_button(
        label="🌐 スタンドアロンHTMLレポートをダウンロード",
        data=html_content.encode("utf-8"),
        file_name=f"financial_report_{company_name}.html",
        mime="text/html",
        type="primary"
    )
