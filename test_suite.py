"""
財務AIダッシュボード 単体・統合検証スクリプト
"""

import sys
from pathlib import Path

# パス追加
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

from modules.data_loader import (
    load_example_data,
    load_template_bytes,
    get_periods_from_pl,
    get_periods_from_bs,
    validate_data,
    format_currency_oku,
)
from modules.metrics import (
    calculate_metrics,
    evaluate_financial_health,
)
from modules.charts import (
    plot_summary_trends,
    plot_waterfall_pl,
    plot_margin_comparison,
    plot_cost_structure,
    plot_asset_stacked,
    plot_liab_stacked,
    plot_financial_health_ratios,
    plot_dupont_factors,
    plot_bep_analysis,
    plot_health_radar,
)
from modules.ai_service import (
    build_summary_prompt,
    build_pl_prompt,
    build_bs_prompt,
    generate_all_comments,
)
from modules.report_exporter import generate_html_report


def test_all():
    print("[1/5] サンプルデータ読み込み・検証テスト...")
    df_pl, df_bs, df_summary = load_example_data()
    assert not df_pl.empty, "df_pl が空です"
    assert not df_bs.empty, "df_bs が空です"
    assert not df_summary.empty, "df_summary が空です"
    
    warnings = validate_data(df_pl, df_bs, df_summary)
    assert len(warnings) == 0, f"バリデーション警告: {warnings}"

    pl_prev, pl_curr = get_periods_from_pl(df_pl)
    bs_prev, bs_curr = get_periods_from_bs(df_bs)
    assert pl_prev == "2024年3月期", f"前期不正: {pl_prev}"
    assert pl_curr == "2025年3月期", f"当期不正: {pl_curr}"
    print("  -> OK (前期: 2024年3月期, 当期: 2025年3月期)")

    print("[2/5] 財務指標計算・デュポン・BEP・ルールベース診断テスト...")
    m = calculate_metrics(df_pl, df_bs, df_summary, pl_prev, pl_curr)
    assert m.rev_curr == 5340000, f"売上高不一致: {m.rev_curr}"
    assert m.op_curr == 450000, f"営業利益不一致: {m.op_curr}"
    assert m.equity_ratio_curr > 60.0, f"自己資本比率不一致: {m.equity_ratio_curr}"
    assert m.dupont_turnover_curr > 0, "総資産回転率が0以下です"
    assert m.bep_sales > 0, "損益分岐点売上高が0以下です"

    health = evaluate_financial_health(m)
    assert health["total_score"] > 0, "スコアが0以下です"
    print(f"  -> OK (売上高: {format_currency_oku(m.rev_curr)}, 総合スコア: {health['total_score']}点, 判定: {health['grade']})")

    print("[3/5] Plotly チャート生成テスト...")
    fig1 = plot_summary_trends(df_summary)
    fig2 = plot_waterfall_pl(df_pl, pl_curr)
    fig3 = plot_margin_comparison(df_pl, pl_prev, pl_curr)
    fig4 = plot_asset_stacked(df_bs, pl_prev, pl_curr)
    fig5 = plot_dupont_factors(m)
    fig6 = plot_health_radar(health["scores"])
    assert fig1 is not None and fig2 is not None and fig5 is not None
    print("  -> OK (全Plotlyフィギュアが正常に生成)")

    print("[4/5] AI プロンプト構築 & オフライン診断コメントテスト...")
    p_sum = build_summary_prompt(m)
    p_pl = build_pl_prompt(m)
    p_bs = build_bs_prompt(m)
    assert "証券アナリスト" in p_sum
    assert "損益計算書データ" in p_pl
    assert "貸借対照表データ" in p_bs

    comments = generate_all_comments(m, token="")
    assert "summary" in comments and "pl" in comments and "bs" in comments
    print(f"  -> OK (オフライン診断コメント正常生成: {len(comments['summary']['text'])}文字)")

    print("[5/6] スタンドアロンHTMLレポート出力テスト...")
    html = generate_html_report(
        company_name="株式会社サンプルテック (9999)",
        m=m,
        df_pl=df_pl,
        df_bs=df_bs,
        df_summary=df_summary,
        ai_comments=comments,
        health_eval=health
    )
    assert "<html" in html and "</html>" in html
    assert "株式会社サンプルテック" in html
    print(f"  -> OK (HTMLレポート正常生成: {len(html):,} バイト)")

    print("[6/6] 銘柄コード・企業名からの自動財務データ取得テスト...")
    from modules.stock_fetcher import resolve_ticker, fetch_company_financials
    sym_7203, _ = resolve_ticker("7203")
    assert sym_7203 == "7203.T", f"7203解決失敗: {sym_7203}"
    sym_toyota, _ = resolve_ticker("トヨタ")
    assert sym_toyota == "7203.T", f"トヨタ解決失敗: {sym_toyota}"

    f_pl, f_bs, f_sum, f_name = fetch_company_financials("4502")
    assert not f_pl.empty and not f_bs.empty and not f_sum.empty
    assert "4502" in f_name
    print(f"  -> OK (4502 自動取得成功: {f_name}, {len(f_pl)} 項目)")

    print("[7/7] ライフサイエンス2社業績比較機能＆チャートテスト...")
    from modules.stock_fetcher import LIFE_SCIENCE_PRESET_STOCKS, extract_company_kpis
    from modules.metrics import evaluate_two_companies_comparison
    from modules.charts import (
        plot_comparison_radar,
        plot_comparison_scale_bars,
        plot_comparison_margins,
        plot_comparison_dupont,
    )
    # プリセット検証（ライフサイエンス限定 & 6090完全除外）
    assert len(LIFE_SCIENCE_PRESET_STOCKS) >= 10
    assert any("4502" in s for s in LIFE_SCIENCE_PRESET_STOCKS)
    assert any("4568" in s for s in LIFE_SCIENCE_PRESET_STOCKS)
    assert not any("6090" in s for s in LIFE_SCIENCE_PRESET_STOCKS)
    assert not any("7203" in s for s in LIFE_SCIENCE_PRESET_STOCKS)

    # 2社KPI抽出
    kpi_a = extract_company_kpis(f_pl, f_bs, f_sum, f_name)
    assert kpi_a["metrics"].rev_curr > 0

    # 比較評価
    comp_eval = evaluate_two_companies_comparison(kpi_a, kpi_a)
    assert "ライフサイエンス・アナリスト比較総括" in comp_eval["commentary"]

    # チャート生成
    fig_radar = plot_comparison_radar(kpi_a, kpi_a)
    fig_scale = plot_comparison_scale_bars(kpi_a, kpi_a)
    fig_marg = plot_comparison_margins(kpi_a, kpi_a)
    fig_dup = plot_comparison_dupont(kpi_a, kpi_a)
    assert fig_radar is not None and fig_scale is not None and fig_marg is not None and fig_dup is not None
    print("  -> OK (2社比較評価・レーダーチャート・並行棒グラフすべて正常生成)")

    print("\n==========================================")
    print("  すべてのテストが正常に通過しました！ (ALL PASSED)")
    print("==========================================")



if __name__ == "__main__":
    test_all()
