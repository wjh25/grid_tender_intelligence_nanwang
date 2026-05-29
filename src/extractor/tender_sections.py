"""公告章节抽取模块。"""

from __future__ import annotations

from html.parser import HTMLParser
import re


SECTION_RE = re.compile(
    r"(?m)^\s*(?P<section_no>(?:\d+|[一二三四五六七八九十]+)[.、．])\s*(?P<section_title>[^\n]{2,40})\s*$"
)

SUBSECTION_RE = re.compile(r"^\s*\d+[.、．]\s*\d+")

MAJOR_TITLE_KEYWORDS = [
    "招标条件",
    "项目概况",
    "招标范围",
    "投标人资格",
    "招标文件获取",
    "投标文件",
    "开标时间",
    "发布公告",
    "计算机硬件特征码",
    "现场核查",
    "异议及投诉",
    "联系方式",
    "公告的其他内容",
    "招标公告附件",
]


def extract_sections(text: str) -> list[dict[str, object]]:
    """按编号标题切分正文，保存章节顺序、编号、标题和内容。"""
    # 只保留南网公告的主章节标题，避免标包表格里的编号被误识别为章节。
    matches = [match for match in SECTION_RE.finditer(text) if _is_major_title(match.group("section_title"))]
    sections: list[dict[str, object]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append(
            {
                "section_order": index + 1,
                "section_no": match.group("section_no").strip(),
                "section_title": match.group("section_title").strip(),
                "section_content": text[start:end].strip(),
            }
        )
    return sections


def extract_blocks(text: str, html: str | None = None) -> list[dict[str, object]]:
    """把正文转换成网站易渲染的 block 列表。"""
    sections = extract_sections(text)
    html_tables = _extract_html_tables(html or "")
    blocks: list[dict[str, object]] = []
    order = 1
    if not sections:
        return [
            {
                "block_order": 1,
                "block_type": "paragraph",
                "heading_level": None,
                "section_no": None,
                "title": None,
                "text_content": text,
                "table_json": None,
                "block_json": {"type": "paragraph", "text": text},
            }
        ]

    for section in sections:
        blocks.append(
            {
                "block_order": order,
                "block_type": "heading",
                "heading_level": 1,
                "section_no": section.get("section_no"),
                "title": section.get("section_title"),
                "text_content": None,
                "table_json": None,
                "block_json": {
                    "type": "heading",
                    "level": 1,
                    "section_no": section.get("section_no"),
                    "text": section.get("section_title"),
                },
            }
        )
        order += 1
        content = str(section.get("section_content") or "").strip()
        if content:
            table_json = _match_html_table(content, html_tables)
            block_type = "table_like_text" if table_json else "paragraph"
            text_content = _remove_flat_table_lines(content) if table_json else content
            blocks.append(
                {
                    "block_order": order,
                    "block_type": block_type,
                    "heading_level": None,
                    "section_no": section.get("section_no"),
                    "title": section.get("section_title"),
                    "text_content": text_content,
                    "table_json": table_json,
                    "block_json": {
                        "type": block_type,
                        "section_title": section.get("section_title"),
                        "text": text_content,
                    },
                }
            )
            order += 1
    return blocks


def extract_requirements(blocks: list[dict[str, object]]) -> list[dict[str, object]]:
    """抽取招标要求类内容，方便业务表快速查询。"""
    requirement_keywords = [
        "招标条件",
        "投标人资格",
        "招标文件获取",
        "投标文件",
        "开标时间",
        "联系方式",
    ]
    requirements: list[dict[str, object]] = []
    current_heading: dict[str, object] | None = None
    for block in blocks:
        if block.get("block_type") == "heading":
            title = str(block.get("title") or "")
            current_heading = block if any(keyword in title for keyword in requirement_keywords) else None
            continue
        if current_heading and block.get("text_content"):
            requirements.append(
                {
                    "requirement_order": len(requirements) + 1,
                    "requirement_type": current_heading.get("title"),
                    "requirement_title": current_heading.get("title"),
                    "requirement_text": block.get("text_content"),
                    "raw_json": {
                        "heading": current_heading.get("block_json"),
                        "content": block.get("block_json"),
                    },
                }
            )
    return requirements


def _is_major_title(title: str) -> bool:
    if SUBSECTION_RE.match(title) or re.match(r"^\s*\d+", title):
        return False
    return any(keyword in title for keyword in MAJOR_TITLE_KEYWORDS)


def _match_html_table(content: str, tables: list[dict[str, object]]) -> dict[str, object] | None:
    for index, table in enumerate(tables):
        table_text = _table_plain_text(table)
        if _table_belongs_to_section(content, table_text):
            return tables.pop(index)
    return None


def _table_belongs_to_section(content: str, table_text: str) -> bool:
    if not table_text:
        return False
    normalized_content = _compact_text(content)
    normalized_table = _compact_text(table_text)
    if not normalized_table:
        return False
    return normalized_table[: min(len(normalized_table), 30)] in normalized_content


def _table_plain_text(table: dict[str, object]) -> str:
    parts: list[str] = []
    headers = table.get("headers")
    rows = table.get("rows")
    if isinstance(headers, list):
        parts.extend(str(item) for item in headers)
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, list):
                parts.extend(str(item) for item in row)
    return "\n".join(parts)


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _remove_flat_table_lines(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line == "序号":
            return "\n".join(lines[:index]).strip()
    return text


def _extract_html_tables(html: str) -> list[dict[str, object]]:
    if "<table" not in html.lower():
        return []
    parser = _TableParser()
    parser.feed(html)
    tables: list[dict[str, object]] = []
    for rows in parser.tables:
        clean_rows = [[cell for cell in row if cell] for row in rows]
        clean_rows = [row for row in clean_rows if row]
        if len(clean_rows) < 2:
            continue
        tables.append(
            {
                "format": "html_table",
                "headers": clean_rows[0],
                "rows": clean_rows[1:],
            }
        )
    return tables


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._current_rows: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._current_rows = []
        elif self._table_depth and tag == "tr":
            self._current_row = []
        elif self._table_depth and tag in {"td", "th"}:
            self._current_cell = []
        elif self._table_depth and tag == "br" and self._current_cell is not None:
            self._current_cell.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            text = _normalize_cell_text("".join(self._current_cell))
            self._current_row.append(text)
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None and self._current_rows is not None:
            if any(cell for cell in self._current_row):
                self._current_rows.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._table_depth:
            if self._table_depth == 1 and self._current_rows is not None:
                self.tables.append(self._current_rows)
                self._current_rows = None
            self._table_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._table_depth and self._current_cell is not None:
            self._current_cell.append(data)


def _normalize_cell_text(text: str) -> str:
    text = re.sub(r"[ \t\r\f\v\u00a0\u3000]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()
