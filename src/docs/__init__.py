"""In-process documentation index for the kyma-companion docs build artifact.

This package provides a lightweight BM25-based search index that operates
entirely in-process without any external vector database or embedding service.

Public API::

    from docs import DocIndex, DocPage

    index = DocIndex("/path/to/docs-artifact")
    index.load()
    results = index.search("serverless function scaling", top_k=5)
    page = index.read("kyma-project/kyma::docs/05-technical-reference/README.md")
"""

from docs.index import DocIndex
from docs.types import DocPage

__all__ = ["DocIndex", "DocPage"]
