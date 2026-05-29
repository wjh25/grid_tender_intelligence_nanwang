from typing import Any

from app.db import cursor


def list_southern_grid_tenders(q: str | None, limit: int, offset: int) -> dict[str, Any]:
    filters = ["d.is_latest IS TRUE"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if q:
        filters.append(
            "("
            "d.title ILIKE %(q)s OR "
            "d.project_code ILIKE %(q)s OR "
            "d.project_name ILIKE %(q)s OR "
            "d.buyer ILIKE %(q)s OR "
            "d.company_name ILIKE %(q)s"
            ")"
        )
        params["q"] = f"%{q}%"

    where_sql = " AND ".join(filters)
    count_sql = f"SELECT count(*) AS total FROM tender_documents d WHERE {where_sql}"
    list_sql = f"""
        SELECT
          d.id,
          d.title,
          d.announcement_type,
          d.purchase_category,
          d.company_name,
          d.publish_date,
          d.source_list_order,
          d.project_code,
          d.project_name,
          d.buyer,
          d.agency,
          d.source_url,
          d.last_seen_at,
          count(DISTINCT r.id) AS requirement_count,
          count(DISTINCT b.id) AS block_count
        FROM tender_documents d
        LEFT JOIN tender_requirements r ON r.document_id = d.id
        LEFT JOIN document_blocks b ON b.document_id = d.id
        WHERE {where_sql}
        GROUP BY d.id
        ORDER BY d.publish_date DESC NULLS LAST, d.source_list_order ASC NULLS LAST, d.id DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """
    with cursor() as cur:
        cur.execute(count_sql, params)
        total = cur.fetchone()["total"]
        cur.execute(list_sql, params)
        items = cur.fetchall()
    return {"total": total, "items": items, "limit": limit, "offset": offset}


def get_southern_grid_tender(document_id: int) -> dict[str, Any] | None:
    sql = """
        SELECT
          id,
          title,
          announcement_type,
          purchase_category,
          company_name,
          publish_date,
          source_list_url,
          source_list_order,
          project_code,
          project_name,
          buyer,
          agency,
          source_url,
          document_json,
          raw_text,
          last_seen_at
        FROM tender_documents
        WHERE id = %(document_id)s AND is_latest IS TRUE
    """
    with cursor() as cur:
        cur.execute(sql, {"document_id": document_id})
        return cur.fetchone()


def get_document_blocks(document_id: int) -> list[dict[str, Any]]:
    sql = """
        SELECT
          id,
          block_order,
          block_type,
          heading_level,
          section_no,
          title,
          text_content,
          table_json,
          block_json
        FROM document_blocks
        WHERE document_id = %(document_id)s
        ORDER BY block_order ASC
    """
    with cursor() as cur:
        cur.execute(sql, {"document_id": document_id})
        return cur.fetchall()


def get_tender_requirements(document_id: int) -> list[dict[str, Any]]:
    sql = """
        SELECT
          id,
          requirement_order,
          requirement_type,
          requirement_title,
          requirement_text,
          raw_json
        FROM tender_requirements
        WHERE document_id = %(document_id)s
        ORDER BY requirement_order ASC
    """
    with cursor() as cur:
        cur.execute(sql, {"document_id": document_id})
        return cur.fetchall()


def get_tender_packages(document_id: int) -> list[dict[str, Any]]:
    sql = """
        SELECT
          id,
          package_no,
          package_name,
          package_description,
          estimated_amount,
          amount_unit,
          equipment_type,
          service_type,
          raw_row
        FROM tender_packages
        WHERE document_id = %(document_id)s
        ORDER BY id ASC
    """
    with cursor() as cur:
        cur.execute(sql, {"document_id": document_id})
        return cur.fetchall()
