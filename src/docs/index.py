"""In-process BM25-based documentation index for the docs build artifact."""

import json
import os
import re
from typing import Any

from rank_bm25 import BM25Okapi

from docs.types import DocPage


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block from Markdown text.

    Args:
        text: Raw Markdown text that may begin with a YAML frontmatter block.

    Returns:
        Markdown text with the frontmatter block removed, or the original text
        if no frontmatter was present.
    """
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :].lstrip("\n")
    return text


def _extract_title(content: str, meta: dict[str, Any]) -> str:
    """Extract a page title from content or metadata.

    Looks for the first ``# `` H1 heading after stripping frontmatter.  Falls
    back to the ``title`` key in *meta*, and finally returns an empty string.

    Args:
        content: Full Markdown text (may include frontmatter).
        meta: Parsed ``meta.json`` dictionary for the containing module directory.

    Returns:
        The page title as a plain string (without the leading ``# ``).
    """
    stripped = _strip_frontmatter(content)
    match = re.search(r"^#\s+(.+)", stripped, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return str(meta.get("title", ""))


def _build_url(base_url: str, repo: str, rel_path: str) -> str:
    """Construct the canonical URL for a documentation page.

    Args:
        base_url: Base URL from ``meta.json`` (may be empty).
        repo: GitHub repository slug used as a fallback prefix.
        rel_path: Repository-relative path to the Markdown file.

    Returns:
        A URL string formed by joining *base_url* (or *repo*) with *rel_path*.
    """
    prefix = base_url.rstrip("/") if base_url else repo.rstrip("/")
    path_part = rel_path.lstrip("/")
    return f"{prefix}/{path_part}"


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Very common English function words that carry no retrieval signal. Kept
# deliberately small: domain words such as "module" or "cluster" must stay.
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how",
        "i", "if", "in", "is", "it", "its", "my", "of", "on", "or", "that", "the", "this", "to",
        "was", "what", "when", "which", "with", "you", "your",
    }
)  # fmt: skip


def _clean_content(text: str) -> str:
    """Strip frontmatter and HTML comments from Markdown text.

    This is the text handed to the agent, so the Markdown structure itself is
    kept; only invisible or non-content blocks are removed.

    Args:
        text: Raw Markdown text as read from disk.

    Returns:
        Markdown text without YAML frontmatter and HTML comments.
    """
    return _HTML_COMMENT_RE.sub("", _strip_frontmatter(text)).strip("\n")


def _index_text(text: str) -> str:
    """Reduce cleaned Markdown to the text worth indexing.

    Link and image targets, HTML tags and Markdown emphasis contribute tokens
    such as ``https``, ``github`` or ``md`` that match nothing meaningful, so
    they are dropped while link labels and code identifiers are kept.

    Args:
        text: Cleaned Markdown text (see :func:`_clean_content`).

    Returns:
        Plain text suitable for :func:`_tokenize`.
    """
    text = _MD_IMAGE_RE.sub(r"\1", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    return _HTML_TAG_RE.sub(" ", text)


def _tokenize(text: str) -> list[str]:
    """Tokenize text for BM25 indexing and querying.

    Lowercases, splits on anything that is not a letter or digit (so
    ``Kyma?``, a back-ticked ``APIRule`` and ``**Istio**`` become ``kyma``,
    ``apirule`` and ``istio``), and drops a small set of English stopwords.

    Args:
        text: Input text to tokenize.

    Returns:
        List of lowercase alphanumeric tokens.
    """
    return [tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in _STOPWORDS]


# Number of times title tokens are repeated to weight them higher than body tokens.
_TITLE_WEIGHT = 3


class DocIndex:
    """In-process BM25 search index over a local documentation artifact directory.

    The directory layout expected by this class is produced by the
    ``doc_indexer`` service::

        <docs_path>/
          <module-dir>/       # one directory per repo, named by repo slug
            <relative>.md
            meta.json         # optional: repo, module, base_url metadata

    Usage::

        index = DocIndex("/path/to/docs")
        index.load()
        results = index.search("serverless function scaling")
    """

    def __init__(self, docs_path: str) -> None:
        """Initialise the index with the path to the docs artifact directory.

        Args:
            docs_path: Filesystem path to the root of the docs build artifact.
        """
        self._docs_path = docs_path
        self._pages: dict[str, DocPage] = {}
        self._page_list: list[DocPage] = []
        self._bm25: BM25Okapi | None = None
        self._loaded = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Scan *docs_path*, build the page registry, and compile the BM25 index.

        Walking is performed top-down; every ``.md`` file found underneath a
        top-level sub-directory is treated as a documentation page.  A
        ``meta.json`` file in the sub-directory root supplies repo slug, module
        name, and base URL for all pages within that sub-directory.

        This method is idempotent: calling it a second time re-scans and
        rebuilds the index from scratch.
        """
        self._pages = {}
        self._page_list = []
        self._bm25 = None
        self._loaded = False

        for module_dir_name in sorted(os.listdir(self._docs_path)):
            module_dir = os.path.join(self._docs_path, module_dir_name)
            if not os.path.isdir(module_dir):
                continue
            meta = self._read_meta(module_dir)
            repo = str(meta.get("repo", module_dir_name))
            module = str(meta.get("module", ""))
            base_url = str(meta.get("base_url", ""))

            for dirpath, _dirnames, filenames in os.walk(module_dir):
                for filename in sorted(filenames):
                    if not filename.endswith(".md"):
                        continue
                    full_path = os.path.join(dirpath, filename)
                    rel_to_module = os.path.relpath(full_path, module_dir)
                    raw = self._read_file(full_path)
                    title = _extract_title(raw, meta)
                    content = _clean_content(raw)
                    url = _build_url(base_url, repo, rel_to_module)
                    page_id = f"{repo}::{rel_to_module}"
                    page = DocPage(
                        title=title,
                        url=url,
                        repo=repo,
                        path=rel_to_module,
                        module=module,
                        content=content,
                    )
                    self._pages[page_id] = page
                    self._page_list.append(page)

        if self._page_list:
            corpus = [
                _tokenize(page.title) * _TITLE_WEIGHT + _tokenize(_index_text(page.content)) for page in self._page_list
            ]
            self._bm25 = BM25Okapi(corpus)

        self._loaded = True

    def search(self, query: str, top_k: int = 5, module: str = "") -> list[DocPage]:
        """Return the top-ranked pages for *query* using BM25.

        Pages that share a title are collapsed to the highest-scoring one, so
        a page and its mirror in another source (for example a module page
        and its SAP Help copy) do not both occupy a result slot.

        Args:
            query: Free-text search query.
            top_k: Maximum number of results to return.
            module: If non-empty, restrict results to pages whose
                ``module`` field matches (case-insensitive).  When no
                matching pages exist the filter is dropped and the global
                top-*k* results are returned instead.

        Returns:
            Up to *top_k* ``DocPage`` objects ordered by relevance descending.
        """
        if not self._loaded or self._bm25 is None or not self._page_list:
            return []

        tokens = _tokenize(query)
        scores: list[float] = self._bm25.get_scores(tokens).tolist()
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        if module:
            filtered = [(i, s) for i, s in ranked if self._page_list[i].module.lower() == module.lower()]
            if filtered:
                return self._unique_by_title(filtered, top_k)
            # Fall back to global ranking when filter yields nothing.

        return self._unique_by_title(ranked, top_k)

    def _unique_by_title(self, ranked: list[tuple[int, float]], top_k: int) -> list[DocPage]:
        """Take pages from *ranked* (descending score) until *top_k*, skipping repeated titles.

        Titles are compared after tokenization, so differences in case or
        punctuation do not keep two copies of the same page apart. Untitled
        pages are never collapsed.

        Args:
            ranked: ``(page index, score)`` pairs in descending score order.
            top_k: Maximum number of pages to return.

        Returns:
            Up to *top_k* distinct-title ``DocPage`` objects.
        """
        seen: set[str] = set()
        results: list[DocPage] = []
        for i, _score in ranked:
            page = self._page_list[i]
            key = " ".join(_tokenize(page.title))
            if key:
                if key in seen:
                    continue
                seen.add(key)
            results.append(page)
            if len(results) == top_k:
                break
        return results

    def read(self, page_id: str) -> DocPage | None:
        """Return the page identified by *page_id*, or ``None`` if not found.

        Args:
            page_id: Composite identifier in the form ``<repo>::<path>``.

        Returns:
            The matching ``DocPage``, or ``None``.
        """
        return self._pages.get(page_id)

    def list_module(self, module: str = "") -> list[DocPage]:
        """Return all pages, optionally restricted to a single module.

        Results are sorted by ``(module, path)`` in ascending order.

        Args:
            module: If non-empty, only pages whose ``module`` field matches
                (case-insensitive) are returned.

        Returns:
            Sorted list of ``DocPage`` objects.
        """
        pages = self._page_list
        if module:
            pages = [p for p in pages if p.module.lower() == module.lower()]
        return sorted(pages, key=lambda p: (p.module, p.path))

    @property
    def page_count(self) -> int:
        """Total number of pages currently held in the index."""
        return len(self._pages)

    @property
    def is_loaded(self) -> bool:
        """``True`` after :py:meth:`load` has completed successfully."""
        return self._loaded

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_meta(directory: str) -> dict[str, Any]:
        """Read and parse ``meta.json`` from *directory*, returning ``{}`` on failure.

        Args:
            directory: Filesystem path to search for ``meta.json``.

        Returns:
            Parsed JSON object as a dictionary, or an empty dict.
        """
        meta_path = os.path.join(directory, "meta.json")
        if not os.path.isfile(meta_path):
            return {}
        try:
            with open(meta_path, encoding="utf-8") as fh:
                return json.load(fh)  # type: ignore[no-any-return]
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _read_file(path: str) -> str:
        """Read a text file and return its contents.

        Args:
            path: Absolute filesystem path to the file.

        Returns:
            File contents as a string, or an empty string on read error.
        """
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return ""
