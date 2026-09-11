"""PR body report generator for documentation curation results."""

from curation.types import ClassificationResult

CLASSIFIER_ERROR_PREFIX = "classifier error:"


def _page_link(path: str, repo_url: str) -> str:
    """Return a Markdown link or bare path depending on whether repo_url is set.

    Args:
        path: The file path within the repository.
        repo_url: Base URL of the repository, or empty string.

    Returns:
        A Markdown link string if repo_url is set, otherwise the bare path.
    """
    if repo_url:
        return f"[{path}]({repo_url}/blob/HEAD/{path})"
    return path


def _view_link(path: str, repo_url: str) -> str:
    """Return a Markdown [View file](url) link, or empty string if no repo_url.

    Args:
        path: The file path within the repository.
        repo_url: Base URL of the repository, or empty string.

    Returns:
        A formatted [View file](url) string, or empty string.
    """
    if repo_url:
        return f"[View file]({repo_url}/blob/HEAD/{path})"
    return ""


def _summary_section(
    added_pages: list[str],
    removed_pages: list[str],
    needs_decision_count: int,
) -> str:
    """Build the ## Summary section text.

    Args:
        added_pages: List of page paths added in this update.
        removed_pages: List of page paths removed in this update.
        needs_decision_count: Number of items requiring a manual decision.

    Returns:
        Markdown text for the Summary section.
    """
    parts: list[str] = []
    if added_pages:
        n = len(added_pages)
        parts.append(f"{n} page{'s' if n != 1 else ''} added")
    if removed_pages:
        m = len(removed_pages)
        parts.append(f"{m} page{'s' if m != 1 else ''} removed")
    if needs_decision_count:
        k = needs_decision_count
        if k == 1:
            parts.append("1 item needs a decision")
        else:
            parts.append(f"{k} items need a decision")
    body = ", ".join(parts) if parts else "No changes."
    return f"## Summary\n\n{body}"


def _added_pages_section(
    added_pages: list[str],
    included: list[ClassificationResult],
    repo_url: str,
) -> str:
    """Build the ## Added pages section text.

    Args:
        added_pages: Ordered list of page paths to include in the table.
        included: Classification results with decision == "include".
        repo_url: Base repository URL for generating file links.

    Returns:
        Markdown text for the Added pages section.
    """
    include_by_path: dict[str, ClassificationResult] = {r.candidate.path: r for r in included}
    lines = ["## Added pages", "", "| Page | Module | Rationale |", "| --- | --- | --- |"]
    for page in added_pages:
        result = include_by_path.get(page)
        page_cell = _page_link(page, repo_url)
        module = result.candidate.repo if result else ""
        rationale = result.rationale if result else ""
        lines.append(f"| {page_cell} | {module} | {rationale} |")
    return "\n".join(lines)


def _removed_pages_section(
    removed_pages: list[str],
    excluded: list[ClassificationResult],
) -> str:
    """Build the ## Removed pages section text.

    Args:
        removed_pages: Ordered list of page paths that were removed.
        excluded: Classification results with decision == "exclude".

    Returns:
        Markdown text for the Removed pages section.
    """
    exclude_by_path: dict[str, ClassificationResult] = {r.candidate.path: r for r in excluded}
    lines = ["## Removed pages", ""]
    for page in removed_pages:
        result = exclude_by_path.get(page)
        if result:
            lines.append(f"- {page} -- {result.rationale}")
        else:
            lines.append(f"- {page}")
    return "\n".join(lines)


def _needs_decision_section(unsure: list[ClassificationResult], repo_url: str) -> str:
    """Build the ## Needs a decision section text.

    Args:
        unsure: Classification results with decision == "unsure".
        repo_url: Base repository URL for generating file links.

    Returns:
        Markdown text for the Needs a decision section.
    """
    lines = ["## Needs a decision", ""]
    for r in unsure:
        key = f"{r.candidate.repo}::{r.candidate.path}"
        lines.append(f"- [ ] `{key}` -- {r.rationale}")
        view = _view_link(r.candidate.path, repo_url)
        if view:
            lines.append(f"  {view}")
    return "\n".join(lines)


def _unclassified_section(errors: list[ClassificationResult]) -> str:
    """Build the ## Unclassified section text.

    Args:
        errors: Results whose rationale starts with CLASSIFIER_ERROR_PREFIX.

    Returns:
        Markdown text for the Unclassified section.
    """
    lines = ["## Unclassified", ""]
    for r in errors:
        key = f"{r.candidate.repo}::{r.candidate.path}"
        lines.append(f"- `{key}`: {r.rationale}")
    return "\n".join(lines)


def generate_pr_body(
    results: list[ClassificationResult],
    added_pages: list[str],
    removed_pages: list[str],
    repo_url: str = "",
) -> str:
    """Generate a Markdown PR body from classification results.

    Produces a Markdown string with sections for summary, added pages,
    removed pages, items needing a decision, and unclassified items.
    Sections are omitted when they have no content.

    Args:
        results: Classification results from the curation agent.
        added_pages: List of page paths added in this update.
        removed_pages: List of page paths removed in this update.
        repo_url: Base URL of the repository (e.g. https://github.com/org/repo).
                  Used to generate links. If empty, bare paths are used.

    Returns:
        A Markdown string suitable for use as a GitHub PR body.
    """
    errors = [r for r in results if r.rationale.startswith(CLASSIFIER_ERROR_PREFIX)]
    included = [r for r in results if r.decision == "include" and r not in errors]
    excluded = [r for r in results if r.decision == "exclude" and r not in errors]
    unsure = [r for r in results if r.decision == "unsure" and r not in errors]

    sections: list[str] = [_summary_section(added_pages, removed_pages, len(unsure))]

    if added_pages:
        sections.append(_added_pages_section(added_pages, included, repo_url))
    if removed_pages:
        sections.append(_removed_pages_section(removed_pages, excluded))
    if unsure:
        sections.append(_needs_decision_section(unsure, repo_url))
    if errors:
        sections.append(_unclassified_section(errors))

    return "\n\n".join(sections) + "\n"
