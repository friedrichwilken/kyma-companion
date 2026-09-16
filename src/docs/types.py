"""Data types for the in-process documentation index."""

from dataclasses import dataclass


@dataclass
class DocPage:
    """A single documentation page loaded from the docs build artifact.

    Attributes:
        title: H1 heading or frontmatter title of the page.
        url: Canonical kyma-project.io URL for the page.
        repo: GitHub repository slug, e.g. "kyma-project/kyma".
        path: Repository-relative path to the Markdown file.
        module: Kyma module name (empty string if unknown or cross-cutting).
        content: Full Markdown text after preprocessing.
        doc_type: Coarse kind of page from the source's navigation: ``concept``,
            ``tutorial``, ``reference``, ``troubleshooting`` or ``release-notes``.
            Empty when the source has no navigation metadata.
        section: Navigation breadcrumb the page sits under, e.g. ``"Tutorials"``.
        mirror_of: Page ID of the canonical page this one duplicates (for example
            the kyma-project module page an SAP Help copy was derived from).
            Mirrors stay readable by ID but are not searched.
    """

    title: str
    url: str
    repo: str
    path: str
    module: str
    content: str
    doc_type: str = ""
    section: str = ""
    mirror_of: str = ""
