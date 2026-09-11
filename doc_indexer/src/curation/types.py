"""Shared dataclasses for the curation pipeline.

These types are defined here as stubs so the eval-classifier can operate
independently.  Issue #51 (classify-residue + decisions-cache) will flesh
out the full implementations; when that branch is merged this file should
be replaced by the canonical definitions.
"""

from dataclasses import dataclass, field


@dataclass
class CandidateDoc:
    """A documentation file that is a candidate for indexing.

    Attributes:
        repo: Repository name (e.g. ``kyma-project/istio``).
        path: File path relative to the repository root.
        h1: First H1 heading extracted from the document, or ``None``.
        excerpt: Short text excerpt from the document body.
        directory: Top-level directory component of the path.
        residue_reason: Free-text label explaining why this candidate was produced.
        content_hash: SHA-256 hex digest of the path string (used as a stable ID).
    """

    repo: str
    path: str
    h1: str | None
    excerpt: str
    directory: str
    residue_reason: str
    content_hash: str


@dataclass
class ClassificationResult:
    """The outcome of running a classifier on a single :class:`CandidateDoc`.

    Attributes:
        candidate: The document that was classified.
        decision: ``"include"``, ``"exclude"``, or ``"unsure"``.
        rationale: Human-readable explanation of the decision.
    """

    candidate: CandidateDoc
    decision: str
    rationale: str = field(default="")
