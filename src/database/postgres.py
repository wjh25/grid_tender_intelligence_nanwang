"""PostgreSQL 写入模块。

当前远端没有安装 psycopg/psycopg2，因此先通过 Docker 容器内的 psql
完成最小入库闭环。后续正式运行可替换为 psycopg 连接池。
"""

from __future__ import annotations

import base64
import json
import subprocess
from typing import Any


CONTAINER = "grid-tender-postgres"
DB_NAME = "grid_tender"
DB_USER = "grid_tender"


def run_sql(sql: str) -> None:
    """通过容器内 psql 执行 SQL。"""
    subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-v", "ON_ERROR_STOP=1"],
        input=sql,
        text=True,
        check=True,
    )


def save_document(
    row: dict[str, Any],
    blocks: list[dict[str, Any]],
    requirements: list[dict[str, Any]] | None = None,
) -> None:
    """保存原始页面、文档、展示 blocks 和项目关系表。"""
    run_sql(_build_document_sql(row, blocks, requirements or []))


def _build_document_sql(row: dict[str, Any], blocks: list[dict[str, Any]], requirements: list[dict[str, Any]]) -> str:
    source_url = _sql_text(row.get("source_url"))
    document_id = f"(SELECT id FROM tender_documents WHERE source_url = {source_url})"
    document_json = {
        "source_url": row.get("source_url"),
        "title": row.get("title"),
        "announcement_type": row.get("announcement_type"),
        "project_code": row.get("project_code"),
        "blocks": blocks,
    }
    block_values = _block_values(blocks)
    requirement_values = _requirement_values(requirements)

    return f"""
BEGIN;

INSERT INTO tender_sources(name, base_url, source_type)
VALUES ('南方电网供应链统一服务平台', 'https://www.bidding.csg.cn', 'southern_grid')
ON CONFLICT (name, base_url) DO UPDATE SET source_type = excluded.source_type;

INSERT INTO crawl_pages(source_id, url, url_hash, http_status, raw_html, raw_text, content_hash)
SELECT
  id,
  {source_url},
  {_sql_text(row.get("url_hash"))},
  200,
  {_sql_text(row.get("raw_html"))},
  {_sql_text(row.get("raw_text"))},
  {_sql_text(row.get("content_hash"))}
FROM tender_sources
WHERE name = '南方电网供应链统一服务平台'
ON CONFLICT (url) DO UPDATE SET
  fetched_at = now(),
  http_status = excluded.http_status,
  raw_html = excluded.raw_html,
  raw_text = excluded.raw_text,
  content_hash = excluded.content_hash;

INSERT INTO tender_documents(
  source_id, crawl_page_id, source_url, url_hash, title, announcement_type,
  purchase_category, company_name, publish_date, project_name, project_code,
  source_list_url, source_list_order, buyer, agency, document_json, raw_text,
  content_hash, last_seen_at, is_latest
)
SELECT
  s.id,
  c.id,
  {source_url},
  {_sql_text(row.get("url_hash"))},
  {_sql_text(row.get("title"))},
  {_sql_text(row.get("announcement_type"))},
  {_sql_text(row.get("purchase_category"))},
  {_sql_text(row.get("company_name"))},
  {_sql_date(row.get("publish_date"))},
  {_sql_text(row.get("project_name"))},
  {_sql_text(row.get("project_code"))},
  {_sql_text(row.get("source_list_url"))},
  {_sql_int(row.get("source_list_order"))},
  {_sql_text(row.get("buyer"))},
  {_sql_text(row.get("agency"))},
  {_sql_jsonb(document_json)},
  {_sql_text(row.get("raw_text"))},
  {_sql_text(row.get("content_hash"))},
  now(),
  true
FROM tender_sources s
JOIN crawl_pages c ON c.url = {source_url}
WHERE s.name = '南方电网供应链统一服务平台'
ON CONFLICT (source_url) DO UPDATE SET
  crawl_page_id = excluded.crawl_page_id,
  title = excluded.title,
  announcement_type = excluded.announcement_type,
  purchase_category = excluded.purchase_category,
  company_name = excluded.company_name,
  publish_date = excluded.publish_date,
  project_name = excluded.project_name,
  project_code = excluded.project_code,
  source_list_url = excluded.source_list_url,
  source_list_order = excluded.source_list_order,
  buyer = excluded.buyer,
  agency = excluded.agency,
  document_json = excluded.document_json,
  raw_text = excluded.raw_text,
  content_hash = excluded.content_hash,
  last_seen_at = now();

DELETE FROM document_blocks WHERE document_id = {document_id};
DELETE FROM tender_projects WHERE document_id = {document_id};
DELETE FROM tender_requirements WHERE document_id = {document_id};
DELETE FROM extraction_runs WHERE document_id = {document_id};

INSERT INTO document_blocks(
  document_id, block_order, block_type, heading_level, section_no, title,
  text_content, table_json, block_json
)
SELECT
  {document_id},
  v.block_order,
  v.block_type,
  v.heading_level,
  v.section_no,
  v.title,
  v.text_content,
  v.table_json,
  v.block_json
FROM (
  VALUES
  {block_values}
) AS v(block_order, block_type, heading_level, section_no, title, text_content, table_json, block_json);

INSERT INTO tender_projects(
  document_id, project_code, project_name, buyer, agency, company_name, publish_date, raw_json
)
VALUES (
  {document_id},
  {_sql_text(row.get("project_code"))},
  {_sql_text(row.get("project_name"))},
  {_sql_text(row.get("buyer"))},
  {_sql_text(row.get("agency"))},
  {_sql_text(row.get("company_name"))},
  {_sql_date(row.get("publish_date"))},
  {_sql_jsonb(row)}
);

INSERT INTO tender_requirements(
  document_id, requirement_order, requirement_type, requirement_title, requirement_text, raw_json
)
SELECT
  {document_id},
  v.requirement_order,
  v.requirement_type,
  v.requirement_title,
  v.requirement_text,
  v.raw_json
FROM (
  VALUES
  {requirement_values}
) AS v(requirement_order, requirement_type, requirement_title, requirement_text, raw_json);

INSERT INTO extraction_runs(document_id, extractor_version, status, result_json)
VALUES (
  {document_id},
  'nanwang-jsonb-blocks-v1',
  'success',
  {_sql_jsonb({"block_count": len(blocks), "requirement_count": len(requirements), "project_code": row.get("project_code")})}
);

COMMIT;
"""


def _block_values(blocks: list[dict[str, Any]]) -> str:
    if not blocks:
        blocks = [
            {
                "block_order": 1,
                "block_type": "paragraph",
                "heading_level": None,
                "section_no": None,
                "title": None,
                "text_content": "",
                "table_json": None,
                "block_json": {"type": "paragraph", "text": ""},
            }
        ]
    return ",\n".join(
        "("
        + ", ".join(
            [
                _sql_int(block.get("block_order")),
                _sql_text(block.get("block_type")),
                _sql_int(block.get("heading_level")),
                _sql_text(block.get("section_no")),
                _sql_text(block.get("title")),
                _sql_text(block.get("text_content")),
                _sql_jsonb(block.get("table_json")),
                _sql_jsonb(block.get("block_json")),
            ]
        )
        + ")"
        for block in blocks
    )


def _requirement_values(requirements: list[dict[str, Any]]) -> str:
    if not requirements:
        requirements = [
            {
                "requirement_order": 1,
                "requirement_type": "未识别招标要求",
                "requirement_title": "未识别招标要求",
                "requirement_text": "",
                "raw_json": {},
            }
        ]
    return ",\n".join(
        "("
        + ", ".join(
            [
                _sql_int(item.get("requirement_order")),
                _sql_text(item.get("requirement_type")),
                _sql_text(item.get("requirement_title")),
                _sql_text(item.get("requirement_text")),
                _sql_jsonb(item.get("raw_json")),
            ]
        )
        + ")"
        for item in requirements
    )


def _sql_text(value: Any) -> str:
    if value is None or value == "":
        return "NULL"
    encoded = base64.b64encode(str(value).encode("utf-8")).decode("ascii")
    return f"convert_from(decode('{encoded}', 'base64'), 'UTF8')"


def _sql_jsonb(value: Any) -> str:
    if value is None:
        return "NULL::jsonb"
    encoded = base64.b64encode(json.dumps(value, ensure_ascii=False).encode("utf-8")).decode("ascii")
    return f"convert_from(decode('{encoded}', 'base64'), 'UTF8')::jsonb"


def _sql_date(value: Any) -> str:
    if value is None or value == "":
        return "NULL"
    return f"{_sql_text(value)}::date"


def _sql_int(value: Any) -> str:
    if value is None or value == "":
        return "NULL"
    return str(int(value))
