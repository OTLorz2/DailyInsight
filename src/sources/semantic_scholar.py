"""
Semantic Scholar source adapter: fetch papers from Semantic Scholar API.
Returns list of dicts with title, url, summary for RawStore contract.

Requires SEMANTIC_SCHOLAR_API_KEY in environment variables (optional but recommended).
"""
import ssl
import urllib.request
import urllib.parse
import json
import os
from typing import Any

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = None


def fetch_semantic_scholar(
    categories: list[str] | None = None,
    max_results: int = 50,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch recent papers from Semantic Scholar.
    
    Args:
        categories: List of field of study names (e.g., ["Computer Science", "Machine Learning"])
        max_results: Maximum number of results to return
        query: Optional search query (default searches for recent AI/ML papers)
    
    Returns list of {"title", "url", "summary"}.
    """
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    
    # Default query for AI/ML papers if no query provided
    if not query:
        query = "machine learning OR artificial intelligence OR deep learning"
    
    # Build the API URL
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    params = {
        "query": query,
        "limit": min(max_results, 100),  # API max is 100
        "fields": "title,abstract,url,year,citationCount,fieldsOfStudy",
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    headers = {"User-Agent": "insight-mode/1.0"}
    if api_key:
        headers["x-api-key"] = api_key
    
    req = urllib.request.Request(url, headers=headers)
    kwargs = {"timeout": 30}
    if _SSL_CTX is not None:
        kwargs["context"] = _SSL_CTX
    
    with urllib.request.urlopen(req, **kwargs) as resp:
        body = resp.read().decode("utf-8")
    
    return _parse_semantic_scholar_json(body, categories)


def _parse_semantic_scholar_json(
    json_str: str, 
    categories: list[str] | None = None
) -> list[dict[str, Any]]:
    """Parse Semantic Scholar API JSON response."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return []
    
    papers = data.get("data", [])
    results = []
    
    for paper in papers:
        title = paper.get("title", "").strip()
        url = paper.get("url", "")
        
        # Use abstract as summary
        abstract = paper.get("abstract", "")
        summary = abstract.strip()[:5000] if abstract else ""
        
        # Filter by field of study if categories specified
        if categories:
            fields = paper.get("fieldsOfStudy", []) or []
            # Check if any category matches any field (case-insensitive)
            match = False
            for cat in categories:
                cat_lower = cat.lower()
                for field in fields:
                    if cat_lower in field.lower():
                        match = True
                        break
                if match:
                    break
            if not match:
                continue
        
        if title and url:
            results.append({"title": title, "url": url, "summary": summary})
    
    return results
