from __future__ import annotations

import argparse
import json

from crawler.southern_grid_playwright import collect_list_items_since, fetch_detail
from database.postgres import save_document
from extractor.tender_sections import extract_blocks, extract_requirements
from parser.southern_grid_parser import parse_detail_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl Southern Grid tender data once and save to PostgreSQL")
    parser.add_argument("--list-url", default="https://www.bidding.csg.cn/zbgg/index.jhtml")
    parser.add_argument("--since-date", default="2026-05-29")
    parser.add_argument("--detail-url", help="Optional detail URL for a deterministic single-page test")
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()

    list_items = []
    if args.detail_url:
        detail_urls = [args.detail_url]
    else:
        list_items = collect_list_items_since(args.list_url, args.since_date, args.limit)
        detail_urls = [item.url for item in list_items]

    results = []
    for index, url in enumerate(detail_urls[: args.limit]):
        detail = fetch_detail(url)
        row = parse_detail_text(detail.title, detail.url, detail.html, detail.text)
        if list_items:
            row["source_list_url"] = list_items[index].list_url
            row["source_list_order"] = list_items[index].list_order
            row["company_name"] = row.get("company_name") or list_items[index].company_name
            row["publish_date"] = row.get("publish_date") or list_items[index].publish_date
            row["announcement_type"] = row.get("announcement_type") or list_items[index].announcement_type
        blocks = extract_blocks(row["raw_text"], detail.html)
        requirements = extract_requirements(blocks)
        save_document(row, blocks, requirements)
        results.append(
            {
                "url": url,
                "title": row.get("title"),
                "project_code": row.get("project_code"),
                "publish_date": row.get("publish_date"),
                "blocks": len(blocks),
                "requirements": len(requirements),
                "headings": [block["title"] for block in blocks if block["block_type"] == "heading"],
            }
        )

    print(json.dumps({"saved": len(results), "since_date": args.since_date, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
