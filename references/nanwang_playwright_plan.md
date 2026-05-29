# 南网招投标采集实现记录

## 目标

当前 skill 聚焦南方电网供应链统一服务平台：

```text
https://www.bidding.csg.cn/zbgg/index.jhtml
```

采集“采购公告 -> 招标公告”，按日期过滤，打开详情页，保存：

- 原始网页 HTML
- 原始正文文本
- 网站展示用 Document Blocks
- 招标要求 tender_requirements
- 项目字段 tender_projects
- JSONB 原始 payload

## 为什么使用 PostgreSQL + JSONB

南网页面格式复杂，可能包含：

- 标题
- 分段
- 二级小节
- 表格
- 附件
- 候选人名单
- 中标结果

纯关系表会太僵硬，纯 NoSQL 又不方便统计和筛选。

因此采用：

```text
Document Blocks + Business Tables + JSONB Raw Payload
```

含义：

- Document Blocks：按顺序保存网页内容块，给网站渲染。
- Business Tables：保存项目、招标要求、标包、候选人、中标结果等可查询字段。
- JSONB Raw Payload：保留复杂原始结构，避免解析规则不完整时丢数据。

## 列表页采集

模块：

```text
src/crawler/southern_grid_playwright.py
```

流程：

```text
打开列表页
等待 networkidle
提取 a[href*='.jhtml']
过滤 /zbgg/、/gsgg/、/zbgs/、/cgxx/
去重
提取 row_text
从 row_text 中提取公告类型、日期、公司、source_list_order
```

重要字段：

- `source_list_url`
- `source_list_order`
- `publish_date`
- `announcement_type`
- `company_name`
- `url`
- `title`

列表页中同一天的显示顺序由 `source_list_order` 保存。

## 详情页采集

模块：

```text
src/crawler/southern_grid_playwright.py
src/parser/southern_grid_parser.py
```

流程：

```text
打开详情页
保存 page.content() 为 raw_html
保存 body.inner_text() 为 raw_text
解析 title
解析 project_code
解析 publish_date
解析 buyer / agency
生成 url_hash / content_hash
```

## Blocks 和招标要求

模块：

```text
src/extractor/tender_sections.py
```

`extract_blocks()` 输出：

- `heading`
- `paragraph`
- `table_like_text`

`extract_requirements()` 从 blocks 中提取：

- 招标条件
- 投标人资格要求
- 招标文件获取
- 投标文件递交
- 开标时间
- 联系方式

这些写入：

```text
tender_requirements
```

## 数据库写入

模块：

```text
src/database/postgres.py
```

当前远端没有安装 psycopg，因此写库使用：

```bash
docker exec -i grid-tender-postgres psql -U grid_tender -d grid_tender
```

写入顺序：

```text
tender_sources
crawl_pages
tender_documents
document_blocks
tender_projects
tender_requirements
extraction_runs
```

同一个 source_url 再次采集会 upsert `tender_documents`，并重建对应的 blocks、requirements、projects、extraction_runs。

## 排序规则

不要依赖 PostgreSQL 表物理顺序。

采购公告展示使用：

```sql
ORDER BY publish_date DESC, source_list_order ASC, id DESC
```

对应视图：

```text
v_tender_purchase_notice_summary
```

## 常用 SQL

查看采购公告汇总：

```sql
select *
from v_tender_purchase_notice_summary;
```

查看招标要求：

```sql
select *
from v_tender_requirements_flat
order by document_id, requirement_order;
```

查看正文块：

```sql
select *
from v_document_blocks_flat
order by document_id, block_order;
```

查看 JSONB blocks：

```sql
select title, jsonb_array_length(document_json->'blocks') as block_count
from tender_documents;
```

## 当前已验证命令

清空并重建 schema：

```bash
docker exec -i grid-tender-postgres psql -U grid_tender -d grid_tender \
  < /home/untu/.openclaw/workspace/skills/grid_tender_intelligence_nanwang/src/database/postgres_schema.sql
```

采集 2026-05-29 的招标公告：

```bash
cd /home/untu/.openclaw/workspace/skills/grid_tender_intelligence_nanwang
PYTHONPATH=src python3 src/main.py \
  --list-url https://www.bidding.csg.cn/zbgg/index.jhtml \
  --since-date 2026-05-29 \
  --limit 10
```

当前这天已验证采集到两条：

```text
1200431105.jhtml
1200431104.jhtml
```

## 后续扩展

下一步可以扩展：

- `zbhxrgs/*.jhtml` 中标候选人公示，写入 `tender_candidates`
- 中标结果公告，写入 `tender_awards`
- 附件提取，写入 `tender_attachments`
- 标包表格解析，写入 `tender_packages`
- 将 `postgres.py` 从 `docker exec psql` 改成 `psycopg` 连接池

