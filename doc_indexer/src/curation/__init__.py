"""Curation pipeline for the doc-indexer.

Exports the public surface of the curation package.

Phase 1 (issues #51-#53): classify residue, decisions cache, PR body.
Phase 3 functions (eval_question_drafter, usage_stats, gap_report) are
present as stubs and raise ``NotImplementedError`` until the required
infrastructure (Langfuse, page identity in tool output) is available.
"""

from curation.classifier import classify_residue
from curation.decisions_cache import DecisionsCache
from curation.eval_question_drafter import draft_eval_questions
from curation.gap_report import generate_gap_report
from curation.report import generate_pr_body
from curation.residue import find_residue
from curation.types import (
    CandidateDoc,
    ChangedPage,
    ClassificationResult,
    CuratorConfig,
    EvalQuestionProposal,
    UsageStats,
)
from curation.usage_stats import fetch_usage_stats

__all__ = [
    "CandidateDoc",
    "ChangedPage",
    "ClassificationResult",
    "CuratorConfig",
    "DecisionsCache",
    "EvalQuestionProposal",
    "UsageStats",
    "classify_residue",
    "draft_eval_questions",
    "fetch_usage_stats",
    "find_residue",
    "generate_gap_report",
    "generate_pr_body",
]
