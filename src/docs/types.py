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
    """

    title: str
    url: str
    repo: str
    path: str
    module: str
    content: str
