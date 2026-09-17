from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from agents.kyma.react_agent import _tool_summarizer
from agents.kyma.tools.search import DocSearchTool, SearchKymaDocTool
from docs.index import DocIndex
from docs.types import DocPage
from utils.settings import TOTAL_CHUNKS_LIMIT


def _make_page(
    title: str = "Untitled",
    url: str = "",
    module: str = "",
    content: str = "",
) -> DocPage:
    """Build a minimal DocPage for testing."""
    return DocPage(title=title, url=url, repo="repo", path="path.md", module=module, content=content)


def _make_tool(pages: list[DocPage]) -> DocSearchTool:
    """Create a DocSearchTool backed by a mocked DocIndex returning *pages*."""
    mock_index = Mock(spec=DocIndex)
    kept = [p for p in pages if p.content.strip()]
    mock_index.search = Mock(return_value=kept)
    mock_index.search_with_sections = Mock(return_value=[(p, "") for p in kept])
    return DocSearchTool(mock_index)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "pages,expected_output",
    [
        # Single document case
        ([_make_page(content="Single document content")], "### Untitled\nID: repo::path.md\n\nSingle document content"),
        # Multiple documents case
        (
            [_make_page(content="First doc"), _make_page(content="Second doc")],
            "### Untitled\nID: repo::path.md\n\nFirst doc\n\n---\n\n### Untitled\nID: repo::path.md\n\nSecond doc",
        ),
        # Three documents case
        (
            [_make_page(content="Doc 1"), _make_page(content="Doc 2"), _make_page(content="Doc 3")],
            "### Untitled\nID: repo::path.md\n\nDoc 1\n\n---\n\n"
            "### Untitled\nID: repo::path.md\n\nDoc 2\n\n---\n\n"
            "### Untitled\nID: repo::path.md\n\nDoc 3",
        ),
        # Empty list - should return fallback message
        ([], "No relevant documentation found."),
        # Documents with empty content - filtered by the tool
        ([_make_page(content="")], "No relevant documentation found."),
        # Mixed content with special characters
        (
            [
                _make_page(content="Content with special chars: !@#$"),
                _make_page(content="Unicode: αβγ"),
            ],
            "### Untitled\nID: repo::path.md\n\nContent with special chars: !@#$\n\n---\n\n"
            "### Untitled\nID: repo::path.md\n\nUnicode: αβγ",
        ),
        # Documents with newlines
        (
            [_make_page(content="Multi\nline\ncontent"), _make_page(content="Another\ndocument")],
            "### Untitled\nID: repo::path.md\n\nMulti\nline\ncontent\n\n---\n\n"
            "### Untitled\nID: repo::path.md\n\nAnother\ndocument",
        ),
    ],
)
async def test_arun(pages: list[DocPage], expected_output: str) -> None:
    """Test _arun formats DocPage results into the expected Markdown string."""
    tool = _make_tool(pages)
    result = await tool._arun("test query")
    assert result == expected_output


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "pages,expected_output",
    [
        # Single document
        ([_make_page(content="Single document content")], ["Single document content"]),
        # Multiple documents
        (
            [_make_page(content="First doc"), _make_page(content="Second doc")],
            ["First doc", "Second doc"],
        ),
        # Empty list
        ([], []),
        # Empty content filtered by the mock
        ([_make_page(content="")], []),
        # Mixed: some empty, some valid
        (
            [_make_page(content="Valid content"), _make_page(content=""), _make_page(content="Another valid")],
            ["Valid content", "Another valid"],
        ),
    ],
)
async def test_arun_list(pages: list[DocPage], expected_output: list[str]) -> None:
    """Test arun_list returns the content strings from the matched pages."""
    tool = _make_tool(pages)
    result = await tool.arun_list("test query")
    assert result == expected_output


def test_search_kyma_doc_tool_is_alias() -> None:
    """SearchKymaDocTool is an alias for DocSearchTool."""
    assert SearchKymaDocTool is DocSearchTool


# ---------------------------------------------------------------------------
# _tool_summarizer
# ---------------------------------------------------------------------------


class TestToolSummarizer:
    """Tests for _maybe_summarize."""

    @pytest.mark.asyncio
    async def test_short_response_returned_unchanged(self) -> None:
        """When the response is within the token limit, summarizer is not called."""

        summarizer = MagicMock()
        summarizer.summarize_tool_response = AsyncMock(return_value="summary")

        text = "short response"
        result = await _tool_summarizer(
            response=[text], text=text, query="q", summarizer=summarizer, config=None, token_limit=10_000
        )

        assert result == text
        summarizer.summarize_tool_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_long_response_triggers_summarizer(self) -> None:
        """When the response exceeds the token limit, summarizer.summarize_tool_response is called."""

        summarizer = MagicMock()
        summarizer.summarize_tool_response = AsyncMock(return_value="summarized")

        # ~200 tokens; token_limit=150 → num_chunks=(200//150)+1=2 which is within TOTAL_CHUNKS_LIMIT
        text = " ".join(["word"] * 200)
        result = await _tool_summarizer(
            response=[text], text=text, query="list pods", summarizer=summarizer, config=None, token_limit=150
        )

        assert result == "summarized"
        summarizer.summarize_tool_response.assert_awaited_once()
        call_kwargs = summarizer.summarize_tool_response.call_args[1]
        assert call_kwargs["user_query"] == "list pods"
        assert call_kwargs["nums_of_chunks"] == TOTAL_CHUNKS_LIMIT

    @pytest.mark.asyncio
    async def test_summarizer_failure_falls_back_to_original_text(self) -> None:
        """If summarizer raises a generic error, the original text is returned instead of propagating."""

        summarizer = MagicMock()
        summarizer.summarize_tool_response = AsyncMock(side_effect=RuntimeError("llm error"))

        # ~200 tokens; token_limit=150 → num_chunks=2, within TOTAL_CHUNKS_LIMIT
        text = " ".join(["word"] * 200)
        result = await _tool_summarizer(
            response=[text], text=text, query="q", summarizer=summarizer, config=None, token_limit=150
        )

        assert result == text

    @pytest.mark.asyncio
    async def test_chunks_limit_exceeded_returns_message(self) -> None:
        """If num_chunks exceeds TOTAL_CHUNKS_LIMIT, CHUNK_LIMIT_EXCEEDED_RESPONSE is returned."""
        from agents.kyma.react_agent import CHUNK_LIMIT_EXCEEDED_RESPONSE

        summarizer = MagicMock()
        summarizer.summarize_tool_response = AsyncMock(return_value="summarized")

        # ~200 tokens with token_limit=5 → num_chunks=41, far exceeds TOTAL_CHUNKS_LIMIT=2
        text = " ".join(["word"] * 200)
        result = await _tool_summarizer(
            response=[text], text=text, query="q", summarizer=summarizer, config=None, token_limit=5
        )
        assert result == CHUNK_LIMIT_EXCEEDED_RESPONSE
