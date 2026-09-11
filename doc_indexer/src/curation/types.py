"""Shared data types for the doc-indexer curation pipeline.

Covers all phases (Phase 1 through Phase 3). Types that are only used by
Phase 3 stubs are marked accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Phase 1 types (issues #51-#53)
# ---------------------------------------------------------------------------


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
        content_hash: SHA-256 hex digest of the file content.
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
        doc_type: Optional document type label.
        module: Optional Kyma module name.
        confidence: Classifier confidence score between 0 and 1.
        rationale: Human-readable explanation of the decision.
        decided_by: How the decision was made; ``"agent"`` for LLM decisions.
    """

    candidate: CandidateDoc
    decision: Literal["include", "exclude", "unsure"]
    doc_type: str | None = None
    module: str | None = None
    confidence: float = 0.0
    rationale: str = ""
    decided_by: str = "agent"


@dataclass
class CuratorConfig:
    """Configuration passed to curator functions.

    Attributes:
        residue_to_agent: Whether to send residue to the LLM classifier.
        decisions_file: Path to the committed decisions cache JSONL file.
        model_name: LLM model name; ``None`` uses the default mini model.
        langfuse_host: Base URL of the Langfuse instance (Phase 3).
        langfuse_public_key: Public key for Langfuse API authentication (Phase 3).
        langfuse_secret_key: Secret key for Langfuse API authentication (Phase 3).
        eval_questions_per_page: Maximum number of eval questions to draft per
            changed page (Phase 3).
        floor_precision: Minimum acceptable precision (0-1) for the eval-classifier.
            Exits with code 1 when the measured precision falls below this value.
        floor_recall: Minimum acceptable recall (0-1) for the eval-classifier.
            Exits with code 1 when the measured recall falls below this value.
    """

    residue_to_agent: bool = False
    decisions_file: str = "curation/decisions.jsonl"
    model_name: str | None = None
    langfuse_host: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    eval_questions_per_page: int = 3
    floor_precision: float = 0.85
    floor_recall: float = 0.80


# ---------------------------------------------------------------------------
# Phase 3 types (issues #54-#56)
# ---------------------------------------------------------------------------


@dataclass
class ChangedPage:
    """A documentation page that was added or modified.

    Used by the curator to decide whether a page needs new eval questions
    drafted (Phase 3 -- issue #54).

    Attributes:
        repo: GitHub repository slug, e.g. ``kyma-project/kyma``.
        path: Relative path within the repo, e.g. ``docs/user/01-overview.md``.
        content_before: Full Markdown content before the change, or ``None`` for
            newly added pages.
        content_after: Full Markdown content after the change.
    """

    repo: str
    path: str
    content_before: str | None
    content_after: str


@dataclass
class EvalQuestionProposal:
    """A retrieval-eval question proposed by the agent for a changed page.

    Written to ``curation/retrieval_eval_proposals.jsonl`` (Phase 3 -- issue #54).

    Attributes:
        repo: GitHub repository slug this question was drafted for.
        path: Relative path within the repo of the source page.
        question: The natural-language retrieval question.
        expected_statement: A short statement that a correct retrieved chunk
            should support.
        drafted_by: How the proposal was created; always ``"agent"``.
    """

    repo: str
    path: str
    question: str
    expected_statement: str
    drafted_by: str = "agent"


@dataclass
class UsageStats:
    """Aggregated usage statistics from Langfuse (Phase 3 -- issue #55).

    Attributes:
        retrievals_per_page: Number of times each page URL was returned in a
            ``search_kyma_doc`` tool call.
        citations_per_page: Number of times each page URL was cited in the reply.
        zero_hit_pages: Pages in the index that were never retrieved.
    """

    retrievals_per_page: dict[str, int] = field(default_factory=dict)
    citations_per_page: dict[str, int] = field(default_factory=dict)
    zero_hit_pages: list[str] = field(default_factory=list)
