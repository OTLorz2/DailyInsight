"""
medRxiv source adapter: fetch recent preprints from medRxiv via their API.
Returns list of dicts with title, url, summary for RawStore contract.
"""
import ssl
import urllib.request
import urllib.parse
import json
from typing import Any

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = None


def fetch_medrxiv(
    categories: list[str] | None = None,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """
    Fetch recent preprints from medRxiv.
    
    Returns list of {"title", "url", "summary"}.
    """
    # medRxiv uses the same API structure as bioRxiv
    url = f"https://api.biorxiv.org/details/medrxiv/0/{max_results}"
    
    req = urllib.request.Request(url, headers={"User-Agent": "insight-mode/1.0"})
    kwargs = {"timeout": 30}
    if _SSL_CTX is not None:
        kwargs["context"] = _SSL_CTX
    
    with urllib.request.urlopen(req, **kwargs) as resp:
        body = resp.read().decode("utf-8")
    
    return _parse_medrxiv_json(body, categories)


def _parse_medrxiv_json(json_str: str, categories: list[str] | None = None) -> list[dict[str, Any]]:
    """Parse medRxiv API JSON response."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return []
    
    collection = data.get("collection", [])
    results = []
    
    for item in collection:
        title = item.get("title", "").strip()
        # medRxiv uses doi as the identifier
        doi = item.get("doi", "")
        url = f"https://www.medrxiv.org/content/{doi}" if doi else item.get("url", "")
        # medRxiv has an abstract field
        summary = item.get("abstract", "").strip()[:5000]
        
        # Filter by category if specified
        item_category = item.get("category", "")
        if categories and item_category and item_category not in categories:
            continue
        
        if title and url:
            results.append({"title": title, "url": url, "summary": summary})
    
    return results
