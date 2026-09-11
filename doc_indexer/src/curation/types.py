"""Shared data types for the doc-indexer curation pipeline.

Covers all phases (Phase 1 through Phase 3).  Types that are only used by
Phase 3 stubs are marked accordingly.
"""

from dataclasses import dataclass, field


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

    Written to ``curation/retrieval_eval_proposals.jsonl`` by
    :func:`~curation.eval_question_drafter.draft_eval_questions` (Phase 3 --
    issue #54).  A human reviewer accepts proposals into the live eval set at
    ``doc_indexer/evaluation/queries.jsonl``.

    Attributes:
        repo: GitHub repository slug this question was drafted for.
        path: Relative path within the repo of the source page.
        question: The natural-language retrieval question.
        expected_statement: A short statement that a correct retrieved chunk
            should support.
        drafted_by: How the proposal was created; always ``"agent"`` for
            LLM-drafted proposals.
    """

    repo: str
    path: str
    question: str
    expected_statement: str
    drafted_by: str = "agent"


@dataclass
class UsageStats:
    """Aggregated usage statistics from Langfuse.

    Produced by :func:`~curation.usage_stats.fetch_usage_stats` (Phase 3 --
    issue #55) and consumed by
    :func:`~curation.gap_report.generate_gap_report` (Phase 3 -- issue #56).

    Attributes:
        retrievals_per_page: Number of times each page URL was returned in a
            ``search_kyma_doc`` tool call.  Key is the canonical page URL.
        citations_per_page: Number of times each page URL was actually cited in
            the final agent reply.  Key is the canonical page URL.
        zero_hit_pages: Pages that are in the index but were never retrieved
            during the reporting period.  These are drop candidates.
    """

    retrievals_per_page: dict[str, int] = field(default_factory=dict)
    citations_per_page: dict[str, int] = field(default_factory=dict)
    zero_hit_pages: list[str] = field(default_factory=list)


@dataclass
class CuratorConfig:
    """Configuration passed to curator functions.

    Attributes:
        langfuse_host: Base URL of the Langfuse instance.
        langfuse_public_key: Public key for Langfuse API authentication.
        langfuse_secret_key: Secret key for Langfuse API authentication.
        eval_questions_per_page: Maximum number of eval questions to draft per
            changed page.
    """

    langfuse_host: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    eval_questions_per_page: int = 3
