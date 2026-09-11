"""Unit tests for Phase 3 curation stubs (issues #54, #55, #56).

These tests verify that each stub raises ``NotImplementedError`` with a
message that explains why it is not yet implemented, so future implementers
know exactly what is needed.
"""

import asyncio

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def changed_page():
    from curation.types import ChangedPage

    return ChangedPage(
        repo="kyma-project/kyma",
        path="docs/user/01-overview.md",
        content_before=None,
        content_after="# Overview\n\nThis is a new page.",
    )


@pytest.fixture
def curator_config():
    from curation.types import CuratorConfig

    return CuratorConfig(
        langfuse_host="https://cloud.langfuse.com",
        langfuse_public_key="pk-test",
        langfuse_secret_key="sk-test",
    )


@pytest.fixture
def usage_stats():
    from curation.types import UsageStats

    return UsageStats(
        retrievals_per_page={"https://kyma-project.io/docs/page1": 5},
        citations_per_page={"https://kyma-project.io/docs/page1": 2},
        zero_hit_pages=["https://kyma-project.io/docs/page2"],
    )


# ---------------------------------------------------------------------------
# Issue #54 -- draft_eval_questions
# ---------------------------------------------------------------------------


def test_draft_eval_questions_raises(changed_page, curator_config):
    from curation.eval_question_drafter import draft_eval_questions

    with pytest.raises(NotImplementedError, match="Phase 3"):
        asyncio.run(draft_eval_questions([changed_page], curator_config))


def test_draft_eval_questions_raises_with_empty_list(curator_config):
    from curation.eval_question_drafter import draft_eval_questions

    with pytest.raises(NotImplementedError, match="Phase 3"):
        asyncio.run(draft_eval_questions([], curator_config))


# ---------------------------------------------------------------------------
# Issue #55 -- fetch_usage_stats
# ---------------------------------------------------------------------------


def test_fetch_usage_stats_raises():
    from curation.usage_stats import fetch_usage_stats

    with pytest.raises(NotImplementedError, match="Phase 3"):
        fetch_usage_stats(
            langfuse_host="https://cloud.langfuse.com",
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )


def test_fetch_usage_stats_raises_with_custom_days():
    from curation.usage_stats import fetch_usage_stats

    with pytest.raises(NotImplementedError, match="Phase 3"):
        fetch_usage_stats(
            langfuse_host="https://cloud.langfuse.com",
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
            days=7,
        )


# ---------------------------------------------------------------------------
# Issue #56 -- generate_gap_report
# ---------------------------------------------------------------------------


def test_generate_gap_report_raises(usage_stats):
    from curation.gap_report import generate_gap_report

    with pytest.raises(NotImplementedError, match="Phase 3"):
        generate_gap_report(usage_stats)


def test_generate_gap_report_raises_with_output_path(usage_stats, tmp_path):
    from curation.gap_report import generate_gap_report

    with pytest.raises(NotImplementedError, match="Phase 3"):
        generate_gap_report(usage_stats, output_path=str(tmp_path / "report.md"))


# ---------------------------------------------------------------------------
# Types round-trip
# ---------------------------------------------------------------------------


def test_changed_page_fields():
    from curation.types import ChangedPage

    page = ChangedPage(
        repo="kyma-project/kyma",
        path="docs/user/01-overview.md",
        content_before="# Old",
        content_after="# New",
    )
    assert page.repo == "kyma-project/kyma"
    assert page.path == "docs/user/01-overview.md"
    assert page.content_before == "# Old"
    assert page.content_after == "# New"


def test_eval_question_proposal_default_drafted_by():
    from curation.types import EvalQuestionProposal

    proposal = EvalQuestionProposal(
        repo="kyma-project/kyma",
        path="docs/user/01-overview.md",
        question="What is Kyma?",
        expected_statement="Kyma is an opinionated set of Kubernetes-based modular building blocks.",
    )
    assert proposal.drafted_by == "agent"


def test_usage_stats_default_fields():
    from curation.types import UsageStats

    stats = UsageStats()
    assert stats.retrievals_per_page == {}
    assert stats.citations_per_page == {}
    assert stats.zero_hit_pages == []


def test_curator_config_defaults():
    from curation.types import CuratorConfig

    cfg = CuratorConfig()
    assert cfg.eval_questions_per_page > 0
    assert cfg.langfuse_host == ""
