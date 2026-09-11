"""Unit tests for curation.eval_classifier."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_classifier(decision: str):
    """Return a classifier function that always returns *decision*."""
    from curation.types import CandidateDoc, ClassificationResult

    def _fn(candidate: CandidateDoc) -> ClassificationResult:
        return ClassificationResult(candidate=candidate, decision=decision, rationale="mock")

    return _fn


def _write_labels(tmp_path: Path, records: list[dict]) -> str:
    """Write *records* as JSONL to a temp file and return the path string."""
    labels_file = tmp_path / "labels.jsonl"
    lines = [json.dumps(r) for r in records]
    labels_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(labels_file)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

INCLUDE_RECORD = {"repo": "kyma-project/istio", "path": "docs/user/01-overview.md", "decision": "include"}
EXCLUDE_RECORD = {"repo": "kyma-project/istio", "path": "CONTRIBUTING.md", "decision": "exclude"}
UNSURE_RECORD = {"repo": "kyma-project/istio", "path": "docs/user/maybe.md", "decision": "unsure"}


# ---------------------------------------------------------------------------
# Precision / recall computation tests
# ---------------------------------------------------------------------------


def test_all_true_positives(tmp_path):
    """Classifier predicts 'include' for all 'include' labels -- perfect recall/precision."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    labels = _write_labels(tmp_path, [INCLUDE_RECORD] * 5)
    result = run_eval(labels, _make_classifier("include"), CuratorConfig(floor_precision=0.0, floor_recall=0.0))

    assert result.precision == pytest.approx(1.0)
    assert result.recall == pytest.approx(1.0)
    assert result.confusion["tp"] == 5
    assert result.confusion["fp"] == 0
    assert result.confusion["fn"] == 0


def test_all_true_negatives(tmp_path):
    """Classifier predicts 'exclude' for all 'exclude' labels -- perfect specificity."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    labels = _write_labels(tmp_path, [EXCLUDE_RECORD] * 4)
    result = run_eval(labels, _make_classifier("exclude"), CuratorConfig(floor_precision=0.0, floor_recall=0.0))

    # No positives predicted => precision defaults to 1.0; no actual positives => recall defaults to 1.0
    assert result.precision == pytest.approx(1.0)
    assert result.recall == pytest.approx(1.0)
    assert result.confusion["tn"] == 4
    assert result.confusion["fp"] == 0


def test_false_positives_reduce_precision(tmp_path):
    """Including all docs when some should be excluded reduces precision."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    records = [INCLUDE_RECORD] * 3 + [EXCLUDE_RECORD] * 3
    labels = _write_labels(tmp_path, records)
    result = run_eval(labels, _make_classifier("include"), CuratorConfig(floor_precision=0.0, floor_recall=0.0))

    assert result.confusion["tp"] == 3
    assert result.confusion["fp"] == 3
    assert result.confusion["fn"] == 0
    assert result.precision == pytest.approx(3 / 6)
    assert result.recall == pytest.approx(1.0)


def test_false_negatives_reduce_recall(tmp_path):
    """Excluding all docs when some should be included reduces recall."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    records = [INCLUDE_RECORD] * 4 + [EXCLUDE_RECORD] * 2
    labels = _write_labels(tmp_path, records)
    result = run_eval(labels, _make_classifier("exclude"), CuratorConfig(floor_precision=0.0, floor_recall=0.0))

    assert result.confusion["fn"] == 4
    assert result.confusion["tn"] == 2
    assert result.recall == pytest.approx(0.0)
    # No positives predicted => precision defaults to 1.0
    assert result.precision == pytest.approx(1.0)


def test_mixed_predictions(tmp_path):
    """Mixed predictions produce expected TP/FP/FN/TN counts."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval
    from curation.types import CandidateDoc, ClassificationResult

    include_a = {"repo": "r", "path": "docs/user/a.md", "decision": "include"}
    include_b = {"repo": "r", "path": "docs/user/b.md", "decision": "include"}
    exclude_c = {"repo": "r", "path": "CONTRIBUTING.md", "decision": "exclude"}
    exclude_d = {"repo": "r", "path": ".github/workflows/ci.yaml", "decision": "exclude"}

    # classifier: include a, exclude b (FN), include c (FP), exclude d
    predictions = {
        "docs/user/a.md": "include",
        "docs/user/b.md": "exclude",
        "CONTRIBUTING.md": "include",
        ".github/workflows/ci.yaml": "exclude",
    }

    def _mixed(candidate: CandidateDoc) -> ClassificationResult:
        decision = predictions.get(candidate.path, "exclude")
        return ClassificationResult(candidate=candidate, decision=decision, rationale="mock")

    labels = _write_labels(tmp_path, [include_a, include_b, exclude_c, exclude_d])
    result = run_eval(labels, _mixed, CuratorConfig(floor_precision=0.0, floor_recall=0.0))

    assert result.confusion["tp"] == 1  # a
    assert result.confusion["fn"] == 1  # b
    assert result.confusion["fp"] == 1  # c
    assert result.confusion["tn"] == 1  # d
    assert result.precision == pytest.approx(1 / 2)
    assert result.recall == pytest.approx(1 / 2)
    assert result.f1 == pytest.approx(1 / 2)


def test_unsure_labels_are_skipped(tmp_path):
    """Lines with decision='unsure' must be skipped and not counted."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    records = [INCLUDE_RECORD, UNSURE_RECORD, EXCLUDE_RECORD]
    labels = _write_labels(tmp_path, records)
    result = run_eval(labels, _make_classifier("include"), CuratorConfig(floor_precision=0.0, floor_recall=0.0))

    assert result.n_labeled == 2  # only include + exclude counted
    assert result.n_tested == 2


def test_f1_is_harmonic_mean(tmp_path):
    """F1 = 2*P*R / (P+R) for non-trivial values."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    # Build a scenario: 4 include, 2 exclude.  Classifier includes all => P=4/6, R=1.0
    records = [INCLUDE_RECORD] * 4 + [EXCLUDE_RECORD] * 2
    labels = _write_labels(tmp_path, records)
    result = run_eval(labels, _make_classifier("include"), CuratorConfig(floor_precision=0.0, floor_recall=0.0))

    expected_p = 4 / 6
    expected_r = 1.0
    expected_f1 = 2 * expected_p * expected_r / (expected_p + expected_r)
    assert result.f1 == pytest.approx(expected_f1)


# ---------------------------------------------------------------------------
# Floor enforcement tests
# ---------------------------------------------------------------------------


def test_floor_precision_triggers_exit(tmp_path):
    """sys.exit(1) is raised when precision is below the configured floor."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    # Classifier includes everything including excludes => low precision
    records = [INCLUDE_RECORD] * 1 + [EXCLUDE_RECORD] * 9
    labels = _write_labels(tmp_path, records)

    with pytest.raises(SystemExit) as exc_info:
        run_eval(labels, _make_classifier("include"), CuratorConfig(floor_precision=0.85, floor_recall=0.0))
    assert exc_info.value.code == 1


def test_floor_recall_triggers_exit(tmp_path):
    """sys.exit(1) is raised when recall is below the configured floor."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    # Classifier excludes everything including includes => zero recall
    records = [INCLUDE_RECORD] * 9 + [EXCLUDE_RECORD] * 1
    labels = _write_labels(tmp_path, records)

    with pytest.raises(SystemExit) as exc_info:
        run_eval(labels, _make_classifier("exclude"), CuratorConfig(floor_precision=0.0, floor_recall=0.80))
    assert exc_info.value.code == 1


def test_both_floors_pass_no_exit(tmp_path):
    """No SystemExit when both precision and recall exceed their floors."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    records = [INCLUDE_RECORD] * 9 + [EXCLUDE_RECORD] * 1
    labels = _write_labels(tmp_path, records)

    # Perfect classifier; should not exit.
    result = run_eval(
        labels,
        _make_classifier("include"),  # all included = TP for includes, FP for the 1 exclude
        CuratorConfig(floor_precision=0.5, floor_recall=0.8),
    )
    # precision = 9/10 = 0.9 >= 0.5, recall = 1.0 >= 0.8 -- should not raise
    assert result.precision >= 0.5
    assert result.recall >= 0.8


def test_floor_exit_code_is_one(tmp_path):
    """The exit code is exactly 1, not some other truthy integer."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    records = [EXCLUDE_RECORD] * 5
    labels = _write_labels(tmp_path, records)

    # All predicted 'include', all labeled 'exclude' => precision = 0
    with pytest.raises(SystemExit) as exc_info:
        run_eval(labels, _make_classifier("include"), CuratorConfig(floor_precision=0.85, floor_recall=0.0))
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_labels_file(tmp_path):
    """An empty file returns zero metrics without crashing."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    labels = str(tmp_path / "empty.jsonl")
    Path(labels).write_text("", encoding="utf-8")
    result = run_eval(labels, _make_classifier("include"), CuratorConfig(floor_precision=0.0, floor_recall=0.0))

    assert result.n_labeled == 0
    assert result.n_tested == 0
    # Both safe-divisions return 1.0 when denominators are zero
    assert result.precision == pytest.approx(1.0)
    assert result.recall == pytest.approx(1.0)


def test_malformed_json_lines_are_skipped(tmp_path):
    """Lines that are not valid JSON are skipped without raising an exception."""
    from curation.config import CuratorConfig
    from curation.eval_classifier import run_eval

    labels_file = tmp_path / "bad.jsonl"
    labels_file.write_text(
        json.dumps(INCLUDE_RECORD) + "\nNOT VALID JSON\n" + json.dumps(INCLUDE_RECORD) + "\n",
        encoding="utf-8",
    )
    result = run_eval(
        str(labels_file), _make_classifier("include"), CuratorConfig(floor_precision=0.0, floor_recall=0.0)
    )
    assert result.n_tested == 2


def test_candidate_built_with_correct_fields(tmp_path):
    """_build_candidate populates directory and content_hash correctly."""
    import hashlib

    from curation.eval_classifier import _build_candidate

    candidate = _build_candidate("kyma-project/istio", "docs/user/01-overview.md")
    assert candidate.directory == "docs"
    assert candidate.content_hash == hashlib.sha256(b"docs/user/01-overview.md").hexdigest()
    assert candidate.h1 is None
    assert candidate.excerpt == ""
    assert candidate.residue_reason == "labeled"
