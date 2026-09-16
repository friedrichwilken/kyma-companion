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


_FRONTMATTER_TITLE_RE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)


def _frontmatter_title(text: str) -> str:
    """Return the ``title`` value of a YAML frontmatter block, or an empty string.

    Args:
        text: Raw Markdown text that may begin with a YAML frontmatter block.

    Returns:
        The title with surrounding quotes removed, or ``""`` when there is no
        frontmatter or it has no ``title`` key.
    """
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end == -1:
        return ""
    match = _FRONTMATTER_TITLE_RE.search(text[3:end])
    if not match:
        return ""
    return match.group(1).strip().strip("'\"")


def _extract_title(content: str) -> str:
    """Extract a page title from content.

    Looks for the first ``# `` H1 heading after stripping frontmatter. Falls
    back to the frontmatter ``title`` key (used by the SAP tutorials, which
    carry no H1), and finally returns an empty string.

    Args:
        content: Full Markdown text (may include frontmatter).

    Returns:
        The page title as a plain string (without the leading ``# ``).
    """
    stripped = _strip_frontmatter(content)
    match = re.search(r"^#\s+(.+)", stripped, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return _frontmatter_title(content)


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

# Sources whose pages are the canonical version of a document. Pages from other
# sources that share a title with a canonical page are treated as mirrors.
_CANONICAL_REPO_PREFIX = "kyma-project/"


def _title_key(title: str) -> str:
    """Return the tokenized form of a title used to detect the same page across sources."""
    return " ".join(_tokenize(title))


# Number of times a section heading's tokens are repeated in the section's BM25 document.
_HEADING_WEIGHT = 2
# H2 sections longer than this many tokens are split further at H3 headings.
_SECTION_SPLIT_TOKENS = 1200

_H2_RE = re.compile(r"^##\s+(.+?)\s*#*\s*$")
_H3_RE = re.compile(r"^###\s+(.+?)\s*#*\s*$")


def _split_at(text: str, heading_re: re.Pattern[str]) -> list[tuple[str, str]]:
    """Split Markdown text at headings matching *heading_re*, ignoring fenced code.

    Args:
        text: Markdown text.
        heading_re: Pattern for a heading line; group 1 is the heading text.

    Returns:
        ``(heading, body)`` pairs in document order. The text before the first
        heading is returned with an empty heading, and is omitted when blank.
    """
    parts: list[tuple[str, str]] = []
    heading = ""
    body: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else heading_re.match(line)
        if match:
            parts.append((heading, "\n".join(body)))
            heading, body = match.group(1).strip(), []
        else:
            body.append(line)
    parts.append((heading, "\n".join(body)))
    return [(h, b) for h, b in parts if h or b.strip()]


def split_sections(content: str) -> list[tuple[str, str]]:
    """Split a page into retrieval units: the intro, then one unit per H2 section.

    H2 sections longer than ``_SECTION_SPLIT_TOKENS`` tokens are split again at
    their H3 headings; those units are labelled ``"<H2> / <H3>"``.

    Args:
        content: Cleaned Markdown content of a page.

    Returns:
        ``(heading, body)`` pairs; the intro has an empty heading. A page
        without H2 headings yields a single intro unit.
    """
    units: list[tuple[str, str]] = []
    for heading, body in _split_at(content, _H2_RE):
        if heading and len(_tokenize(body)) > _SECTION_SPLIT_TOKENS:
            for sub_heading, sub_body in _split_at(body, _H3_RE):
                units.append((f"{heading} / {sub_heading}" if sub_heading else heading, sub_body))
        else:
            units.append((heading, body))
    return units or [("", content)]


class DocIndex:
    """In-process BM25 search index over a local documentation artifact directory.

    The directory layout expected by this class is produced by the
    ``doc_indexer`` service::

        <docs_path>/
          <module-dir>/       # one directory per source, named by source
            <relative>.md
            meta.json         # optional: repo, module, base_url, and per-page
                              # navigation metadata (title, doc_type, section)

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
        self._unit_page: list[int] = []
        self._unit_heading: list[str] = []
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
        self._unit_page = []
        self._unit_heading = []
        self._loaded = False
        title_keys: dict[str, set[str]] = {}

        for module_dir_name in sorted(os.listdir(self._docs_path)):
            module_dir = os.path.join(self._docs_path, module_dir_name)
            if not os.path.isdir(module_dir):
                continue
            meta = self._read_meta(module_dir)
            repo = str(meta.get("repo", module_dir_name))
            module = str(meta.get("module", ""))
            base_url = str(meta.get("base_url", ""))
            page_meta: dict[str, Any] = meta.get("pages", {}) if isinstance(meta.get("pages"), dict) else {}

            for dirpath, _dirnames, filenames in os.walk(module_dir):
                for filename in sorted(filenames):
                    if not filename.endswith(".md"):
                        continue
                    full_path = os.path.join(dirpath, filename)
                    rel_to_module = os.path.relpath(full_path, module_dir)
                    raw = self._read_file(full_path)
                    nav: dict[str, Any] = page_meta.get(rel_to_module, {})
                    # The navigation title (sidebar or table of contents) is canonical;
                    # the H1 or frontmatter title is the fallback.
                    heading = _extract_title(raw)
                    title = str(nav.get("title") or heading)
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
                        doc_type=str(nav.get("doc_type", "")),
                        section=str(nav.get("section", "")),
                    )
                    self._pages[page_id] = page
                    self._page_list.append(page)
                    title_keys[page_id] = {_title_key(t) for t in (title, heading) if t}

        self._mark_mirrors(title_keys)
        self._page_list = [page for page in self._page_list if not page.mirror_of]

        if self._page_list:
            self._build_corpus()

        self._loaded = True

    def _build_corpus(self) -> None:
        """Compile the section-level BM25 index over the searchable pages.

        Every page is split into retrieval units (intro plus one per H2 section,
        long H2 sections further by H3). A unit's document is the page title
        repeated ``_TITLE_WEIGHT`` times, the unit heading repeated
        ``_HEADING_WEIGHT`` times, and the unit body. Scoring sections instead
        of whole pages stops long pages from being penalised by length
        normalisation when only one of their sections answers the query.
        """
        unit_docs: list[list[str]] = []
        for page_index, page in enumerate(self._page_list):
            title_tokens = _tokenize(page.title) * _TITLE_WEIGHT
            for heading, body in split_sections(_index_text(page.content)):
                unit_docs.append(title_tokens + _tokenize(heading) * _HEADING_WEIGHT + _tokenize(body))
                self._unit_page.append(page_index)
                self._unit_heading.append(heading)
        self._bm25 = BM25Okapi(unit_docs)

    def _page_scores(self, tokens: list[str]) -> tuple[list[float], list[str]]:
        """Score every searchable page for *tokens* by its best-matching section.

        Args:
            tokens: Tokenized query.

        Returns:
            Per page index, the score and the heading of the best section
            (empty for the intro).
        """
        assert self._bm25 is not None  # noqa: S101
        unit_scores: list[float] = self._bm25.get_scores(tokens).tolist()
        best: list[float] = [float("-inf")] * len(self._page_list)
        best_heading: list[str] = [""] * len(self._page_list)
        for unit_index, score in enumerate(unit_scores):
            page_index = self._unit_page[unit_index]
            if score > best[page_index]:
                best[page_index] = score
                best_heading[page_index] = self._unit_heading[unit_index]
        return best, best_heading

    def _mark_mirrors(self, title_keys: dict[str, set[str]]) -> None:
        """Link non-canonical pages to the canonical page with the same title.

        The SAP Help Portal republishes the module documentation from the
        kyma-project repositories under the same titles. Indexing both copies
        lets them compete for the same result slot and skews term statistics,
        so the copy is marked as a mirror of the kyma-project page and left
        out of the search corpus. It remains readable by its page ID.

        Args:
            title_keys: Per page ID, the tokenized navigation title and H1 of
                the page. Both are compared, because a module sidebar may
                label a page differently from its heading while the copy
                keeps the heading.
        """
        canonical: dict[str, str] = {}
        for page_id, page in self._pages.items():
            if page.repo.startswith(_CANONICAL_REPO_PREFIX):
                for key in title_keys.get(page_id, ()):
                    canonical.setdefault(key, page_id)
        for page_id, page in self._pages.items():
            if page.repo.startswith(_CANONICAL_REPO_PREFIX):
                continue
            for key in title_keys.get(page_id, ()):
                original = canonical.get(key)
                if original and original != page_id:
                    page.mirror_of = original
                    break

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
        return [page for page, _heading in self.search_with_sections(query, top_k, module)]

    def search_with_sections(self, query: str, top_k: int = 5, module: str = "") -> list[tuple[DocPage, str]]:
        """Like :meth:`search`, but also return the heading of each page's best-matching section.

        Args:
            query: Free-text search query.
            top_k: Maximum number of results to return.
            module: Optional module filter, see :meth:`search`.

        Returns:
            ``(page, heading)`` pairs ordered by relevance descending; the
            heading is empty when the page's intro matched best.
        """
        if not self._loaded or self._bm25 is None or not self._page_list:
            return []

        tokens = _tokenize(query)
        scores, headings = self._page_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        if module:
            filtered = [(i, s) for i, s in ranked if self._page_list[i].module.lower() == module.lower()]
            if filtered:
                ranked = filtered
            # Fall back to global ranking when filter yields nothing.

        return [(page, headings[i]) for i, page in self._unique_by_title(ranked, top_k)]

    def _unique_by_title(self, ranked: list[tuple[int, float]], top_k: int) -> list[tuple[int, DocPage]]:
        """Take pages from *ranked* (descending score) until *top_k*, skipping repeated titles.

        Titles are compared after tokenization, so differences in case or
        punctuation do not keep two copies of the same page apart. Untitled
        pages are never collapsed.

        Args:
            ranked: ``(page index, score)`` pairs in descending score order.
            top_k: Maximum number of pages to return.

        Returns:
            Up to *top_k* ``(page index, page)`` pairs with distinct titles.
        """
        seen: set[str] = set()
        results: list[tuple[int, DocPage]] = []
        for i, _score in ranked:
            page = self._page_list[i]
            key = " ".join(_tokenize(page.title))
            if key:
                if key in seen:
                    continue
                seen.add(key)
            results.append((i, page))
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
        """Total number of pages currently held in the index, mirrors included."""
        return len(self._pages)

    @property
    def searchable_count(self) -> int:
        """Number of pages in the search corpus (mirrors excluded)."""
        return len(self._page_list)

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
