"""南网页面解析模块。"""

from __future__ import annotations

import hashlib
import re


def clean_text(text: str) -> str:
    """清洗正文空白，保留换行以便章节切分。"""
    lines = [re.sub(r"[ \t\u00a0\u3000]+", " ", line).strip() for line in text.splitlines()]
    return _trim_navigation_tail("\n".join(line for line in lines if line))


def _trim_navigation_tail(text: str) -> str:
    markers = ["上一篇：", "下一篇：", "上一篇:", "下一篇:", "返回列表"]
    positions = [text.find(marker) for marker in markers if marker in text]
    if not positions:
        return text
    return text[: min(positions)].strip()


def parse_detail_text(title: str, url: str, html: str, text: str) -> dict[str, object]:
    """从南网详情正文中抽取公告级字段。"""
    clean = clean_text(text)
    data: dict[str, object] = {
        "source_url": url,
        "url_hash": hashlib.sha256(url.encode("utf-8")).hexdigest(),
        "title": title.strip() or _first_title(clean),
        "announcement_type": _guess_announcement_type(title + "\n" + clean),
        "purchase_category": _guess_purchase_category(title + "\n" + clean),
        "company_name": _guess_company(clean),
        "publish_date": _guess_publish_date(clean),
        "project_name": _guess_project_name(title, clean),
        "project_code": _guess_project_code(clean),
        "buyer": _guess_buyer(clean),
        "agency": _guess_agency(clean),
        "raw_html": html,
        "raw_text": clean,
        "content_hash": hashlib.sha256(clean.encode("utf-8")).hexdigest(),
    }
    return data


def _first_title(text: str) -> str:
    for line in text.splitlines():
        if "公告" in line and len(line) > 8:
            return line
    return "未识别标题"


def _guess_announcement_type(text: str) -> str | None:
    for value in ["招标公告", "非招标公告", "公示公告", "中标公告", "结果公告", "澄清公告"]:
        if value in text:
            return value
    return None


def _guess_purchase_category(text: str) -> str | None:
    for value in ["货物", "工程", "服务"]:
        if value in text:
            return value
    return None


def _guess_company(text: str) -> str | None:
    buyer = _guess_buyer(text)
    if buyer:
        return buyer

    patterns = [
        r"((?:广东|广西|云南|贵州|海南|深圳|广州|南方)电网(?:有限责任)?公司)",
        r"((?:超高压输电公司|调峰调频公司))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _clean_party_name(match.group(1))
    return None


def _guess_publish_date(text: str) -> str | None:
    match = re.search(r"(20\d{2}[-年]\d{1,2}[-月]\d{1,2})", text)
    if not match:
        return None
    return match.group(1).replace("年", "-").replace("月", "-").replace("日", "")


def _guess_project_name(title: str, text: str) -> str:
    match = re.search(r"(?:项目名称|采购项目名称)[:：]\s*([^\n]+)", text)
    return match.group(1).strip() if match else title.strip()


def _guess_project_code(text: str) -> str | None:
    match = re.search(r"(?:招标编号|采购编号|项目编号)[:：]\s*([A-Za-z0-9_\-./]+)", text)
    return match.group(1).strip() if match else None


def _guess_buyer(text: str) -> str | None:
    patterns = [
        r"(?:招\s*标\s*人|采\s*购\s*人)[:：]\s*([^\n]+)",
        r"(?:招\s*标\s*人|采\s*购\s*人)为([^，。\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _clean_party_name(match.group(1))
    return None


def _guess_agency(text: str) -> str | None:
    match = re.search(r"(?:招\s*标\s*代理机构|采\s*购\s*代理机构)[:：]\s*([^\n]+)", text)
    return _clean_party_name(match.group(1)) if match else None


def _clean_party_name(value: str) -> str:
    value = re.sub(r"[ \t\u00a0\u3000]+", " ", value).strip()
    value = re.split(r"[，。,；;]", value, maxsplit=1)[0].strip()
    return value
