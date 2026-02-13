"""Verify arXiv adapter: parse response, write to RawStore, read back."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sources.arxiv import _parse_arxiv_xml, fetch_arxiv
from src.storage import RawStore

# Minimal arXiv API XML response (one entry)
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Test Paper on AI</title>
    <id>http://arxiv.org/abs/2401.00001</id>
    <summary>This is a test abstract for verification.</summary>
  </entry>
</feed>
"""


def test_parse_arxiv_xml():
    items = _parse_arxiv_xml(SAMPLE_XML)
    assert len(items) == 1
    assert items[0]["title"] == "Test Paper on AI"
    assert items[0]["url"] == "http://arxiv.org/abs/2401.00001"
    assert "test abstract" in items[0]["summary"]


def test_arxiv_to_raw_store():
    """Adapter output format fits RawStore; insert and read back."""
    items = _parse_arxiv_xml(SAMPLE_XML)
    path = os.path.join(os.path.dirname(__file__), "..", "data", "_test_arxiv.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        store = RawStore(path)
        for it in items:
            pk = store.insert(it["title"], it["url"], it["summary"], "arxiv")
            assert pk is not None
        row = store.get_by_id(1)
        assert row is not None
        assert row.title == items[0]["title"]
        assert row.url == items[0]["url"]
        assert row.source == "arxiv"
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


if __name__ == "__main__":
    test_parse_arxiv_xml()
    print("arXiv parse OK")
    test_arxiv_to_raw_store()
    print("arXiv -> RawStore OK")
