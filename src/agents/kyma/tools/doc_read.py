"""Tool to read a single Kyma documentation page by its page ID."""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from agents.kyma.tools.search import _format_page
from docs.index import DocIndex


class DocReadArgs(BaseModel):
    """Arguments for the read_kyma_doc tool."""

    page_id: str = Field(
        description='Page identifier in the form "repo::path", e.g. "kyma-project/kyma::docs/user/01-overview.md"',
    )


class DocReadTool(BaseTool):
    """Tool to read the full content of a specific Kyma documentation page by its page ID."""

    name: str = "read_kyma_doc"
    description: str = (
        "Read the full content of a specific Kyma documentation page by its page ID. "
        "Use after search_kyma_doc to get the complete text of a page."
    )
    args_schema: type[BaseModel] = DocReadArgs
    return_direct: bool = False

    _index: DocIndex = PrivateAttr()

    def __init__(self, index: DocIndex) -> None:
        """Initialize the tool with a pre-loaded DocIndex.

        Args:
            index: The in-process BM25 documentation index.
        """
        super().__init__()
        self._index = index

    def _run(self, page_id: str) -> str:
        """Synchronous execution — not used; async path is preferred.

        Args:
            page_id: The page identifier to look up.

        Returns:
            Empty string (sync path not implemented).
        """
        return ""

    async def _arun(self, page_id: str) -> str:
        """Read the full content of a documentation page asynchronously.

        Args:
            page_id: The page identifier in the form ``repo::path``.

        Returns:
            Formatted page content, or an error message if the page was not found.
        """
        page = self._index.read(page_id)
        if page is None:
            return f"Page not found: {page_id}"
        return _format_page(page)
