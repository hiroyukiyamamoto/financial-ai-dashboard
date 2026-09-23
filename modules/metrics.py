"""
財務指標計算・デュポン分析・損益分岐点（BEP）分析・自動財務診断エンジン
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import pandas as pd
from .data_loader import get_pl_val, get_bs_val


@dataclass
class FinancialMetrics:
    # 期間情報
    period_prev: str
    period_curr: str
    
    # 損益計算書 (PL)
    rev_curr: float = 0.0
    rev_prev: float = 0.0
    rev_diff: float = 0.0
    rev_growth_rate: float = 0.0
    
    gp_curr: float = 0.0
    gp_prev: float = 0.0
    gp_margin_curr: float = 0.0
    gp_margin_prev: float = 0.0
    
    cogs_curr: float = 0.0
    sga_curr: float = 0.0
    
    op_curr: float = 0.0
    op_prev: float = 0.0
    op_margin_curr: float = 0.0
    op_margin_prev: float = 0.0
    op_growth_rate: float = 0.0
    
    ord_curr: float = 0.0
    ord_prev: float = 0.0
    ord_margin_curr: float = 0.0
    ord_margin_prev: float = 0.0
    
    ni_curr: float = 0.0
    ni_prev: float = 0.0
    ni_margin_curr: float = 0.0
    ni_margin_prev: float = 0.0
    
    # 貸借対照表 (BS)
    asset_curr: float = 0.0
    asset_prev: float = 0.0
    ca_curr: float = 0.0
    ca_prev: float = 0.0
    fa_curr: float = 0.0
    fa_prev: float = 0.0
    
    liab_curr: float = 0.0
    liab_prev: float = 0.0
    cl_curr: float = 0.0
    cl_prev: float = 0.0
    fl_curr: float = 0.0
    fl_prev: float = 0.0
    
    eq_curr: float = 0.0
    eq_prev: float = 0.0
    
    # 健全性・効率性指標
    equity_ratio_curr: float = 0.0
    equity_ratio_prev: float = 0.0
    cur_ratio_curr: float = 0.0
    cur_ratio_prev: float = 0.0
    debt_ratio_curr: float = 0.0
    debt_ratio_prev: float = 0.0
    roa_curr: float = 0.0
    roa_prev: float = 0.0
    roe_curr: float = 0.0
    roe_prev: float = 0.0
    
    # デュポン分析 (3分解)
    dupont_margin_curr: float = 0.0   # 純利益率 (%)
    dupont_margin_prev: float = 0.0
    dupont_turnover_curr: float = 0.0 # 総資産回転率 (回)
    dupont_turnover_prev: float = 0.0
    dupont_leverage_curr: float = 0.0 # 財務レバレッジ (倍)
    dupont_leverage_prev: float = 0.0
    
    # 損益分岐点分析 (BEP)
    bep_sales: float = 0.0
    bep_ratio: float = 0.0
    safety_margin: float = 0.0
    marginal_profit_ratio: float = 0.0


def calculate_metrics(
    df_pl: pd.DataFrame,
    df_bs: pd.DataFrame,
    df_summary: Optional[pd.DataFrame],
    period_prev: str,
    period_curr: str
) -> FinancialMetrics:
    """PL, BS, Summary からすべての財務指標を一括計算"""
    m = FinancialMetrics(period_prev=period_prev, period_curr=period_curr)
    
    # 損益計算書項目
    m.rev_curr = get_pl_val(df_pl, "売上高", period_curr)
    m.rev_prev = get_pl_val(df_pl, "売上高", period_prev)
    m.rev_diff = m.rev_curr - m.rev_prev
    m.rev_growth_rate = ((m.rev_diff / abs(m.rev_prev)) * 100.0) if m.rev_prev != 0 else 0.0
    
    m.cogs_curr = get_pl_val(df_pl, "売上原価", period_curr)
    m.sga_curr = get_pl_val(df_pl, "販売費及び一般管理費", period_curr)
    
    m.gp_curr = get_pl_val(df_pl, "売上総利益", period_curr)
    m.gp_prev = get_pl_val(df_pl, "売上総利益", period_prev)
    m.gp_margin_curr = (m.gp_curr / m.rev_curr * 100.0) if m.rev_curr != 0 else 0.0
    m.gp_margin_prev = (m.gp_prev / m.rev_prev * 100.0) if m.rev_prev != 0 else 0.0
    
    m.op_curr = get_pl_val(df_pl, "営業利益", period_curr)
    m.op_prev = get_pl_val(df_pl, "営業利益", period_prev)
    m.op_margin_curr = (m.op_curr / m.rev_curr * 100.0) if m.rev_curr != 0 else 0.0
    m.op_margin_prev = (m.op_prev / m.rev_prev * 100.0) if m.rev_prev != 0 else 0.0
    m.op_growth_rate = (((m.op_curr - m.op_prev) / abs(m.op_prev)) * 100.0) if m.op_prev != 0 else 0.0
    
    m.ord_curr = get_pl_val(df_pl, "経常利益", period_curr)
    m.ord_prev = get_pl_val(df_pl, "経常利益", period_prev)
    m.ord_margin_curr = (m.ord_curr / m.rev_curr * 100.0) if m.rev_curr != 0 else 0.0
    m.ord_margin_prev = (m.ord_prev / m.rev_prev * 100.0) if m.rev_prev != 0 else 0.0
    
    m.ni_curr = get_pl_val(df_pl, "当期純利益", period_curr)
    m.ni_prev = get_pl_val(df_pl, "当期純利益", period_prev)
    m.ni_margin_curr = (m.ni_curr / m.rev_curr * 100.0) if m.rev_curr != 0 else 0.0
    m.ni_margin_prev = (m.ni_prev / m.rev_prev * 100.0) if m.rev_prev != 0 else 0.0
    
    # 貸借対照表項目
    m.asset_curr = get_bs_val(df_bs, "資産合計", period_curr)
    m.asset_prev = get_bs_val(df_bs, "資産合計", period_prev)
    
    m.ca_curr = get_bs_val(df_bs, "流動資産合計", period_curr)
    m.ca_prev = get_bs_val(df_bs, "流動資産合計", period_prev)
    m.fa_curr = get_bs_val(df_bs, "固定資産合計", period_curr)
    m.fa_prev = get_bs_val(df_bs, "固定資産合計", period_prev)
    
    m.liab_curr = get_bs_val(df_bs, "負債合計", period_curr)
    m.liab_prev = get_bs_val(df_bs, "負債合計", period_prev)
    m.cl_curr = get_bs_val(df_bs, "流動負債合計", period_curr)
    m.cl_prev = get_bs_val(df_bs, "流動負債合計", period_prev)
    m.fl_curr = get_bs_val(df_bs, "固定負債合計", period_curr)
    m.fl_prev = get_bs_val(df_bs, "固定負債合計", period_prev)
    
    m.eq_curr = get_bs_val(df_bs, "純資産合計", period_curr)
    m.eq_prev = get_bs_val(df_bs, "純資産合計", period_prev)
    
    # 健全性比率
    m.equity_ratio_curr = (m.eq_curr / m.asset_curr * 100.0) if m.asset_curr != 0 else 0.0
    m.equity_ratio_prev = (m.eq_prev / m.asset_prev * 100.0) if m.asset_prev != 0 else 0.0
    
    m.cur_ratio_curr = (m.ca_curr / m.cl_curr * 100.0) if m.cl_curr != 0 else 0.0
    m.cur_ratio_prev = (m.ca_prev / m.cl_prev * 100.0) if m.cl_prev != 0 else 0.0
    
    m.debt_ratio_curr = (m.liab_curr / m.eq_curr * 100.0) if m.eq_curr != 0 else 0.0
    m.debt_ratio_prev = (m.liab_prev / m.eq_prev * 100.0) if m.eq_prev != 0 else 0.0
    
    m.roa_curr = (m.ni_curr / m.asset_curr * 100.0) if m.asset_curr != 0 else 0.0
    m.roa_prev = (m.ni_prev / m.asset_prev * 100.0) if m.asset_prev != 0 else 0.0
    
    # ROE (Summaryにあれば直近、なければ ni / eq)
    if df_summary is not None and "ROE" in df_summary.columns and len(df_summary) >= 2:
        m.roe_curr = float(df_summary["ROE"].iloc[-1])
        m.roe_prev = float(df_summary["ROE"].iloc[-2])
    else:
        m.roe_curr = (m.ni_curr / m.eq_curr * 100.0) if m.eq_curr != 0 else 0.0
        m.roe_prev = (m.ni_prev / m.eq_prev * 100.0) if m.eq_prev != 0 else 0.0
        
    # デュポン分析 (ROE = 純利益率 × 総資産回転率 × 財務レバレッジ)
    # 当期
    m.dupont_margin_curr = m.ni_margin_curr
    m.dupont_turnover_curr = (m.rev_curr / m.asset_curr) if m.asset_curr != 0 else 0.0
    m.dupont_leverage_curr = (m.asset_curr / m.eq_curr) if m.eq_curr != 0 else 0.0
    
    # 前期
    m.dupont_margin_prev = m.ni_margin_prev
    m.dupont_turnover_prev = (m.rev_prev / m.asset_prev) if m.asset_prev != 0 else 0.0
    m.dupont_leverage_prev = (m.asset_prev / m.eq_prev) if m.eq_prev != 0 else 0.0
    
    # 損益分岐点 (BEP) 分析
    # 変動費 ≒ 売上原価、固定費 ≒ 販管費 と近似
    marginal_profit = m.rev_curr - m.cogs_curr
    if m.rev_curr > 0:
        m.marginal_profit_ratio = marginal_profit / m.rev_curr
        if m.marginal_profit_ratio > 0:
            m.bep_sales = m.sga_curr / m.marginal_profit_ratio
            m.bep_ratio = (m.bep_sales / m.rev_curr) * 100.0
            m.safety_margin = 100.0 - m.bep_ratio
            
    return m


def evaluate_financial_health(m: FinancialMetrics) -> Dict[str, Any]:
    """
    ルールベース財務健全性診断エンジン（オフライン・API不要）
    収益性・安全性・成長性・効率性の4軸でスコアリング（各25点満点、合計100点満点）
    S (85+), A (70+), B (55+), C (40+), D (<40)
    """
    # 1. 収益性 (Profitability)
    p_score = 0.0
    if m.op_margin_curr >= 10.0:
        p_score += 10.0
    elif m.op_margin_curr >= 5.0:
        p_score += 7.0
    elif m.op_margin_curr > 0:
        p_score += 4.0
    else:
        p_score += 0.0
        
    if m.roe_curr >= 15.0:
        p_score += 10.0
    elif m.roe_curr >= 8.0:
        p_score += 7.0
    elif m.roe_curr > 0:
        p_score += 4.0
    else:
        p_score += 0.0
        
    if m.roa_curr >= 8.0:
        p_score += 5.0
    elif m.roa_curr >= 4.0:
        p_score += 3.5
    elif m.roa_curr > 0:
        p_score += 2.0
    else:
        p_score += 0.0
        
    # 2. 安全性 (Safety)
    s_score = 0.0
    if m.equity_ratio_curr >= 60.0:
        s_score += 12.0
    elif m.equity_ratio_curr >= 40.0:
        s_score += 9.0
    elif m.equity_ratio_curr >= 20.0:
        s_score += 5.0
    else:
        s_score += 1.0
        
    if m.cur_ratio_curr >= 200.0:
        s_score += 8.0
    elif m.cur_ratio_curr >= 130.0:
        s_score += 6.0
    elif m.cur_ratio_curr >= 100.0:
        s_score += 4.0
    else:
        s_score += 1.0
        
    if m.debt_ratio_curr <= 80.0:
        s_score += 5.0
    elif m.debt_ratio_curr <= 150.0:
        s_score += 3.5
    else:
        s_score += 1.0
        
    # 3. 成長性 (Growth)
    g_score = 0.0
    if m.rev_growth_rate >= 10.0:
        g_score += 13.0
    elif m.rev_growth_rate >= 3.0:
        g_score += 9.0
    elif m.rev_growth_rate >= 0:
        g_score += 5.0
    else:
        g_score += 1.0
        
    if m.op_growth_rate >= 10.0:
        g_score += 12.0
    elif m.op_growth_rate >= 0:
        g_score += 8.0
    else:
        g_score += 2.0
        
    # 4. 効率性 & 堅実性 (Efficiency)
    e_score = 0.0
    if m.dupont_turnover_curr >= 1.5:
        e_score += 10.0
    elif m.dupont_turnover_curr >= 1.0:
        e_score += 8.0
    elif m.dupont_turnover_curr >= 0.7:
        e_score += 5.0
    else:
        e_score += 2.0
        
    if m.safety_margin >= 25.0:
        e_score += 15.0
    elif m.safety_margin >= 10.0:
        e_score += 10.0
    elif m.safety_margin >= 0:
        e_score += 6.0
    else:
        e_score += 1.0
        
    total_score = p_score + s_score + g_score + e_score
    
    if total_score >= 85:
        grade = "S (極めて優良)"
        color = "#1a9641"
    elif total_score >= 70:
        grade = "A (優良)"
        color = "#2c7bb6"
    elif total_score >= 55:
        grade = "B (健全)"
        color = "#f77f00"
    elif total_score >= 40:
        grade = "C (要改善)"
        color = "#e66101"
    else:
        grade = "D (警戒水準)"
        color = "#d73027"
        
    # 自動生成診断レポートテキスト
    strengths = []
    cautions = []
    
    if m.equity_ratio_curr >= 50.0:
        strengths.append(f"自己資本比率が{m.equity_ratio_curr:.1f}%と強固で、中長期の財務安全性が非常に高い水準です。")
    elif m.equity_ratio_curr < 30.0:
        cautions.append(f"自己資本比率が{m.equity_ratio_curr:.1f}%とやや低く、レバレッジ依存度への注視が必要です。")
        
    if m.op_margin_curr >= 8.0:
        strengths.append(f"営業利益率が{m.op_margin_curr:.1f}%を記録しており、本業における価格競争力・付加価値創出が優れています。")
    elif m.op_margin_curr < 3.0:
        cautions.append(f"営業利益率が{m.op_margin_curr:.1f}%と薄利傾向にあるため、原価改善または高付加価値化が課題です。")
        
    if m.rev_growth_rate > 0 and m.op_growth_rate > 0:
        strengths.append(f"売上高（前年比+{m.rev_growth_rate:.1f}%）、営業利益（前年比+{m.op_growth_rate:.1f}%）の『増収増益』を達成しています。")
    elif m.rev_growth_rate > 0 and m.op_growth_rate <= 0:
        cautions.append("増収であるものの営業減益となっており、売上拡大に伴う費用の増加（販管費・原価率悪化）の精査が推奨されます。")
    elif m.rev_growth_rate <= 0:
        cautions.append(f"売上高が前年比{m.rev_growth_rate:.1f}%と減収傾向にあり、市場シェア維持や新規需要の開拓が急務です。")
        
    if m.cur_ratio_curr >= 150.0:
        strengths.append(f"流動比率は{m.cur_ratio_curr:.1f}%を確保しており、短期的な資金繰り・支払能力に懸念はありません。")
    elif m.cur_ratio_curr < 100.0:
        cautions.append(f"流動比率が100%を下回っており（{m.cur_ratio_curr:.1f}%）、運転資金の確保に注意が必要です。")
        
    if m.safety_margin >= 15.0:
        strengths.append(f"損益分岐点に対する安全余裕率は{m.safety_margin:.1f}%あり、売上減少に対する耐性があります。")
        
    summary_text = (
        f"【総合評価スコア: {total_score:.1f}点 / 100点】— 判定: {grade}\n\n"
        f"■ 強み・評価点:\n" + ("\n".join([f"・{s}" for s in strengths]) if strengths else "・特筆すべき突出した強みは観察されず、全体的に標準水準です。") + "\n\n"
        f"■ 課題・留意点:\n" + ("\n".join([f"・{c}" for c in cautions]) if cautions else "・特段の財務的リスクは見当たらず、極めて健全な財務基盤です。")
    )
    
    return {
        "total_score": round(total_score, 1),
        "grade": grade,
        "color": color,
        "scores": {
            "収益性": round(p_score, 1),
            "安全性": round(s_score, 1),
            "成長性": round(g_score, 1),
            "効率性": round(e_score, 1),
        },
        "strengths": strengths,
        "cautions": cautions,
        "summary_text": summary_text
    }


def evaluate_two_companies_comparison(kpi_a: dict, kpi_b: dict) -> dict:
    """
    ライフサイエンス業界の視点を踏まえた2社業績・財務比較診断エンジン。
    """
    name_a = kpi_a["name"]
    name_b = kpi_b["name"]
    ma: FinancialMetrics = kpi_a["metrics"]
    mb: FinancialMetrics = kpi_b["metrics"]

    # 1. 規模判定
    scale_leader = name_a if ma.rev_curr >= mb.rev_curr else name_b
    rev_ratio = (ma.rev_curr / mb.rev_curr) if mb.rev_curr > 0 else 1.0

    # 2. 収益性判定
    prof_leader = name_a if ma.op_margin_curr >= mb.op_margin_curr else name_b
    op_diff = abs(ma.op_margin_curr - mb.op_margin_curr)

    # 3. 健全性判定
    safety_leader = name_a if ma.equity_ratio_curr >= mb.equity_ratio_curr else name_b

    # 4. 資本効率判定
    roe_leader = name_a if ma.roe_curr >= mb.roe_curr else name_b

    highlights = []
    
    # 規模
    if rev_ratio >= 1.5:
        highlights.append(f"【事業規模】{name_a} が売上高で {name_b} を約 {rev_ratio:.1f}倍 上回り、メガファーマ・大手としてのグローバル事業規模・販売網で優位に立っています。")
    elif rev_ratio <= 0.67:
        highlights.append(f"【事業規模】{name_b} が売上高で {name_a} を約 {(1.0/rev_ratio):.1f}倍 上回り、スケールメリットと市場カバレッジでリードしています。")
    else:
        highlights.append(f"【事業規模】両社の売上規模は比較的拮抗しており（規模比 {rev_ratio:.2f}倍）、業界内での直接的なライバル関係にあります。")

    # 収益力 (ライフサイエンス特有の粗利率・営業利益率)
    if op_diff >= 5.0:
        leader = name_a if ma.op_margin_curr > mb.op_margin_curr else name_b
        trailer = name_b if leader == name_a else name_a
        m_high = max(ma.op_margin_curr, mb.op_margin_curr)
        m_low = min(ma.op_margin_curr, mb.op_margin_curr)
        highlights.append(f"【本業の稼ぐ力】{leader}（営業利益率 {m_high:.1f}%）が {trailer}（同 {m_low:.1f}%）を {op_diff:.1f}ポイント 凌駕しており、高付加価値新薬・特許製品の比率や価格決定力で強みを発揮しています。")
    else:
        highlights.append(f"【本業の稼ぐ力】営業利益率は {name_a}: {ma.op_margin_curr:.1f}% vs {name_b}: {mb.op_margin_curr:.1f}% と僅差（差 {op_diff:.1f}pt）で、両社ともに同等の利益創出力を持っています。")

    # 資本健全性 & 研究開発余力
    if abs(ma.equity_ratio_curr - mb.equity_ratio_curr) >= 15.0:
        s_lead = name_a if ma.equity_ratio_curr > mb.equity_ratio_curr else name_b
        s_trail = name_b if s_lead == name_a else name_a
        eq_high = max(ma.equity_ratio_curr, mb.equity_ratio_curr)
        eq_low = min(ma.equity_ratio_curr, mb.equity_ratio_curr)
        highlights.append(f"【財務健全性・R&D投資余力】自己資本比率は {s_lead}（{eq_high:.1f}%）が {s_trail}（{eq_low:.1f}%）を大きく上回り、臨床開発パイプラインの失敗リスクや大型買収・アライアンスに対する高い耐震力を誇ります。")
    else:
        highlights.append(f"【財務健全性】自己資本比率は {name_a}: {ma.equity_ratio_curr:.1f}% vs {name_b}: {mb.equity_ratio_curr:.1f}% となり、両社とも業界標準に見合った財務クッションを維持しています。")

    # デュポン分解の要因分析
    dupont_comment = ""
    if ma.roe_curr > mb.roe_curr:
        if ma.dupont_margin_curr > mb.dupont_margin_curr:
            factor = "高マージン（純利益率の高さ）"
        elif ma.dupont_turnover_curr > mb.dupont_turnover_curr:
            factor = "高い総資産回転率（資本の効率的活用）"
        else:
            factor = "レバレッジ活用"
        dupont_comment = f"ROE（株主資本利益率）は {name_a}（{ma.roe_curr:.1f}%）が {name_b}（{mb.roe_curr:.1f}%）を上回っており、特に『{factor}』が主たる牽引役となっています。"
    else:
        if mb.dupont_margin_curr > ma.dupont_margin_curr:
            factor = "高マージン（純利益率の高さ）"
        elif mb.dupont_turnover_curr > ma.dupont_turnover_curr:
            factor = "高い総資産回転率（資本の効率的活用）"
        else:
            factor = "レバレッジ活用"
        dupont_comment = f"ROE（株主資本利益率）は {name_b}（{mb.roe_curr:.1f}%）が {name_a}（{ma.roe_curr:.1f}%）を上回っており、特に『{factor}』が主たる牽引役となっています。"
    highlights.append(f"【デュポン資本効率分析】{dupont_comment}")

    # ライフサイエンス業界総括
    commentary = (
        f"### 🔬 ライフサイエンス・アナリスト比較総括\n\n"
        f"**{name_a}** と **{name_b}** をライフサイエンス・ヘルスケアの事業構造の観点から比較すると、以下の特徴が明確です：\n\n"
        + "\n".join([f"・{h}" for h in highlights]) + "\n\n"
        f"**投資・事業戦略の視点:**\n"
        f"- ライフサイエンス業界において新薬・高度医療機器の創出には数百億〜数千億円規模の研究開発投資（R&D）と10年スパンの開発期間を要します。\n"
        f"- **{scale_leader}** は豊富なキャッシュフローとスケールを活かしたグローバル大型臨床試験・M&Aの実行力に長けており、一方で **{prof_leader}** は高収益な主力製品ポートフォリオにより高い資本効率を創出しています。"
    )

    return {
        "scale_leader": scale_leader,
        "profitability_leader": prof_leader,
        "safety_leader": safety_leader,
        "roe_leader": roe_leader,
        "highlights": highlights,
        "commentary": commentary
    }

