"""Resolvers that select documentation pages from upstream sources of truth.

A resolver looks at a downloaded repository and decides which Markdown files
are user-facing documentation, using the structure the upstream project
maintains itself instead of a hand-picked path list:

- ``sidebar``: the ``_sidebar.ts`` navigation of a kyma-project module repo,
  which is what kyma-project.io publishes.
- ``sap_help_toc``: the table of contents of the SAP Help Portal repository,
  keeping only the subtrees whose title matches (for example "Kyma").
- ``tutorials``: SAP tutorial repositories, selecting tutorials whose path or
  frontmatter tags mention the match string.

Every resolver returns a :class:`Selection` with the chosen pages, their
canonical titles and a coarse ``doc_type``, plus the Markdown files in its
scope that it did not select (orphans) so that the curator can review them.
"""

import os
import re
from dataclasses import dataclass, field

from utils.logging import get_logger

logger = get_logger(__name__)

DOC_TYPE_CONCEPT = "concept"
DOC_TYPE_TUTORIAL = "tutorial"
DOC_TYPE_REFERENCE = "reference"
DOC_TYPE_TROUBLESHOOTING = "troubleshooting"
DOC_TYPE_RELEASE_NOTES = "release-notes"

_TROUBLESHOOTING_RE = re.compile(
    r"troubleshoot|diagnos|error|issue|fail|not (?:working|found|ready|delivered)|cannot|can't|unable|"
    r"pending|refused|forbidden|denied|missing|incompatible|conflict|reverting|recover",
    re.IGNORECASE,
)
_TUTORIAL_RE = re.compile(
    r"^(?:tutorial|getting started|get started|create|creating|configure|configuring|enable|enabling|expose|"
    r"exposing|deploy|deploying|set up|setting up|add|adding|manage|managing|migrate|migrating|use|using|send|"
    r"sending|subscribe|install|installing|assign|connect|integrate|update|delete|retrieve|access|run|running|"
    r"customize|inject|override|log into|collect|restart|choose|switch|activate|change|generate|build|test|"
    r"upgrade|provision|register|secure|scale|monitor|publish|trigger|bind|mount|migrat|register)\b",
    re.IGNORECASE,
)
_REFERENCE_RE = re.compile(
    r"reference|parameter|specification|\bapi\b|\bcr\b|custom resource|resources?$|architecture|glossary|"
    r"metrics|limitations|schema|presets|configmap|rbac|gen-docs|commands?$|\bkyma (?:alpha|module|app)\b",
    re.IGNORECASE,
)
_RELEASE_RE = re.compile(r"release notes?|what's new|changelog", re.IGNORECASE)


@dataclass
class SelectedPage:
    """A Markdown page chosen by a resolver."""

    path: str
    title: str = ""
    doc_type: str = ""
    section: str = ""


@dataclass
class Selection:
    """Result of running a resolver over a repository."""

    pages: dict[str, SelectedPage] = field(default_factory=dict)
    orphans: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    def add(self, page: SelectedPage) -> None:
        """Record *page* unless a page with the same path is already selected."""
        self.pages.setdefault(page.path, page)


def classify_doc_type(title: str, ancestors: list[str] | None = None) -> str:
    """Return a coarse document type for a page from its title and section titles.

    Section titles (the sidebar groups or table-of-contents branches a page
    sits under) take precedence, nearest first; the page title decides when no
    section title is telling.

    Args:
        title: The page title.
        ancestors: Section titles from the root down to the page's parent.

    Returns:
        One of the ``DOC_TYPE_*`` constants.
    """
    for text in [*reversed(ancestors or []), title]:
        if _RELEASE_RE.search(text):
            return DOC_TYPE_RELEASE_NOTES
        if _TROUBLESHOOTING_RE.search(text):
            return DOC_TYPE_TROUBLESHOOTING
        if re.search(r"tutorial", text, re.IGNORECASE):
            return DOC_TYPE_TUTORIAL
        if re.search(r"technical reference|^resources$|custom resources?$", text, re.IGNORECASE):
            return DOC_TYPE_REFERENCE
    if _TUTORIAL_RE.search(title):
        return DOC_TYPE_TUTORIAL
    if _REFERENCE_RE.search(title):
        return DOC_TYPE_REFERENCE
    return DOC_TYPE_CONCEPT


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _markdown_files(root: str) -> list[str]:
    """Return all ``.md`` paths under *root*, relative to it, sorted."""
    found: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".md"):
                found.append(os.path.relpath(os.path.join(dirpath, filename), root))
    return sorted(found)


def _resolve_link(repo_dir: str, base_dir: str, link: str) -> str | None:
    """Map a navigation link to an existing Markdown file, repository-relative.

    Sidebar and table-of-contents links come in several spellings: with or
    without ``.md``, pointing at a directory that holds a ``README.md``, or
    carrying an anchor. Returns ``None`` when no file matches.
    """
    target = link.split("#", 1)[0].strip()
    if not target:
        return None
    target = target.removeprefix("./")
    candidates = [target] if target.endswith(".md") else [f"{target}.md", f"{target}/README.md", target]
    for candidate in candidates:
        rel = os.path.normpath(os.path.join(base_dir, candidate))
        if rel.startswith("..") or not rel.endswith(".md"):
            continue
        if os.path.isfile(os.path.join(repo_dir, rel)):
            return rel
    return None


def _frontmatter(text: str) -> dict[str, str]:
    """Return the top-level scalar keys of a YAML frontmatter block, or ``{}``."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    result: dict[str, str] = {}
    for line in text[3:end].splitlines():
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if match:
            result[match.group(1)] = match.group(2).strip().strip("'\"")
    return result


def _h1(text: str) -> str:
    """Return the first H1 heading of Markdown text, or an empty string."""
    body = text
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4 :]
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return match.group(1).strip() if match else ""


# ---------------------------------------------------------------------------
# Sidebar resolver (kyma-project module repositories)
# ---------------------------------------------------------------------------

_SIDEBAR_TOKEN_RE = re.compile(
    r"(?P<open>\{)|(?P<close>\})|(?P<lopen>\[)|(?P<lclose>\])"
    r"|text:\s*'(?P<text>(?:\\.|[^'\\])*)'"
    r"|link:\s*'(?P<link>(?:\\.|[^'\\])*)'"
    r"|text:\s*\"(?P<text2>(?:\\.|[^\"\\])*)\""
    r"|link:\s*\"(?P<link2>(?:\\.|[^\"\\])*)\""
)


@dataclass
class SidebarNode:
    """One entry of a ``_sidebar.ts`` navigation tree."""

    text: str = ""
    link: str = ""
    items: list["SidebarNode"] = field(default_factory=list)


class _SidebarParser:
    """State of a tolerant token scan over a ``_sidebar.ts`` object literal."""

    def __init__(self) -> None:
        self.root: list[SidebarNode] = []
        self.list_stack: list[list[SidebarNode]] = []
        self.node_stack: list[SidebarNode] = []

    def feed(self, kind: str, value: str) -> None:
        """Apply one token to the parser state."""
        if kind == "lopen":
            self.list_stack.append(self.node_stack[-1].items if self.node_stack else self.root)
        elif kind == "lclose":
            if not self.list_stack:
                raise ValueError("unbalanced ']' in sidebar")
            self.list_stack.pop()
        elif kind == "open":
            if not self.list_stack:
                raise ValueError("object outside of a list in sidebar")
            node = SidebarNode()
            self.list_stack[-1].append(node)
            self.node_stack.append(node)
        elif kind == "close":
            if not self.node_stack:
                raise ValueError("unbalanced '}' in sidebar")
            self.node_stack.pop()
        elif kind in ("text", "text2") and self.node_stack:
            self.node_stack[-1].text = value.replace("\\'", "'").replace('\\"', '"')
        elif kind in ("link", "link2") and self.node_stack:
            self.node_stack[-1].link = value

    def finish(self) -> list[SidebarNode]:
        """Return the parsed tree, checking that every bracket was closed."""
        if self.list_stack or self.node_stack:
            raise ValueError("unbalanced brackets in sidebar")
        return self.root


def parse_sidebar(source: str) -> list[SidebarNode]:
    """Parse the object literal of a VitePress ``_sidebar.ts`` file.

    The files are uniform enough (``text``, ``link``, ``collapsed``, ``items``)
    that a tolerant token scan is sufficient; anything else is ignored.

    Args:
        source: Contents of the ``_sidebar.ts`` file.

    Returns:
        The top-level navigation nodes.

    Raises:
        ValueError: If brackets do not balance, which means the file layout
            changed and selection would silently pick nothing.
    """
    parser = _SidebarParser()
    for match in _SIDEBAR_TOKEN_RE.finditer(source):
        kind = match.lastgroup or ""
        parser.feed(kind, match.group(kind) or "")
    return parser.finish()


def resolve_sidebar(repo_dir: str, sidebar_path: str = "docs/user/_sidebar.ts") -> Selection:
    """Select the pages linked from a module repository's sidebar.

    Args:
        repo_dir: Root of the downloaded repository.
        sidebar_path: Repository-relative path of the sidebar file.

    Returns:
        The linked pages with sidebar titles and section-derived doc types,
        the directory's README as the module landing page even when the
        sidebar does not link it, plus every other Markdown file under the
        sidebar's directory that the sidebar does not link (orphans) and
        links that match no file.

    Raises:
        FileNotFoundError: If the sidebar file does not exist.
    """
    full_path = os.path.join(repo_dir, sidebar_path)
    with open(full_path, encoding="utf-8") as fh:
        nodes = parse_sidebar(fh.read())
    base_dir = os.path.dirname(sidebar_path)
    selection = Selection()

    def walk(items: list[SidebarNode], ancestors: list[str]) -> None:
        for node in items:
            if node.link:
                rel = _resolve_link(repo_dir, base_dir, node.link)
                if rel is None:
                    selection.unresolved.append(node.link)
                else:
                    selection.add(
                        SelectedPage(
                            path=rel,
                            title=node.text,
                            doc_type=classify_doc_type(node.text, ancestors),
                            section=" > ".join(ancestors),
                        )
                    )
            walk(node.items, [*ancestors, node.text] if node.text else ancestors)

    walk(nodes, [])
    # The site renders the directory's README as the module landing page without
    # a sidebar entry, so it is always part of the module's documentation.
    landing = os.path.normpath(os.path.join(base_dir, "README.md"))
    if landing not in selection.pages and os.path.isfile(os.path.join(repo_dir, landing)):
        with open(os.path.join(repo_dir, landing), encoding="utf-8", errors="replace") as fh:
            landing_title = _h1(fh.read())
        selection.add(SelectedPage(path=landing, title=landing_title, doc_type=DOC_TYPE_CONCEPT, section=""))
    scope = os.path.join(repo_dir, base_dir)
    selection.orphans = [
        os.path.normpath(os.path.join(base_dir, p))
        for p in _markdown_files(scope)
        if os.path.normpath(os.path.join(base_dir, p)) not in selection.pages
    ]
    logger.info(
        "Sidebar resolved",
        extra={
            "sidebar": sidebar_path,
            "pages": len(selection.pages),
            "orphans": len(selection.orphans),
            "unresolved": len(selection.unresolved),
        },
    )
    return selection


# ---------------------------------------------------------------------------
# SAP Help table-of-contents resolver
# ---------------------------------------------------------------------------

_TOC_LINE_RE = re.compile(r"^(?P<indent>\s*)-\s+\[(?P<title>[^\]]+)\]\((?P<link>[^)]+)\)")


def resolve_sap_help_toc(repo_dir: str, toc_path: str = "docs/index.md", title_match: str = r"(?i)kyma") -> Selection:
    """Select the subtrees of an SAP Help table of contents whose title matches.

    The table of contents is a nested Markdown list. A matching entry selects
    itself and everything nested below it. Pages can appear under several
    branches; the first matching branch wins and provides the section.

    Args:
        repo_dir: Root of the downloaded repository.
        toc_path: Repository-relative path of the table of contents.
        title_match: Regular expression an entry title must match to start a
            selected subtree.

    Returns:
        The selected pages, plus every Markdown file under the table of
        contents' directory that no selected entry links (orphans).
    """
    pattern = re.compile(title_match)
    base_dir = os.path.dirname(toc_path)
    with open(os.path.join(repo_dir, toc_path), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    selection = Selection()
    ancestors: list[tuple[int, str]] = []  # (indent, title)
    selected_depth: int | None = None
    for line in lines:
        match = _TOC_LINE_RE.match(line)
        if not match:
            continue
        indent = len(match.group("indent"))
        title = match.group("title").strip()
        while ancestors and ancestors[-1][0] >= indent:
            ancestors.pop()
        if selected_depth is not None and indent <= selected_depth:
            selected_depth = None
        if selected_depth is None and pattern.search(title):
            selected_depth = indent
        if selected_depth is not None:
            rel = _resolve_link(repo_dir, base_dir, match.group("link"))
            if rel is None:
                selection.unresolved.append(match.group("link"))
            else:
                section_titles = [t for _, t in ancestors]
                selection.add(
                    SelectedPage(
                        path=rel,
                        title=title,
                        doc_type=classify_doc_type(title, section_titles),
                        section=" > ".join(section_titles),
                    )
                )
        ancestors.append((indent, title))
    scope = os.path.join(repo_dir, base_dir)
    selection.orphans = [
        os.path.normpath(os.path.join(base_dir, p))
        for p in _markdown_files(scope)
        if os.path.normpath(os.path.join(base_dir, p)) not in selection.pages
    ]
    logger.info(
        "SAP Help TOC resolved",
        extra={"toc": toc_path, "pages": len(selection.pages), "orphans": len(selection.orphans)},
    )
    return selection


# ---------------------------------------------------------------------------
# Tutorials resolver (sap-tutorials repositories)
# ---------------------------------------------------------------------------


def resolve_tutorials(repo_dir: str, root: str = "tutorials", match: str = "kyma") -> Selection:
    """Select tutorials whose path or frontmatter tags mention *match*.

    The tutorial repositories tag Kyma content inconsistently (three spellings
    of the same ``primary_tag`` exist), while the tutorial directory name is
    reliable, so both are checked.

    Args:
        repo_dir: Root of the downloaded repository.
        root: Repository-relative directory holding the tutorials.
        match: Case-insensitive substring to look for.

    Returns:
        The selected tutorials with their frontmatter titles, and the rest of
        the tutorials as orphans.
    """
    needle = match.lower()
    scope = os.path.join(repo_dir, root)
    selection = Selection()
    for rel in _markdown_files(scope):
        path = os.path.normpath(os.path.join(root, rel))
        with open(os.path.join(repo_dir, path), encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        meta = _frontmatter(text)
        tags = " ".join(v for k, v in meta.items() if k in ("tags", "primary_tag", "keywords")).lower()
        if needle in path.lower() or needle in tags:
            title = meta.get("title") or _h1(text)
            selection.add(SelectedPage(path=path, title=title, doc_type=DOC_TYPE_TUTORIAL, section=root))
        else:
            selection.orphans.append(path)
    logger.info(
        "Tutorials resolved", extra={"root": root, "pages": len(selection.pages), "orphans": len(selection.orphans)}
    )
    return selection
