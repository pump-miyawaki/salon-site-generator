#!/usr/bin/env python3
"""
generate_copy.py
-----------------
候補店舗データ（data/salons.json）を読み込み、Claude API に「事実情報だけ」を渡して
各店舗のサイト用コピー（キャッチコピー・紹介文・特徴3点・CTA文）を生成し、
data/generated_copy.json に保存する。

使い方:
    export ANTHROPIC_API_KEY=sk-ant-xxxx
    python3 scripts/generate_copy.py                 # 未生成の店舗だけ生成
    python3 scripts/generate_copy.py --force          # 全店舗を再生成
    python3 scripts/generate_copy.py --id hair-salon-lego  # 特定の1店舗だけ

設計方針:
  - Claude には salons.json に実在するフィールド（店名・エリア・営業時間・得意分野・評価件数）
    しか渡さない。実在しない技術・スタッフ名・受賞歴などを「創作」させないための
    ガードレールをプロンプトに明記している。
  - 出力は JSON 形式に固定し、そのまま build_sites.py が読み込める形にする。
  - 口コミの引用（コピペ）は絶対に行わない設計（レビュー本文はそもそも渡さない）。
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path

try:
    import anthropic
except ImportError:
    anthropic = None

ROOT = Path(__file__).resolve().parent.parent
SALONS_PATH = ROOT / "data" / "salons.json"
OUTPUT_PATH = ROOT / "data" / "generated_copy.json"

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """あなたは地方の個人経営美容室のための Web コピーライターです。
渡された「事実情報」だけを根拠に、誠実で温かみのある紹介文を書いてください。

厳守事項:
- 渡された情報に存在しない事実（スタッフ名、受賞歴、具体的な技術名、価格など）を創作しない。
- 誇大な表現（「日本一」「絶対」など）を使わない。
- Google 口コミの文章を引用・要約して転記しない（評価点数と件数のみ事実として使ってよい）。
- 出力は指定された JSON 形式のみ。前後に説明文を書かない。
"""

USER_PROMPT_TEMPLATE = """以下の店舗の事実情報をもとに、Web サイト用のコピーを作成してください。

店舗名: {name}
エリア: {area}
住所: {address}
得意分野・特徴タグ: {specialty}
Google評価: {rating_line}
営業時間パターン: {hours_summary}

次の JSON 形式で出力してください（この形式以外は出力しないこと）:

{{
  "catch_copy": "20〜40文字程度のキャッチコピー（1文）",
  "about_text": "150〜220文字程度の紹介文（3〜4文、事実情報のみを根拠にする）",
  "features": [
    {{"tag": "2〜4文字の見出しラベル", "title": "短いフレーズ（10文字程度）", "desc": "1文の説明（30文字程度）"}},
    {{"tag": "...", "title": "...", "desc": "..."}},
    {{"tag": "...", "title": "...", "desc": "..."}}
  ],
  "cta_text": "予約・問い合わせを促す1〜2文"
}}
"""


def summarize_hours(hours):
    days_open = [h for h in hours if "定休" not in h[1]]
    if not days_open:
        return "不定休"
    times = set(t for _, t in days_open)
    if len(times) == 1:
        return f"営業時間 {times.pop()}（詳細は店舗へ確認）"
    return "曜日により営業時間が異なる"


def build_user_prompt(salon):
    rating = salon.get("rating")
    rating_count = salon.get("rating_count")
    if rating:
        rating_line = f"{rating} / 5.0（{rating_count}件）"
    else:
        rating_line = "口コミ件数がまだ少ない、または新規"
    return USER_PROMPT_TEMPLATE.format(
        name=salon["name"],
        area=salon["area"],
        address=salon["address"],
        specialty=salon.get("specialty", ""),
        rating_line=rating_line,
        hours_summary=summarize_hours(salon["hours"]),
    )


def call_claude(client, salon, max_retries=3):
    prompt = build_user_prompt(salon)
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=800,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(text)
        except Exception as e:
            print(f"  [warn] {salon['id']} attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(2 * attempt)
    raise RuntimeError(f"Failed to generate copy for {salon['id']} after {max_retries} attempts")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="既存の生成済みコピーも上書きする")
    parser.add_argument("--id", help="特定の店舗IDだけ処理する")
    args = parser.parse_args()

    salons = json.loads(SALONS_PATH.read_text(encoding="utf-8"))
    existing = {}
    if OUTPUT_PATH.exists():
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    targets = [s for s in salons if not args.id or s["id"] == args.id]
    pending = [s for s in targets if args.force or s["id"] not in existing]

    if not pending:
        print("生成対象なし（全店舗すでにコピー済み）。API呼び出しなしで終了します。")
        return

    if anthropic is None:
        sys.exit("先に `pip install anthropic` を実行してください。")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("環境変数 ANTHROPIC_API_KEY を設定してください（新規店舗のコピー生成が必要です）。")

    client = anthropic.Anthropic(api_key=api_key)

    for salon in pending:
        print(f"generating: {salon['id']} ({salon['name']}) ...")
        copy = call_claude(client, salon)
        existing[salon["id"]] = copy
        OUTPUT_PATH.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        time.sleep(1)  # レート制限への配慮

    print(f"done. -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
