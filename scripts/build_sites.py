#!/usr/bin/env python3
"""
build_sites.py
----------------
data/salons.json + data/generated_copy.json を組み合わせて、
templates/salon_template.html から各店舗の静的サイトを output/<id>/index.html に生成する。
さらに全店舗をまとめた一覧ページ output/index.html（自社の実績ポートフォリオ用）も作る。

使い方:
    python3 scripts/build_sites.py                # is_demo=True で全件ビルド（提案用）
    python3 scripts/build_sites.py --live hair-salon-lego   # 契約後、透かしなしで1件だけ本番ビルド
"""

import json
import argparse
import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output"

STUDIO_NAME = "（貴社の屋号をここに設定）"  # README参照: config.json 等に切り出してもよい


def maps_url(place_id: str) -> str:
    return f"https://www.google.com/maps/place/?q=place_id:{place_id}"


def format_phone(raw: str) -> str:
    return raw if raw else "電話番号未掲載"


def build_context(salon, copy, is_demo):
    return {
        "id": salon["id"],
        "name": salon["name"],
        "area": salon["area"],
        "address": salon["address"],
        "phone": format_phone(salon.get("phone", "")),
        "phone_raw": salon.get("phone", "").replace("-", ""),
        "rating": salon.get("rating"),
        "rating_count": salon.get("rating_count"),
        "specialty": salon.get("specialty", ""),
        "hours": salon["hours"],
        "maps_url": maps_url(salon["place_id"]),
        "catch_copy": copy["catch_copy"],
        "about_text": copy["about_text"],
        "features": copy["features"],
        "cta_text": copy["cta_text"],
        "is_demo": is_demo,
        "studio_name": STUDIO_NAME,
        "year": datetime.date.today().year,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        metavar="SALON_ID",
        help="指定した店舗IDを『契約後・透かしなし』の本番ビルドにする",
    )
    parser.add_argument("--only", metavar="SALON_ID", help="指定した1店舗だけビルドする（透かしは付けたまま）")
    args = parser.parse_args()

    salons = json.loads((DATA_DIR / "salons.json").read_text(encoding="utf-8"))
    copies = json.loads((DATA_DIR / "generated_copy.json").read_text(encoding="utf-8"))

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("salon_template.html")

    OUTPUT_DIR.mkdir(exist_ok=True)
    built = []

    for salon in salons:
        sid = salon["id"]
        if args.only and sid != args.only:
            continue
        if sid not in copies:
            print(f"[skip] {sid}: generated_copy.json にコピーがありません。先に generate_copy.py を実行してください。")
            continue

        is_demo = not (args.live and args.live == sid)
        ctx = build_context(salon, copies[sid], is_demo)
        html = template.render(**ctx)

        site_dir = OUTPUT_DIR / sid
        site_dir.mkdir(exist_ok=True)
        (site_dir / "index.html").write_text(html, encoding="utf-8")
        built.append((sid, salon["name"], salon["area"], is_demo))
        print(f"built: output/{sid}/index.html  ({'DEMO' if is_demo else 'LIVE'})")

    # 一覧ページ（自社ポートフォリオ用）
    if not args.only and not args.live:
        index_html = render_index(built)
        (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
        print("built: output/index.html (portfolio index)")


def render_index(built):
    rows = "\n".join(
        f'<li><a href="./{sid}/">{name}</a><span>{area}</span></li>'
        for sid, name, area, _ in built
    )
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<title>サンプルサイト一覧</title>
<style>
  body{{font-family:sans-serif; max-width:640px; margin:60px auto; padding:0 20px; color:#2B2622;}}
  li{{display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px solid #DCD1BC;}}
  a{{color:#A9613A; text-decoration:none; font-weight:600;}}
  span{{color:#8A8175; font-size:13px;}}
</style></head>
<body>
<h1>提案用サンプルサイト一覧</h1>
<ul>{rows}</ul>
</body></html>"""


if __name__ == "__main__":
    main()
