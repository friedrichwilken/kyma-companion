"""Curation pipeline for the doc-indexer.

Exports the public surface of the curation package.

Phase 3 functions (eval_question_drafter, usage_stats, gap_report) are
present as stubs and raise ``NotImplementedError`` until the required
infrastructure (Langfuse, page identity in tool output) is available.
"""

from curation.eval_question_drafter import draft_eval_questions
from curation.gap_report import generate_gap_report
from curation.types import (
    ChangedPage,
    CuratorConfig,
    EvalQuestionProposal,
    UsageStats,
)
from curation.usage_stats import fetch_usage_stats

__all__ = [
    "ChangedPage",
    "CuratorConfig",
    "EvalQuestionProposal",
    "UsageStats",
    "draft_eval_questions",
    "fetch_usage_stats",
    "generate_gap_report",
]
