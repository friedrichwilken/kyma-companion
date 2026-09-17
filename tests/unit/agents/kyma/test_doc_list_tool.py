"""Unit tests for DocListTool."""

from unittest.mock import Mock

import pytest

from agents.kyma.tools.doc_list import DocListTool
from docs.index import DocIndex
from docs.types import DocPage


def _page(module: str, path: str, title: str, doc_type: str = "") -> DocPage:
    return DocPage(
        title=title,
        url=f"https://example/{path}",
        repo=f"kyma-project/{module}",
        path=path,
        module=module,
        content="x",
        doc_type=doc_type,
    )


@pytest.fixture()
def tool() -> DocListTool:
    index = Mock(spec=DocIndex)
    pages = [_page("istio", "a.md", "A", "concept"), _page("istio", "b.md", "B"), _page("serverless", "c.md", "C")]
    index.list_module = Mock(side_effect=lambda module="": [p for p in pages if not module or p.module == module])
    return DocListTool(index)


@pytest.mark.asyncio
async def test_without_module_lists_modules_with_counts(tool: DocListTool) -> None:
    result = await tool._arun()
    assert "- istio: 2 pages" in result
    assert "- serverless: 1 pages" in result
    assert "a.md" not in result


@pytest.mark.asyncio
async def test_with_module_lists_its_pages(tool: DocListTool) -> None:
    result = await tool._arun("istio")
    assert "2 pages, module: istio" in result
    assert "[A](https://example/a.md) `kyma-project/istio::a.md` (concept)" in result
    assert "c.md" not in result


@pytest.mark.asyncio
async def test_unknown_module(tool: DocListTool) -> None:
    assert await tool._arun("nope") == "No pages found for module: nope."
