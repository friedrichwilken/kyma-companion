"""BM25-backed tool for searching Kyma documentation."""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from docs.index import DocIndex
from docs.types import DocPage
from utils.logging import get_logger

DEFAULT_TOP_K: int = 5
SEARCH_KYMA_DOC_TOOL_NAME: str = "search_kyma_doc"

logger = get_logger(__name__)


class DocSearchArgs(BaseModel):
    """Arguments for the search_kyma_doc tool."""

    query: str = Field(
        description="Search query to find relevant Kyma documentation",
        examples=["Help me get started with kyma", "What are Kyma components?"],
    )


def page_id(page: DocPage) -> str:
    """Return the identifier under which ``DocIndex.read`` finds *page*.

    Args:
        page: The page to identify.

    Returns:
        The ``<repo>::<path>`` identifier.
    """
    return f"{page.repo}::{page.path}"


def _format_page(page: DocPage) -> str:
    """Format a single DocPage into a human-readable block with title, source URL, module, ID, and content.

    Args:
        page: A DocPage with title, url, module, and content fields.

    Returns:
        Formatted string block for the page.
    """
    lines = [f"### {page.title}"]
    if page.url:
        lines.append(f"Source: {page.url}")
    if page.module:
        lines.append(f"Module: {page.module}")
    lines.append(f"ID: {page_id(page)}")
    lines.append("")
    lines.append(page.content)
    return "\n".join(lines)


class DocSearchTool(BaseTool):
    """Tool to search through Kyma documentation using the in-process BM25 index."""

    name: str = SEARCH_KYMA_DOC_TOOL_NAME
    description: str = """Used to search through Kyma documentation for relevant information about Kyma concepts,
    features, components, resources, or troubleshooting. A query is required to search the documentation.

    Example queries:
    - "How do I install Kyma?"
    - "What are the main Kyma components?"
    - "How to troubleshoot Kyma Istio module?"
    """

    args_schema: type[BaseModel] = DocSearchArgs
    return_direct: bool = False  # Let the agent process the search results

    _index: DocIndex = PrivateAttr()

    def __init__(self, index: DocIndex) -> None:
        """Initialize the tool with a pre-loaded DocIndex.

        Args:
            index: The in-process BM25 documentation index.
        """
        super().__init__()
        self._index = index

    def _run(self, query: str) -> str:
        """Synchronous execution -- not used; async path is preferred.

        Args:
            query: The search query string.

        Returns:
            Empty string (sync path not implemented).
        """
        return ""

    async def _arun(self, query: str) -> str:
        """Search Kyma documentation asynchronously and return formatted results.

        Args:
            query: The search query string.

        Returns:
            Formatted documentation pages separated by horizontal rules,
            or a message indicating no results were found.
        """
        docs = self._index.search(query, top_k=DEFAULT_TOP_K)
        logger.info(
            "doc_search",
            extra={
                "query": query,
                "result_count": len(docs),
                "results": [{"title": d.title, "url": d.url, "module": d.module, "path": d.path} for d in docs],
            },
        )
        if not docs:
            return "No relevant documentation found."
        return "\n\n---\n\n".join(_format_page(d) for d in docs)

    async def arun_documents(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[DocPage]:
        """Retrieve raw DocPage objects for the given query.

        Args:
            query: The search query string.
            top_k: Maximum number of documents to return.

        Returns:
            List of DocPage objects ordered by relevance descending.
        """
        return self._index.search(query, top_k=top_k)

    async def arun_list(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[str]:
        """Retrieve document content strings for the given query.

        Kept for backward compatibility with the REST endpoint and existing
        callers. Implemented on top of ``arun_documents``.

        Args:
            query: The search query string.
            top_k: Maximum number of documents to return.

        Returns:
            List of content strings for matched documents.
        """
        return [d.content for d in self._index.search(query, top_k=top_k)]


# Backward-compatibility alias so existing tests and callers that reference
# SearchKymaDocTool continue to work until they are updated.
SearchKymaDocTool = DocSearchTool
