import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from utils.logging import get_logger

logger = get_logger(__name__)


class SourceType(StrEnum):
    """Enum for the documents source type."""

    GITHUB = "Github"


class ResolverConfig(BaseModel):
    """How to select pages from a source using its own navigation structure.

    Attributes:
        type: ``sidebar`` (kyma-project module repos, ``docs/user/_sidebar.ts``),
            ``sap_help_toc`` (SAP Help Portal repo, ``docs/index.md``) or
            ``tutorials`` (sap-tutorials repos).
        path: Sidebar or table-of-contents file, or tutorials root directory.
            Defaults depend on the resolver type.
        title_match: ``sap_help_toc`` only: regular expression a table-of-contents
            entry must match for its subtree to be selected.
        match: ``tutorials`` only: case-insensitive substring a tutorial path or
            frontmatter tag must contain.
    """

    type: Literal["sidebar", "sap_help_toc", "tutorials"]
    path: str | None = None
    title_match: str | None = None
    match: str | None = None


class DocumentsSource(BaseModel):
    """Model for the documents source.

    ``include_files`` and ``exclude_files`` are glob patterns. When a
    ``resolver`` is configured the resolver's selection is used and
    ``include_files`` only adds explicit extras on top of it.
    """

    name: str
    source_type: SourceType
    url: str
    include_files: list[str] | None = None
    exclude_files: list[str] | None = None
    filter_file_types: list[str] = ["md"]
    resolver: ResolverConfig | None = None


def get_documents_sources(path: str) -> list[DocumentsSource]:
    """Reads the documents sources from the json file."""
    logger.info("Loading document sources", extra={"path": path})
    sources = []
    with open(path) as f:
        json_obj = json.load(f)
        for item in json_obj:
            sources.append(DocumentsSource(**item))
    logger.info("Loaded document sources", extra={"path": path, "count": len(sources)})
    return sources
