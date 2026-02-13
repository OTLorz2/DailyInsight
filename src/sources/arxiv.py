"""
arXiv source adapter: fetch recent papers from cs.AI, cs.LG, cs.CL via API.
Returns list of dicts with title, url, summary for RawStore contract.
"""
import ssl
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = None

# arXiv API namespace (Atom default ns; use Clark notation for reliable match)
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
ATOM_URI = "http://www.w3.org/2005/Atom"
ARXIV_NS = {"arxiv": "http://arxiv.org/schemas/atom"}


def fetch_arxiv(
    categories: list[str] | None = None,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """
    Fetch recent papers from arXiv. Categories default to cs.AI, cs.LG, cs.CL.
    Returns list of {"title", "url", "summary"}.
    """
    if categories is None:
        categories = ["cs.AI", "cs.LG", "cs.CL"]
    # Use " OR " with spaces so urlencode encodes spaces as +; API expects spaces around OR (parentheses per arXiv manual).
    query = "(" + " OR ".join(f"cat:{c}" for c in categories) + ")"
    url = (
        "http://export.arxiv.org/api/query?"
        + urllib.parse.urlencode({
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": str(max_results),
        })
    )
    req = urllib.request.Request(url, headers={"User-Agent": "insight-mode/1.0"})
    kwargs = {"timeout": 30}
    if _SSL_CTX is not None:
        kwargs["context"] = _SSL_CTX
    with urllib.request.urlopen(req, **kwargs) as resp:
        body = resp.read().decode("utf-8")
    return _parse_arxiv_xml(body)


def _parse_arxiv_xml(xml_str: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_str)
    # Use Clark notation so default-namespace entries are found regardless of prefix
    entries = root.findall(f".//{{{ATOM_URI}}}entry")
    results = []
    for entry in entries:
        title_el = entry.find(f"{{{ATOM_URI}}}title")
        title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""
        link_el = entry.find(f"{{{ATOM_URI}}}id")
        url = (link_el.text or "").strip() if link_el is not None else ""
        summary_el = entry.find(f"{{{ATOM_URI}}}summary")
        summary = (summary_el.text or "").strip().replace("\n", " ")[:5000] if summary_el is not None else ""
        if title and url:
            results.append({"title": title, "url": url, "summary": summary})
    return results
