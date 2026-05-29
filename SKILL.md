---
name: grid-tender-intelligence-nanwang
description: "南方电网供应链统一服务平台招投标资料采集 skill。使用 Playwright 抓取南网公开采购公告/招标公告/中标候选人/中标结果详情页，将原始网页、Document Blocks、JSONB Raw Payload 和项目/招标要求等 Business Tables 保存到 PostgreSQL。当前重点支持采购公告-招标公告列表 https://www.bidding.csg.cn/zbgg/index.jhtml 按日期增量采集。"
user-invocable: true
---

# Grid Tender Intelligence Nanwang

## Current Scope

This skill is dedicated to China Southern Power Grid Supply Chain Platform public tender data.

Primary supported list page:

```text
https://www.bidding.csg.cn/zbgg/index.jhtml
```

Primary supported detail pages:

```text
https://www.bidding.csg.cn/zbgg/*.jhtml
```

Current working task:

```text
采购公告 -> 招标公告 -> 列表页按日期过滤 -> 打开详情页 -> 保存原始网页、正文 blocks、招标要求和项目字段到 PostgreSQL
```

Do not modify the older `grid_tender_intelligence` skill when working here.

## Data Model

Use PostgreSQL with this hybrid storage model:

```text
Document Blocks + Business Tables + JSONB Raw Payload
```

This is not three pieces of software. It is one PostgreSQL database with three storage styles:

- `Document Blocks`: save page content as ordered blocks for website rendering.
- `Business Tables`: save project, requirement, package, candidate, award, and attachment fields for search/statistics/bot usage.
- `JSONB Raw Payload`: preserve complex source data and extracted payloads without losing detail.

Core tables:

- `crawl_pages`: raw URL, raw HTML, raw text, fetch time, content hash.
- `tender_documents`: main announcement record, including title, type, publish date, project code, source URL, and `document_json`.
- `document_blocks`: ordered content blocks such as heading, paragraph, and table-like text.
- `tender_requirements`: extracted tender requirements such as 招标条件, 投标人资格要求, 招标文件获取, 投标文件递交, 开标时间, 联系方式.
- `tender_projects`: structured project-level fields.
- `tender_packages`: package data for future table extraction.
- `tender_candidates`: candidate winner data for future candidate announcement extraction.
- `tender_awards`: final award data for future winner result extraction.
- `tender_attachments`: attachment metadata.
- `extraction_runs`: extractor version and run results.
- `tender_sources`: source platform metadata.

Useful views:

- `v_tender_purchase_notice_summary`: procurement/tender announcement summary.
- `v_tender_requirements_flat`: flattened tender requirements.
- `v_tender_document_summary`: general document summary.
- `v_document_blocks_flat`: ordered blocks for inspection.

Always use explicit ordering. PostgreSQL table physical order is not reliable.

Recommended order for procurement announcement display:

```sql
ORDER BY publish_date DESC, source_list_order ASC, id DESC
```

## Working Commands

Run from the remote machine:

```bash
cd /home/untu/.openclaw/workspace/skills/grid_tender_intelligence_nanwang
```

Collect today's procurement tender announcements:

```bash
PYTHONPATH=src python3 src/main.py \
  --list-url https://www.bidding.csg.cn/zbgg/index.jhtml \
  --since-date 2026-05-29 \
  --limit 10
```

Collect one deterministic detail page:

```bash
PYTHONPATH=src python3 src/main.py \
  --detail-url https://www.bidding.csg.cn/zbgg/1200431105.jhtml \
  --limit 1
```

Reset PostgreSQL schema:

```bash
docker exec -i grid-tender-postgres psql -U grid_tender -d grid_tender \
  < /home/untu/.openclaw/workspace/skills/grid_tender_intelligence_nanwang/src/database/postgres_schema.sql
```

Inspect summary:

```bash
docker exec grid-tender-postgres psql -U grid_tender -d grid_tender \
  -c "select id, publish_date, source_list_order, project_code, left(title, 70) as title from tender_documents order by publish_date desc, source_list_order asc, id desc;"
```

## Current PostgreSQL

Remote host:

```text
172.16.1.101
```

Docker container:

```text
grid-tender-postgres
```

Database:

```text
grid_tender
```

User:

```text
grid_tender
```

Password:

```text
<DB_PASSWORD>
```

Container port binding:

```text
127.0.0.1:5432 -> 5432/tcp
```

OpenClaw runs on the same remote host as this Docker container (`172.16.1.101`), so normal skill execution does not need an SSH tunnel.

Use either:

```text
host: 127.0.0.1
port: 5432
database: grid_tender
user: grid_tender
password: <DB_PASSWORD>
```

or the current code path:

```text
docker exec -i grid-tender-postgres psql -U grid_tender -d grid_tender
```

The database is intentionally bound only to the remote host's localhost, not to the LAN. From the Mac, an SSH tunnel is only needed for pgAdmin or other local Mac tools:

```bash
sshpass -p <SSH_PASSWORD> ssh -f -N -L 15432:127.0.0.1:5432 untu@172.16.1.101
```

pgAdmin on Mac was configured through that optional tunnel as:

```text
Group: Grid Tender
Name: grid_tender_intelligence_nanwang
Host: 127.0.0.1
Port: 15432
Database: grid_tender
Username: grid_tender
PasswordExecCommand: /bin/echo <DB_PASSWORD>
```

## Code Map

```text
src/main.py
```

Command-line entrypoint. Supports `--list-url`, `--since-date`, `--detail-url`, and `--limit`.

```text
src/crawler/southern_grid_playwright.py
```

Uses Playwright to collect list items and detail page HTML/text. Extracts list order, list date, company, title, and detail URL.

```text
src/parser/southern_grid_parser.py
```

Cleans detail text and extracts announcement-level fields: title, project code, buyer, agency, publish date, company, content hash.

```text
src/extractor/tender_sections.py
```

Converts text into ordered blocks and extracts tender requirement content.

```text
src/database/postgres.py
```

Writes data to PostgreSQL via `docker exec ... psql`. This avoids requiring psycopg on the remote host. Later this can be replaced with a direct psycopg connection pool.

```text
src/database/postgres_schema.sql
```

Current database schema and views.

## Known Current State

On 2026-05-29, the `zbgg` list page had two same-day items and both were successfully collected:

- `1200431105.jhtml`, project code `CG2100022002324345`
- `1200431104.jhtml`, project code `CG0500022002312072`

Current expected counts after resetting and collecting those two:

```text
tender_documents: 2
document_blocks: 59
tender_requirements: 16
```

## Safety

- Only collect publicly available pages.
- Do not bypass login, CAPTCHA, CA certificate login, access control, or restricted attachment downloads.
- If a page or attachment requires login, save only public metadata and stop.
- Keep request frequency low.
- Preserve source URL and raw content for auditability.
