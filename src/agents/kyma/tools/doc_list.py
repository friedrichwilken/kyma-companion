"""Tool to list available Kyma documentation pages."""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from docs.index import DocIndex


class DocListArgs(BaseModel):
    """Arguments for the list_kyma_docs tool."""

    module: str = Field(
        default="",
        description='Documentation source to filter by, e.g. "eventing-manager" or "istio". Leave empty to list all.',
    )


class DocListTool(BaseTool):
    """Tool to list available Kyma documentation pages, optionally filtered by module."""

    name: str = "list_kyma_docs"
    description: str = (
        "List available Kyma documentation pages, optionally filtered by module. "
        "Returns page titles, URLs and IDs. "
        "Use to discover what documentation is available."
    )
    args_schema: type[BaseModel] = DocListArgs
    return_direct: bool = False

    _index: DocIndex = PrivateAttr()

    def __init__(self, index: DocIndex) -> None:
        """Initialize the tool with a pre-loaded DocIndex.

        Args:
            index: The in-process BM25 documentation index.
        """
        super().__init__()
        self._index = index

    def _run(self, module: str = "") -> str:
        """Synchronous execution — not used; async path is preferred.

        Args:
            module: Optional module name to filter by.

        Returns:
            Empty string (sync path not implemented).
        """
        return ""

    async def _arun(self, module: str = "") -> str:
        """List documentation pages asynchronously, with optional module filter.

        Args:
            module: If non-empty, restrict results to pages belonging to this module.

        Returns:
            Markdown-formatted list of pages with title, URL, and page ID,
            or a message indicating no pages were found.
        """
        pages = self._index.list_module(module)
        if not pages:
            return f"No pages found{' for module: ' + module if module else ''}."
        lines = [f"- [{p.title}]({p.url}) `{p.repo}::{p.path}`" for p in pages]
        header = f"## Kyma Documentation ({len(pages)} pages{', module: ' + module if module else ''})\n"
        return header + "\n".join(lines)
