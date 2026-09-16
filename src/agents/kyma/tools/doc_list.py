"""Tool to list available Kyma documentation pages."""

from collections import Counter

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
        "List the Kyma documentation modules, or the pages of one module (title, type, URL, page ID). "
        "Call without arguments to see the modules, then with a module to see its pages. "
        "Use it to find a specific page when search_kyma_doc did not surface it."
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
            Without a module: one line per module with its page count. With a
            module: a Markdown list of its pages with type, URL and page ID,
            or a message indicating no pages were found.
        """
        if not module:
            counts = Counter(p.module or "(no module)" for p in self._index.list_module())
            lines = [f"- {name}: {count} pages" for name, count in sorted(counts.items())]
            return "## Kyma documentation modules (pass one as `module` to list its pages)\n" + "\n".join(lines)
        pages = self._index.list_module(module)
        if not pages:
            return f"No pages found for module: {module}."
        lines = [
            f"- [{p.title}]({p.url}) `{p.repo}::{p.path}`" + (f" ({p.doc_type})" if p.doc_type else "") for p in pages
        ]
        header = f"## Kyma Documentation ({len(pages)} pages, module: {module})\n"
        return header + "\n".join(lines)
