"""
bioRxiv source adapter: fetch recent preprints from bioRxiv via their API.
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


def fetch_biorxiv(
    categories: list[str] | None = None,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    """
    Fetch recent preprints from bioRxiv.
    bioRxiv doesn't have a direct category search in the same way as arXiv,
    so we fetch recent preprints and filter by category if specified.
    
    Returns list of {"title", "url", "summary"}.
    """
    # bioRxiv API endpoint for recent preprints
    base_url = "https://api.biorxiv.org/covid19/0"  # Using covid19 endpoint as example
    # For general preprints, use: https://api.biorxiv.org/details/biorxiv/yyyy-mm/dd/ntd_doi
    
    # Using the details endpoint to get recent preprints
    url = f"https://api.biorxiv.org/details/biorxiv/0/{max_results}"
    
    req = urllib.request.Request(url, headers={"User-Agent": "insight-mode/1.0"})
    kwargs = {"timeout": 30}
    if _SSL_CTX is not None:
        kwargs["context"] = _SSL_CTX
    
    with urllib.request.urlopen(req, **kwargs) as resp:
        body = resp.read().decode("utf-8")
    
    return _parse_biorxiv_json(body, categories)


def _parse_biorxiv_json(json_str: str, categories: list[str] | None = None) -> list[dict[str, Any]]:
    """Parse bioRxiv API JSON response."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return []
    
    collection = data.get("collection", [])
    results = []
    
    for item in collection:
        title = item.get("title", "").strip()
        # bioRxiv uses doi as the identifier
        doi = item.get("doi", "")
        url = f"https://www.biorxiv.org/content/{doi}" if doi else item.get("url", "")
        # bioRxiv has an abstract field
        summary = item.get("abstract", "").strip()[:5000]
        
        # Filter by category if specified (bioRxiv uses category field)
        item_category = item.get("category", "")
        if categories and item_category and item_category not in categories:
            continue
        
        if title and url:
            results.append({"title": title, "url": url, "summary": summary})
    
    return results
