"""Verify Analyzer: read RawStore, produce insights, write InsightStore."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch
from src.storage import RawStore, InsightStore
from src.analyzer import _parse_llm_response, run_analyze


def test_parse_llm_response():
    s = '{"opportunities": ["A"], "directions": ["B"], "innovations": ["C"]}'
    out = _parse_llm_response(s)
    assert out["opportunities"] == ["A"] and out["directions"] == ["B"] and out["innovations"] == ["C"]
    s2 = "```json\n" + s + "\n```"
    assert _parse_llm_response(s2) == out


@patch("src.analyzer.OpenAI")
def test_run_analyze_mock(MockOpenAI):
    path = os.path.join(os.path.dirname(__file__), "..", "data", "_test_analyzer.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        raw_store = RawStore(path)
        insight_store = InsightStore(path)
        raw_store.insert("Test Paper", "http://arxiv.org/abs/2401.0", "Abstract here", "arxiv")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"opportunities":["o1"],"directions":["d1"],"innovations":["i1"]}'))]
        )
        MockOpenAI.return_value = mock_client
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            n = run_analyze(raw_store, insight_store, max_items_per_run=5)
        assert n == 1
        insights = insight_store.list_since(limit=10)
        assert len(insights) == 1 and insights[0].opportunities == ["o1"]
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


if __name__ == "__main__":
    test_parse_llm_response()
    print("Parse OK")
    test_run_analyze_mock()
    print("Analyzer run OK")
