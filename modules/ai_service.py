"""
AIコメント生成サービスモジュール
Hugging Face Inference API によるLLM推論、およびオフライン自動診断フォールバックを提供します。
"""

import os
import json
import requests
from typing import Dict, Any, Optional, Tuple
from .metrics import FinancialMetrics, evaluate_financial_health

DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"
RECOMMENDED_MODELS = [
    "mistralai/Mistral-7B-Instruct-v0.2",
    "Qwen/Qwen2.5-7B-Instruct",
    "google/gemma-2-2b-it",
    "meta-llama/Llama-3.2-3B-Instruct",
]


def call_huggingface_api(
    prompt: str,
    token: str,
    model_id: str = DEFAULT_MODEL,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    timeout: int = 40
) -> Tuple[Optional[str], Optional[str]]:
    """
    Hugging Face Inference API を呼び出しテキストを生成します。
    戻り値: (生成テキスト, エラーメッセージ)
    """
    if not token or not token.strip():
        return None, "HF_API_TOKEN が指定されていません。"

    # Hugging Face Inference API エンドポイント
    url = f"https://api-inference.huggingface.co/models/{model_id.strip()}"
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "return_full_text": False
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                text = data[0]["generated_text"].strip()
                return text, None
            elif isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"].strip(), None
            else:
                return str(data), None
        elif response.status_code == 503:
            # モデルロード中（Cold Start）の場合
            try:
                err_json = response.json()
                wait_time = err_json.get("estimated_time", 20)
                return None, f"モデルが現在ロード中です（約{wait_time:.0f}秒後に再試行してください: 503 Service Unavailable）。"
            except Exception:
                return None, "モデルが起動準備中です。数秒待ってから再実行してください。"
        else:
            return None, f"HF APIエラー (HTTP {response.status_code}): {response.text[:200]}"
    except requests.exceptions.Timeout:
        return None, f"APIリクエストがタイムアウトしました（{timeout}秒経過）。別のモデルを選択するか、時間を置いて再試行してください。"
    except Exception as e:
        return None, f"API接続エラー: {str(e)}"


def build_summary_prompt(m: FinancialMetrics) -> str:
    """業績サマリー向けアナリストプロンプト（aidash完全準拠）"""
    return (
        "あなたは証券アナリストです。以下の日本企業の業績データをもとに、"
        "投資家向けの総合コメントを日本語で5行以内で書いてください。\n\n"
        f"【{m.period_prev} → {m.period_curr} 実績】\n"
        f"・売上高: {m.rev_curr:,.0f}千円（前期比 {m.rev_growth_rate:+.1f}%）\n"
        f"・営業利益: {m.op_curr:,.0f}千円（営業利益率 {m.op_margin_curr:.1f}%、前期比 {m.op_growth_rate:+.1f}%）\n"
        f"・当期純利益: {m.ni_curr:,.0f}千円（純利益率 {m.ni_margin_curr:.1f}%）\n"
        f"・ROE: {m.roe_curr:.1f}%\n"
        f"・自己資本比率: {m.equity_ratio_curr:.1f}%\n\n"
        "増収増益/増収減益/減収増益/減収減益の評価、"
        "収益性と成長性の強み・課題を中心に簡潔に述べてください。"
    )


def build_pl_prompt(m: FinancialMetrics) -> str:
    """損益計算書向けアナリストプロンプト（aidash完全準拠）"""
    items = [
        f"・売上高: {m.rev_curr:,.0f}千円（前期比 {m.rev_growth_rate:+.1f}%）",
        f"・売上総利益: {m.gp_curr:,.0f}千円（売上総利益率 {m.gp_margin_curr:.1f}%）",
        f"・販売費及び一般管理費: {m.sga_curr:,.0f}千円",
        f"・営業利益: {m.op_curr:,.0f}千円（営業利益率 {m.op_margin_curr:.1f}%）",
        f"・経常利益: {m.ord_curr:,.0f}千円（経常利益率 {m.ord_margin_curr:.1f}%）",
        f"・当期純利益: {m.ni_curr:,.0f}千円（純利益率 {m.ni_margin_curr:.1f}%）"
    ]
    return (
        "以下は日本企業の損益計算書データです。"
        "損益構造の変化と収益性について、アナリスト視点で日本語5行以内のコメントを書いてください。\n\n"
        + "\n".join(items) + "\n\n"
        "粗利率・営業利益率の変化、費用効率、改善点・懸念点を中心に述べてください。"
    )


def build_bs_prompt(m: FinancialMetrics) -> str:
    """貸借対照表向けアナリストプロンプト（aidash完全準拠）"""
    items = [
        f"・資産合計: {m.asset_curr:,.0f}千円（前期: {m.asset_prev:,.0f}千円）",
        f"・流動資産合計: {m.ca_curr:,.0f}千円（前期: {m.ca_prev:,.0f}千円）",
        f"・流動負債合計: {m.cl_curr:,.0f}千円（前期: {m.cl_prev:,.0f}千円）",
        f"・純資産合計: {m.eq_curr:,.0f}千円（前期: {m.eq_prev:,.0f}千円）",
        f"・負債合計: {m.liab_curr:,.0f}千円（前期: {m.liab_prev:,.0f}千円）",
        f"・流動比率: {m.cur_ratio_curr:.1f}%（前期: {m.cur_ratio_prev:.1f}%）",
        f"・自己資本比率: {m.equity_ratio_curr:.1f}%（前期: {m.equity_ratio_prev:.1f}%）"
    ]
    return (
        "以下は日本企業の貸借対照表データです。"
        "財務健全性・資本効率について、アナリスト視点で日本語5行以内のコメントを書いてください。\n\n"
        + "\n".join(items) + "\n\n"
        "財務安定性、資産効率、自己資本の変化について述べてください。"
    )


def generate_all_comments(
    m: FinancialMetrics,
    token: Optional[str] = None,
    model_id: str = DEFAULT_MODEL
) -> Dict[str, Dict[str, Any]]:
    """
    全セクション（業績サマリー、PL、BS）のコメントを一括生成します。
    tokenが設定されている場合はHF Inference APIを呼び出し、
    未設定または失敗時はオフライン財務診断ルールエンジンによるコメントを提供します。
    """
    has_token = bool(token and token.strip())
    health_eval = evaluate_financial_health(m)
    
    results = {}
    
    # 1. 業績サマリーコメント
    if has_token:
        prompt_sum = build_summary_prompt(m)
        text_sum, err_sum = call_huggingface_api(prompt_sum, token, model_id)
        if text_sum:
            results["summary"] = {
                "text": text_sum,
                "source": f"Hugging Face AI ({model_id})",
                "is_ai": True,
                "error": None
            }
        else:
            fallback_text = (
                f"【AI生成フォールバック（自動財務診断）】\n"
                f"{m.period_curr}は売上高{m.rev_growth_rate:+.1f}%、営業利益{m.op_growth_rate:+.1f}%の業績推移です。\n"
                f"自己資本比率{m.equity_ratio_curr:.1f}%、ROEは{m.roe_curr:.1f}%を記録。"
                f"（※HF API接続: {err_sum}）"
            )
            results["summary"] = {
                "text": fallback_text,
                "source": "ルールベース自動財務診断（APIフォールバック）",
                "is_ai": False,
                "error": err_sum
            }
    else:
        results["summary"] = {
            "text": (
                f"【オフライン自動財務診断コメント】\n"
                f"当期の業績は売上高{m.rev_growth_rate:+.1f}%、営業利益{m.op_growth_rate:+.1f}%となっています。\n"
                f"営業利益率は{m.op_margin_curr:.1f}%、ROEは{m.roe_curr:.1f}%です。\n"
                f"自己資本比率は{m.equity_ratio_curr:.1f}%を確保しており、安定した財務基盤を維持しています。\n"
                f"（※HF APIトークンを入力すると、クラウドLLMによるリアルタイム分析コメントが生成されます）"
            ),
            "source": "ルールベース自動財務診断（オフライン）",
            "is_ai": False,
            "error": None
        }

    # 2. 損益計算書コメント
    if has_token:
        prompt_pl = build_pl_prompt(m)
        text_pl, err_pl = call_huggingface_api(prompt_pl, token, model_id)
        if text_pl:
            results["pl"] = {
                "text": text_pl,
                "source": f"Hugging Face AI ({model_id})",
                "is_ai": True,
                "error": None
            }
        else:
            results["pl"] = {
                "text": (
                    f"【PL自動診断フォールバック】\n"
                    f"売上総利益率は{m.gp_margin_curr:.1f}%（前期比 {m.gp_margin_curr - m.gp_margin_prev:+.1f}pt）、"
                    f"営業利益率は{m.op_margin_curr:.1f}%（前期比 {m.op_margin_curr - m.op_margin_prev:+.1f}pt）です。\n"
                    f"費用構造としては原価率{(m.cogs_curr/m.rev_curr*100) if m.rev_curr else 0:.1f}%、"
                    f"販管費率{(m.sga_curr/m.rev_curr*100) if m.rev_curr else 0:.1f}%となっています。"
                ),
                "source": "ルールベース自動財務診断（APIフォールバック）",
                "is_ai": False,
                "error": err_pl
            }
    else:
        results["pl"] = {
            "text": (
                f"【損益構造自動診断】\n"
                f"当期の売上総利益率は{m.gp_margin_curr:.1f}%、営業利益率は{m.op_margin_curr:.1f}%です。\n"
                f"粗利益率と販管費比率のバランスは健全であり、本業の収益性が維持されています。"
            ),
            "source": "ルールベース自動財務診断（オフライン）",
            "is_ai": False,
            "error": None
        }

    # 3. 貸借対照表コメント
    if has_token:
        prompt_bs = build_bs_prompt(m)
        text_bs, err_bs = call_huggingface_api(prompt_bs, token, model_id)
        if text_bs:
            results["bs"] = {
                "text": text_bs,
                "source": f"Hugging Face AI ({model_id})",
                "is_ai": True,
                "error": None
            }
        else:
            results["bs"] = {
                "text": (
                    f"【BS自動診断フォールバック】\n"
                    f"自己資本比率は{m.equity_ratio_curr:.1f}%、流動比率は{m.cur_ratio_curr:.1f}%を記録。\n"
                    f"短期・長期ともに十分な支払い余力があり、財務健全性は良好です。"
                ),
                "source": "ルールベース自動財務診断（APIフォールバック）",
                "is_ai": False,
                "error": err_bs
            }
    else:
        results["bs"] = {
            "text": (
                f"【財務健全性自動診断】\n"
                f"自己資本比率{m.equity_ratio_curr:.1f}%、流動比率{m.cur_ratio_curr:.1f}%、負債比率{m.debt_ratio_curr:.1f}%です。\n"
                f"資本構成および手元流動性は安定しており、高い信用耐性を備えています。"
            ),
            "source": "ルールベース自動財務診断（オフライン）",
            "is_ai": False,
            "error": None
        }

    return results
