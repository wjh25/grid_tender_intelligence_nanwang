"""南网公开页面 Playwright 采集模块。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import Page, sync_playwright


BASE_URL = "https://www.bidding.csg.cn"


@dataclass
class ListItem:
    title: str
    url: str
    row_text: str
    list_order: int | None = None
    list_url: str | None = None
    announcement_type: str | None = None
    company_name: str | None = None
    publish_date: str | None = None


@dataclass
class DetailPage:
    url: str
    title: str
    html: str
    text: str


def collect_list_items(list_url: str, limit: int = 10) -> list[ListItem]:
    """采集列表页中的公告链接。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _goto(page, list_url)
        anchors = page.locator("a[href*='.jhtml']").evaluate_all(
            """
            links => links.map(a => {
              const row = a.closest('li,tr,div') || a.parentElement;
              return {
                title: (a.innerText || a.textContent || '').trim(),
                href: a.href,
                rowText: row ? row.innerText.trim() : ''
              };
            })
            """
        )
        browser.close()

    seen: set[str] = set()
    items: list[ListItem] = []
    for anchor in anchors:
        url = anchor.get("href") or ""
        title = re.sub(r"\s+", " ", anchor.get("title") or "").strip()
        if not title or url.rstrip("/") == list_url.rstrip("/") or not _is_announcement_url(url) or url in seen:
            continue
        seen.add(url)
        row_text = re.sub(r"\s+", " ", anchor.get("rowText") or "").strip()
        items.append(
            ListItem(
                title=title,
                url=url,
                row_text=row_text,
                list_order=_guess_list_order(row_text),
                list_url=list_url,
                announcement_type=_guess_announcement_type(row_text),
                company_name=_guess_company(row_text),
                publish_date=_guess_date(row_text),
            )
        )
        if len(items) >= limit:
            break
    return items


def collect_list_items_since(list_url: str, since_date: str, limit: int = 20) -> list[ListItem]:
    """采集指定日期及之后的列表项。"""
    items = collect_list_items(list_url, limit=max(limit * 3, 30))
    selected = [item for item in items if item.publish_date and item.publish_date >= since_date]
    return selected[:limit]


def fetch_detail(detail_url: str) -> DetailPage:
    """采集详情页 HTML 与正文文本。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _goto(page, detail_url)
        html = page.content()
        text = page.locator("body").inner_text(timeout=15000)
        title = _first_text(page, ["h1", ".news-title", ".article-title", "title"]) or _guess_title_from_text(text)
        browser.close()
    return DetailPage(url=detail_url, title=title, html=html, text=text)


def _goto(page: Page, url: str) -> None:
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1000)


def _is_announcement_url(url: str) -> bool:
    return any(part in url for part in ["/zbgg/", "/gsgg/", "/zbgs/", "/cgxx/"]) and url.endswith(".jhtml")


def _first_text(page: Page, selectors: list[str]) -> str:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count():
                text = locator.inner_text(timeout=3000).strip()
                if text:
                    return re.sub(r"\s+", " ", text)
        except Exception:
            continue
    return ""


def _guess_title_from_text(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 8 and "公告" in line:
            return line
    return "未识别标题"


def _guess_announcement_type(text: str) -> str | None:
    for value in ["招标公告", "非招标公告", "公示公告", "中标公告", "结果公告", "澄清公告"]:
        if value in text:
            return value
    return None


def _guess_company(text: str) -> str | None:
    match = re.search(r"((?:广东|广西|云南|贵州|海南|深圳|广州|南方)电网(?:有限责任)?公司|超高压输电公司|调峰调频公司)", text)
    return match.group(1) if match else None


def _guess_date(text: str) -> str | None:
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    return match.group(1) if match else None


def _guess_list_order(text: str) -> int | None:
    match = re.search(r"\|\s*20\d{2}-\d{2}-\d{2}\s+(\d+)\s+", text)
    return int(match.group(1)) if match else None
