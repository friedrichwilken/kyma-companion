"""BM25-backed tool for searching Kyma documentation."""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from docs.index import DocIndex, split_sections
from docs.types import DocPage
from utils.logging import get_logger

DEFAULT_TOP_K: int = 5
SEARCH_KYMA_DOC_TOOL_NAME: str = "search_kyma_doc"
# Pages longer than this (characters) are reduced to their intro plus the
# matched section in search results; read_kyma_doc returns the full text.
MAX_PAGE_CHARS: int = 12_000

logger = get_logger(__name__)


class DocSearchArgs(BaseModel):
    """Arguments for the search_kyma_doc tool."""

    query: str = Field(
        description="Search query to find relevant Kyma documentation",
        examples=["Help me get started with kyma", "What are Kyma components?"],
    )
    module: str = Field(
        default="",
        description=(
            "Optional Kyma module to search in, e.g. 'istio', 'serverless', 'api-gateway', 'eventing-manager', "
            "'telemetry-manager', 'btp-manager'. Use it when the question is about a resource of that module "
            "(the UI context names the module). Leave empty for general Kyma questions."
        ),
    )


def page_id(page: DocPage) -> str:
    """Return the identifier under which ``DocIndex.read`` finds *page*.

    Args:
        page: The page to identify.

    Returns:
        The ``<repo>::<path>`` identifier.
    """
    return f"{page.repo}::{page.path}"


def _excerpt(page: DocPage, matched_section: str) -> str:
    """Return the page content, reduced to intro plus matched section when the page is very long.

    Args:
        page: The page to excerpt.
        matched_section: Heading of the section that matched the query (``""`` for the intro).

    Returns:
        The full content for pages up to ``MAX_PAGE_CHARS``; otherwise the
        intro and the matched section with a note on how to read the rest.
    """
    if len(page.content) <= MAX_PAGE_CHARS:
        return page.content
    sections = split_sections(page.content)
    intro = sections[0][1] if sections and not sections[0][0] else ""
    matched = next((text for heading, text in sections if heading == matched_section), "")
    parts = [part for part in (intro, matched if matched_section else "") if part]
    note = f"[Page shortened to the matching section. Use read_kyma_doc with ID {page_id(page)} for the full page.]"
    return "\n\n".join([*parts, note])


def _format_page(page: DocPage, matched_section: str | None = None) -> str:
    """Format a single DocPage into a human-readable block with title, source URL, module, ID, and content.

    Args:
        page: A DocPage with title, url, module, and content fields.
        matched_section: Heading of the section that matched the query, when
            formatting a search result. ``None`` formats the whole page.

    Returns:
        Formatted string block for the page.
    """
    lines = [f"### {page.title}"]
    if page.url:
        lines.append(f"Source: {page.url}")
    if page.module:
        lines.append(f"Module: {page.module}")
    if page.doc_type:
        lines.append(f"Type: {page.doc_type}")
    lines.append(f"ID: {page_id(page)}")
    if matched_section:
        lines.append(f"Matched section: {matched_section}")
    lines.append("")
    lines.append(page.content if matched_section is None else _excerpt(page, matched_section))
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

    @property
    def index(self) -> DocIndex:
        """The documentation index this tool searches."""
        return self._index

    def _run(self, query: str, module: str = "") -> str:
        """Synchronous execution -- not used; async path is preferred.

        Args:
            query: The search query string.
            module: Optional module to restrict the search to.

        Returns:
            Empty string (sync path not implemented).
        """
        return ""

    async def _arun(self, query: str, module: str = "") -> str:
        """Search Kyma documentation asynchronously and return formatted results.

        Args:
            query: The search query string.
            module: Optional module to restrict the search to. When no page of
                that module matches, the search falls back to all modules.

        Returns:
            Formatted documentation pages separated by horizontal rules,
            or a message indicating no results were found.
        """
        hits = self._index.search_with_sections(query, top_k=DEFAULT_TOP_K, module=module)
        logger.info(
            "doc_search",
            extra={
                "query": query,
                "module_filter": module,
                "result_count": len(hits),
                "results": [
                    {
                        "title": d.title,
                        "url": d.url,
                        "module": d.module,
                        "doc_type": d.doc_type,
                        "path": d.path,
                        "section": section,
                    }
                    for d, section in hits
                ],
            },
        )
        if not hits:
            return "No relevant documentation found."
        return "\n\n---\n\n".join(_format_page(d, section) for d, section in hits)

    async def arun_documents(self, query: str, top_k: int = DEFAULT_TOP_K, module: str = "") -> list[DocPage]:
        """Retrieve raw DocPage objects for the given query.

        Args:
            query: The search query string.
            top_k: Maximum number of documents to return.
            module: Optional module to restrict the search to.

        Returns:
            List of DocPage objects ordered by relevance descending.
        """
        return self._index.search(query, top_k=top_k, module=module)

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
