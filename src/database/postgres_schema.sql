-- 南网招投标 PostgreSQL + JSONB 混合 schema。
-- 页面原貌和复杂结构放 JSONB，项目/标包/候选人等高频查询对象放关系表。

DROP TABLE IF EXISTS tender_awards CASCADE;
DROP TABLE IF EXISTS tender_candidates CASCADE;
DROP TABLE IF EXISTS tender_attachments CASCADE;
DROP TABLE IF EXISTS tender_packages CASCADE;
DROP TABLE IF EXISTS tender_requirements CASCADE;
DROP TABLE IF EXISTS tender_projects CASCADE;
DROP TABLE IF EXISTS document_blocks CASCADE;
DROP TABLE IF EXISTS tender_documents CASCADE;
DROP TABLE IF EXISTS crawl_pages CASCADE;
DROP TABLE IF EXISTS extraction_runs CASCADE;
DROP TABLE IF EXISTS tender_announcement_sections CASCADE;
DROP TABLE IF EXISTS tender_announcements CASCADE;
DROP TABLE IF EXISTS crawl_jobs CASCADE;
DROP TABLE IF EXISTS tender_sources CASCADE;

CREATE TABLE tender_sources (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  source_type TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (name, base_url)
);

CREATE TABLE crawl_pages (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT REFERENCES tender_sources(id),
  url TEXT NOT NULL,
  url_hash TEXT NOT NULL,
  fetched_at TIMESTAMPTZ DEFAULT now(),
  http_status INT,
  raw_html TEXT,
  raw_text TEXT,
  content_hash TEXT,
  UNIQUE (url)
);

CREATE TABLE tender_documents (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT REFERENCES tender_sources(id),
  crawl_page_id BIGINT REFERENCES crawl_pages(id) ON DELETE SET NULL,
  source_url TEXT NOT NULL,
  url_hash TEXT NOT NULL,
  title TEXT NOT NULL,
  announcement_type TEXT,
  purchase_category TEXT,
  company_name TEXT,
  publish_date DATE,
  source_list_url TEXT,
  source_list_order INT,
  project_name TEXT,
  project_code TEXT,
  buyer TEXT,
  agency TEXT,
  document_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  raw_text TEXT,
  content_hash TEXT,
  first_seen_at TIMESTAMPTZ DEFAULT now(),
  last_seen_at TIMESTAMPTZ DEFAULT now(),
  is_latest BOOLEAN DEFAULT true,
  UNIQUE (source_url)
);

CREATE TABLE document_blocks (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT REFERENCES tender_documents(id) ON DELETE CASCADE,
  block_order INT NOT NULL,
  block_type TEXT NOT NULL,
  heading_level INT,
  section_no TEXT,
  title TEXT,
  text_content TEXT,
  table_json JSONB,
  block_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (document_id, block_order)
);

CREATE TABLE tender_projects (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT REFERENCES tender_documents(id) ON DELETE CASCADE,
  project_code TEXT,
  project_name TEXT,
  buyer TEXT,
  agency TEXT,
  company_name TEXT,
  publish_date DATE,
  raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (document_id, project_code, project_name)
);

CREATE TABLE tender_requirements (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT REFERENCES tender_documents(id) ON DELETE CASCADE,
  requirement_order INT NOT NULL,
  requirement_type TEXT,
  requirement_title TEXT,
  requirement_text TEXT,
  raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (document_id, requirement_order)
);

CREATE TABLE tender_packages (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT REFERENCES tender_documents(id) ON DELETE CASCADE,
  project_id BIGINT REFERENCES tender_projects(id) ON DELETE SET NULL,
  package_no TEXT,
  package_name TEXT,
  package_description TEXT,
  estimated_amount NUMERIC(18, 2),
  amount_unit TEXT,
  equipment_type TEXT,
  service_type TEXT,
  raw_row JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (document_id, package_no, package_name)
);

CREATE TABLE tender_candidates (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT REFERENCES tender_documents(id) ON DELETE CASCADE,
  package_id BIGINT REFERENCES tender_packages(id) ON DELETE SET NULL,
  project_code TEXT,
  package_no TEXT,
  package_name TEXT,
  supplier_name TEXT,
  candidate_rank INT,
  bid_amount NUMERIC(18, 2),
  amount_unit TEXT,
  quality TEXT,
  delivery_time TEXT,
  qualification TEXT,
  evaluation_status TEXT,
  raw_row JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE tender_awards (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT REFERENCES tender_documents(id) ON DELETE CASCADE,
  package_id BIGINT REFERENCES tender_packages(id) ON DELETE SET NULL,
  winner_name TEXT,
  bid_amount NUMERIC(18, 2),
  amount_unit TEXT,
  award_date DATE,
  raw_row JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE tender_attachments (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT REFERENCES tender_documents(id) ON DELETE CASCADE,
  file_name TEXT,
  file_url TEXT,
  local_path TEXT,
  file_type TEXT,
  file_hash TEXT,
  raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  downloaded_at TIMESTAMPTZ,
  UNIQUE (document_id, file_url)
);

CREATE TABLE extraction_runs (
  id BIGSERIAL PRIMARY KEY,
  document_id BIGINT REFERENCES tender_documents(id) ON DELETE CASCADE,
  extractor_version TEXT,
  status TEXT NOT NULL DEFAULT 'success',
  message TEXT,
  extracted_at TIMESTAMPTZ DEFAULT now(),
  result_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_tender_documents_publish_date
ON tender_documents (publish_date DESC);

CREATE INDEX idx_tender_documents_company
ON tender_documents (company_name);

CREATE INDEX idx_tender_documents_type
ON tender_documents (announcement_type);

CREATE INDEX idx_tender_documents_project_code
ON tender_documents (project_code);

CREATE INDEX idx_document_blocks_document_order
ON document_blocks (document_id, block_order);

CREATE INDEX idx_document_blocks_type
ON document_blocks (block_type);

CREATE INDEX idx_tender_packages_equipment
ON tender_packages (equipment_type);

CREATE INDEX idx_tender_requirements_type
ON tender_requirements (requirement_type);

CREATE INDEX idx_tender_candidates_supplier
ON tender_candidates (supplier_name);

CREATE INDEX idx_tender_documents_json
ON tender_documents USING GIN (document_json);

CREATE INDEX idx_document_blocks_json
ON document_blocks USING GIN (block_json);

CREATE INDEX idx_tender_documents_text_search
ON tender_documents
USING GIN (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(raw_text, '')));

CREATE OR REPLACE VIEW v_tender_document_summary AS
SELECT
  d.id,
  d.title,
  d.announcement_type,
  d.purchase_category,
  d.company_name,
  d.publish_date,
  d.source_list_url,
  d.source_list_order,
  d.project_code,
  d.project_name,
  d.buyer,
  d.source_url,
  count(b.id) AS block_count,
  d.last_seen_at
FROM tender_documents d
LEFT JOIN document_blocks b ON b.document_id = d.id
GROUP BY d.id;

CREATE OR REPLACE VIEW v_tender_purchase_notice_summary AS
SELECT
  d.id,
  d.publish_date,
  d.source_list_order,
  d.title,
  d.project_code,
  d.company_name,
  d.announcement_type,
  d.source_url,
  count(r.id) AS requirement_count,
  d.last_seen_at
FROM tender_documents d
LEFT JOIN tender_requirements r ON r.document_id = d.id
WHERE d.announcement_type = '招标公告'
GROUP BY d.id
ORDER BY d.publish_date DESC NULLS LAST, d.source_list_order ASC NULLS LAST, d.id DESC;

CREATE OR REPLACE VIEW v_tender_requirements_flat AS
SELECT
  d.id AS document_id,
  d.title AS document_title,
  d.project_code,
  d.publish_date,
  r.requirement_order,
  r.requirement_type,
  r.requirement_title,
  r.requirement_text
FROM tender_documents d
JOIN tender_requirements r ON r.document_id = d.id
ORDER BY d.publish_date DESC NULLS LAST, d.source_list_order ASC NULLS LAST, r.requirement_order;

CREATE OR REPLACE VIEW v_document_blocks_flat AS
SELECT
  d.id AS document_id,
  d.title AS document_title,
  d.project_code,
  b.block_order,
  b.block_type,
  b.section_no,
  b.title AS block_title,
  b.text_content,
  b.table_json
FROM tender_documents d
JOIN document_blocks b ON b.document_id = d.id
ORDER BY d.id, b.block_order;
