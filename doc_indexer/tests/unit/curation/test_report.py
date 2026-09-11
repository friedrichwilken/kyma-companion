"""Unit tests for the curation report generator."""

import pytest
from curation.report import generate_pr_body
from curation.types import Candidate, ClassificationResult

pytestmark = pytest.mark.unit


def _make_result(
    decision: str,
    rationale: str,
    repo: str = "kyma-project/kyma",
    path: str = "docs/page.md",
    h1: str = "Page Title",
) -> ClassificationResult:
    return ClassificationResult(
        decision=decision,
        rationale=rationale,
        candidate=Candidate(repo=repo, path=path, h1=h1),
    )


class TestNeedsDecision:
    def test_unsure_items_appear_in_needs_a_decision(self):
        result = _make_result("unsure", "unclear scope", path="docs/foo.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=[])
        assert "## Needs a decision" in body
        assert "- [ ] `kyma-project/kyma::docs/foo.md`" in body
        assert "unclear scope" in body

    def test_unsure_item_uses_checkbox_format(self):
        result = _make_result("unsure", "some rationale", path="docs/bar.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=[])
        assert "- [ ] " in body

    def test_unsure_item_has_view_link_when_repo_url_given(self):
        result = _make_result("unsure", "rationale", path="docs/foo.md")
        body = generate_pr_body(
            [result],
            added_pages=[],
            removed_pages=[],
            repo_url="https://github.com/kyma-project/kyma",
        )
        assert "[View file](https://github.com/kyma-project/kyma/blob/HEAD/docs/foo.md)" in body

    def test_unsure_item_no_view_link_without_repo_url(self):
        result = _make_result("unsure", "rationale", path="docs/foo.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=[])
        assert "[View file]" not in body


class TestAddedPages:
    def test_include_items_appear_in_added_pages(self):
        result = _make_result("include", "very relevant", repo="kyma-project/kyma", path="docs/guide.md")
        body = generate_pr_body([result], added_pages=["docs/guide.md"], removed_pages=[])
        assert "## Added pages" in body
        assert "docs/guide.md" in body

    def test_added_pages_table_has_rationale(self):
        result = _make_result("include", "very relevant", path="docs/guide.md")
        body = generate_pr_body([result], added_pages=["docs/guide.md"], removed_pages=[])
        assert "very relevant" in body

    def test_added_pages_table_has_module(self):
        result = _make_result("include", "rationale", repo="my-repo", path="docs/guide.md")
        body = generate_pr_body([result], added_pages=["docs/guide.md"], removed_pages=[])
        assert "my-repo" in body

    def test_added_pages_link_generated_with_repo_url(self):
        result = _make_result("include", "rationale", path="docs/guide.md")
        body = generate_pr_body(
            [result],
            added_pages=["docs/guide.md"],
            removed_pages=[],
            repo_url="https://github.com/kyma-project/kyma",
        )
        assert "[docs/guide.md](https://github.com/kyma-project/kyma/blob/HEAD/docs/guide.md)" in body

    def test_added_pages_bare_path_without_repo_url(self):
        result = _make_result("include", "rationale", path="docs/guide.md")
        body = generate_pr_body([result], added_pages=["docs/guide.md"], removed_pages=[])
        # Should not contain a Markdown link
        assert "](http" not in body
        assert "docs/guide.md" in body


class TestRemovedPages:
    def test_exclude_items_appear_in_removed_pages(self):
        result = _make_result("exclude", "off-topic", path="docs/old.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=["docs/old.md"])
        assert "## Removed pages" in body
        assert "docs/old.md" in body

    def test_exclude_rationale_shown_in_removed_pages(self):
        result = _make_result("exclude", "deprecated content", path="docs/old.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=["docs/old.md"])
        assert "deprecated content" in body

    def test_removed_page_without_classification_still_listed(self):
        body = generate_pr_body([], added_pages=[], removed_pages=["docs/unclassified.md"])
        assert "## Removed pages" in body
        assert "docs/unclassified.md" in body


class TestUnclassified:
    def test_classifier_error_items_appear_in_unclassified(self):
        result = _make_result("exclude", "classifier error: timeout", path="docs/fail.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=[])
        assert "## Unclassified" in body
        assert "docs/fail.md" in body
        assert "classifier error: timeout" in body

    def test_classifier_error_not_in_removed_pages(self):
        result = _make_result("exclude", "classifier error: timeout", path="docs/fail.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=[])
        assert "## Removed pages" not in body


class TestEmptySections:
    def test_added_pages_section_omitted_when_no_added_pages(self):
        body = generate_pr_body([], added_pages=[], removed_pages=[])
        assert "## Added pages" not in body

    def test_removed_pages_section_omitted_when_no_removed_pages(self):
        body = generate_pr_body([], added_pages=[], removed_pages=[])
        assert "## Removed pages" not in body

    def test_needs_decision_section_omitted_when_no_unsure(self):
        result = _make_result("include", "rationale", path="docs/page.md")
        body = generate_pr_body([result], added_pages=["docs/page.md"], removed_pages=[])
        assert "## Needs a decision" not in body

    def test_unclassified_section_omitted_when_no_errors(self):
        result = _make_result("include", "rationale", path="docs/page.md")
        body = generate_pr_body([result], added_pages=["docs/page.md"], removed_pages=[])
        assert "## Unclassified" not in body

    def test_summary_always_present(self):
        body = generate_pr_body([], added_pages=[], removed_pages=[])
        assert "## Summary" in body


class TestLinks:
    def test_links_use_blob_head_format(self):
        result = _make_result("include", "rationale", path="docs/page.md")
        body = generate_pr_body(
            [result],
            added_pages=["docs/page.md"],
            removed_pages=[],
            repo_url="https://github.com/org/repo",
        )
        assert "/blob/HEAD/docs/page.md" in body

    def test_unsure_view_link_uses_blob_head_format(self):
        result = _make_result("unsure", "unclear", path="docs/foo.md")
        body = generate_pr_body(
            [result],
            added_pages=[],
            removed_pages=[],
            repo_url="https://github.com/org/repo",
        )
        assert "[View file](https://github.com/org/repo/blob/HEAD/docs/foo.md)" in body
