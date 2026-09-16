"""Unit tests for the curation report generator."""

import pytest
from curation.report import generate_pr_body
from curation.types import CandidateDoc, ClassificationResult

pytestmark = pytest.mark.unit


def _make_result(
    decision: str,
    rationale: str,
    repo: str = "kyma-project/kyma",
    path: str = "docs/page.md",
    h1: str = "Page Title",
) -> ClassificationResult:
    candidate = CandidateDoc(
        repo=repo,
        path=path,
        h1=h1,
        excerpt="",
        directory="docs",
        residue_reason="test",
        content_hash="abc123",
    )
    return ClassificationResult(
        decision=decision,  # type: ignore[arg-type]
        rationale=rationale,
        candidate=candidate,
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
        # View link must be on its own indented line, not appended to the checkbox line
        assert "\n  [View file](" in body

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

    def test_classifier_error_exact_line_format(self):
        result = _make_result("exclude", "classifier error: timeout", path="docs/fail.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=[])
        assert "- `kyma-project/kyma::docs/fail.md`: classifier error: timeout" in body

    def test_classifier_error_not_in_removed_pages_when_removed_pages_empty(self):
        result = _make_result("exclude", "classifier error: timeout", path="docs/fail.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=[])
        assert "## Removed pages" not in body

    def test_classifier_error_path_in_removed_pages_shows_page_without_rationale(self):
        # When the failed path is also listed in removed_pages, it should appear in
        # "Removed pages" without a rationale (the error item is excluded from `excluded`).
        result = _make_result("exclude", "classifier error: timeout", path="docs/fail.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=["docs/fail.md"])
        assert "## Removed pages" in body
        assert "docs/fail.md" in body
        # The error rationale must not leak into "Removed pages"
        assert "classifier error" not in body.split("## Removed pages")[1].split("##")[0]

    def test_unsure_with_classifier_error_rationale_goes_to_unclassified_not_needs_decision(self):
        # Edge case: decision="unsure" but rationale is a classifier error.
        # Should appear in Unclassified, not Needs a decision.
        result = _make_result("unsure", "classifier error: unexpected response", path="docs/edge.md")
        body = generate_pr_body([result], added_pages=[], removed_pages=[])
        assert "## Unclassified" in body
        assert "## Needs a decision" not in body


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

    def test_summary_no_changes_when_empty(self):
        body = generate_pr_body([], added_pages=[], removed_pages=[])
        assert "No changes." in body

    def test_summary_singular_counts(self):
        result = _make_result("unsure", "rationale", path="docs/foo.md")
        body = generate_pr_body([result], added_pages=["docs/added.md"], removed_pages=["docs/removed.md"])
        assert "1 page added" in body
        assert "1 page removed" in body
        assert "1 item needs a decision" in body

    def test_summary_plural_counts(self):
        unsure1 = _make_result("unsure", "rationale", path="docs/a.md")
        unsure2 = _make_result("unsure", "rationale", path="docs/b.md")
        body = generate_pr_body(
            [unsure1, unsure2],
            added_pages=["docs/c.md", "docs/d.md"],
            removed_pages=["docs/e.md", "docs/f.md"],
        )
        assert "2 pages added" in body
        assert "2 pages removed" in body
        assert "2 items need a decision" in body


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
