"""Unit tests for DocSearchTool (SearchKymaDocTool alias) backed by DocIndex."""

from unittest.mock import Mock

import pytest

from agents.kyma.tools.search import DocSearchTool, SearchKymaDocTool
from docs.index import DocIndex
from docs.types import DocPage

_TWO_PAGE_COUNT = 2


def _make_page(
    title: str = "Test Page",
    url: str = "https://kyma.io/test",
    module: str = "test-module",
    content: str = "Test content.",
    repo: str = "kyma-project/kyma",
    path: str = "docs/test.md",
) -> DocPage:
    """Helper to build a DocPage for tests."""
    return DocPage(title=title, url=url, repo=repo, path=path, module=module, content=content)


def _make_tool(pages: list[DocPage]) -> DocSearchTool:
    """Create a DocSearchTool with a mocked DocIndex returning the given pages."""
    mock_index = Mock(spec=DocIndex)
    mock_index.search.return_value = pages
    return DocSearchTool(mock_index)


class TestDocSearchToolModuleScope:
    """The module argument is passed through to the index."""

    @pytest.mark.asyncio
    async def test_arun_passes_module_to_index(self) -> None:
        tool = _make_tool([_make_page(content="Body.")])
        await tool._arun("sidecar injection", module="istio")
        tool.index.search.assert_called_once_with("sidecar injection", top_k=5, module="istio")

    @pytest.mark.asyncio
    async def test_arun_documents_passes_module_to_index(self) -> None:
        tool = _make_tool([_make_page(content="Body.")])
        await tool.arun_documents("sinks", top_k=3, module="eventing-manager")
        tool.index.search.assert_called_once_with("sinks", top_k=3, module="eventing-manager")


class TestDocSearchToolFormatting:
    """Formatting of navigation metadata."""

    @pytest.mark.asyncio
    async def test_arun_includes_doc_type_when_present(self) -> None:
        page = _make_page(title="Connection Refused Errors", content="Fix it.")
        page.doc_type = "troubleshooting"
        tool = _make_tool([page])
        result = await tool._arun("connection refused")
        assert "Type: troubleshooting" in result

    @pytest.mark.asyncio
    async def test_arun_omits_type_line_when_doc_type_empty(self) -> None:
        tool = _make_tool([_make_page(content="Body.")])
        result = await tool._arun("query")
        assert "Type:" not in result


class TestDocSearchToolAlias:
    """Verify that SearchKymaDocTool is an alias for DocSearchTool."""

    def test_alias_is_same_class(self) -> None:
        assert SearchKymaDocTool is DocSearchTool


class TestDocSearchToolArun:
    """Tests for DocSearchTool._arun output format."""

    @pytest.mark.asyncio
    async def test_arun_returns_no_relevant_when_empty(self) -> None:
        """_arun returns the not-found message when the index returns no pages."""
        tool = _make_tool([])
        result = await tool._arun("some query")
        assert result == "No relevant documentation found."

    @pytest.mark.asyncio
    async def test_arun_formats_single_page_with_title_url_module_content(self) -> None:
        """_arun formats a page with title, Source, Module, and content."""
        page = _make_page(
            title="Kyma Functions",
            url="https://kyma.io/docs/functions",
            module="serverless",
            content="Functions are short-lived.",
        )
        tool = _make_tool([page])
        result = await tool._arun("functions")

        assert result.startswith("### Kyma Functions")
        assert "Source: https://kyma.io/docs/functions" in result
        assert "Module: serverless" in result
        assert "ID: kyma-project/kyma::docs/test.md" in result
        assert "Functions are short-lived." in result

    @pytest.mark.asyncio
    async def test_arun_formats_multiple_pages_separated_by_hr(self) -> None:
        """_arun joins multiple pages with '---' horizontal rules."""
        pages = [
            _make_page(title="First", url="https://kyma.io/first", content="First content."),
            _make_page(title="Second", url="https://kyma.io/second", content="Second content."),
        ]
        tool = _make_tool(pages)
        result = await tool._arun("query")

        assert "### First" in result
        assert "### Second" in result
        assert "---" in result

    @pytest.mark.asyncio
    async def test_arun_omits_source_line_when_url_empty(self) -> None:
        """_arun skips the Source line when url is an empty string."""
        page = _make_page(url="", title="No URL Doc", content="Content without url.")
        tool = _make_tool([page])
        result = await tool._arun("query")

        assert "### No URL Doc" in result
        assert "Source:" not in result
        assert "Content without url." in result

    @pytest.mark.asyncio
    async def test_arun_omits_module_line_when_module_empty(self) -> None:
        """_arun skips the Module line when module is an empty string."""
        page = _make_page(module="", title="No Module Doc", content="Content.")
        tool = _make_tool([page])
        result = await tool._arun("query")

        assert "Module:" not in result


class TestDocSearchToolArunDocuments:
    """Tests for DocSearchTool.arun_documents."""

    @pytest.mark.asyncio
    async def test_arun_documents_returns_list_of_doc_pages(self) -> None:
        """arun_documents returns the raw DocPage list from the index."""
        pages = [
            _make_page(title="A", content="Alpha."),
            _make_page(title="B", content="Beta."),
        ]
        tool = _make_tool(pages)
        result = await tool.arun_documents("query")

        assert isinstance(result, list)
        assert len(result) == _TWO_PAGE_COUNT
        assert all(isinstance(p, DocPage) for p in result)
        assert result[0].title == "A"
        assert result[1].title == "B"

    @pytest.mark.asyncio
    async def test_arun_documents_returns_empty_list_when_no_results(self) -> None:
        """arun_documents returns an empty list when the index has no matches."""
        tool = _make_tool([])
        result = await tool.arun_documents("query")
        assert result == []


class TestDocSearchToolArunList:
    """Tests for DocSearchTool.arun_list (backward-compat)."""

    @pytest.mark.asyncio
    async def test_arun_list_returns_content_strings(self) -> None:
        """arun_list returns plain content strings for each matched page."""
        pages = [
            _make_page(title="A", content="Doc A content."),
            _make_page(title="B", content="Doc B content."),
        ]
        tool = _make_tool(pages)
        result = await tool.arun_list("query")

        assert result == ["Doc A content.", "Doc B content."]

    @pytest.mark.asyncio
    async def test_arun_list_returns_empty_list_when_no_results(self) -> None:
        """arun_list returns an empty list when no pages are found."""
        tool = _make_tool([])
        result = await tool.arun_list("query")
        assert result == []
