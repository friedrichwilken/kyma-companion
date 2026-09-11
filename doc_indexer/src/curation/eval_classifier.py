"""Classifier evaluation against a labeled JSONL dataset.

Usage::

    from curation.eval_classifier import run_eval
    from curation.config import CuratorConfig

    result = run_eval("curation/labels.jsonl", my_classifier_fn, CuratorConfig())

The labeled file must be a JSONL file where each line contains at least the
fields ``repo``, ``path``, and ``decision`` (``"include"``, ``"exclude"``, or
``"unsure"``).  Lines with ``"unsure"`` are silently skipped.

``classifier_fn`` must accept a single :class:`~curation.types.CandidateDoc`
and return a :class:`~curation.types.ClassificationResult`.
"""

import hashlib
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

from curation.config import CuratorConfig
from curation.types import CandidateDoc, ClassificationResult

from utils.logging import get_logger

logger = get_logger(__name__)

DECISION_INCLUDE = "include"
DECISION_EXCLUDE = "exclude"
DECISION_UNSURE = "unsure"

MIN_DENOMINATOR = 1  # avoid division by zero


@dataclass
class EvalResult:
    """Metrics from a single evaluation run.

    Attributes:
        precision: TP / (TP + FP).  1.0 when there are no false positives.
        recall: TP / (TP + FN).  1.0 when there are no false negatives.
        f1: Harmonic mean of precision and recall.
        n_labeled: Total number of labeled examples (excluding *unsure*).
        n_tested: Number of examples the classifier was called on.
        confusion: Raw confusion counts: ``tp``, ``fp``, ``fn``, ``tn``.
    """

    precision: float
    recall: float
    f1: float
    n_labeled: int
    n_tested: int
    confusion: dict[str, int] = field(default_factory=dict)


def _build_candidate(repo: str, path: str) -> CandidateDoc:
    """Build a minimal :class:`CandidateDoc` from a label entry.

    Args:
        repo: Repository name from the label record.
        path: File path from the label record.

    Returns:
        A :class:`CandidateDoc` with fields populated from the path.
    """
    content_hash = hashlib.sha256(path.encode()).hexdigest()
    directory = path.split("/")[0] if "/" in path else path
    return CandidateDoc(
        repo=repo,
        path=path,
        h1=None,
        excerpt="",
        directory=directory,
        residue_reason="labeled",
        content_hash=content_hash,
    )


def _safe_precision(tp: int, fp: int) -> float:
    """Compute precision, returning 1.0 when the denominator is zero.

    Args:
        tp: True positive count.
        fp: False positive count.

    Returns:
        Precision as a float in [0, 1].
    """
    denom = tp + fp
    if denom < MIN_DENOMINATOR:
        return 1.0
    return tp / denom


def _safe_recall(tp: int, fn: int) -> float:
    """Compute recall, returning 1.0 when the denominator is zero.

    Args:
        tp: True positive count.
        fn: False negative count.

    Returns:
        Recall as a float in [0, 1].
    """
    denom = tp + fn
    if denom < MIN_DENOMINATOR:
        return 1.0
    return tp / denom


def _safe_f1(precision: float, recall: float) -> float:
    """Compute the F1 score, returning 0.0 when both precision and recall are zero.

    Args:
        precision: Precision value in [0, 1].
        recall: Recall value in [0, 1].

    Returns:
        F1 score as a float in [0, 1].
    """
    denom = precision + recall
    if denom == 0.0:
        return 0.0
    return 2 * precision * recall / denom


def _print_markdown_table(result: EvalResult) -> None:
    """Print a Markdown summary table to stdout.

    Args:
        result: Populated :class:`EvalResult` to summarise.
    """
    c = result.confusion
    lines = [
        "| Metric        | Value  |",
        "|---------------|--------|",
        f"| Precision     | {result.precision:.4f} |",
        f"| Recall        | {result.recall:.4f} |",
        f"| F1            | {result.f1:.4f} |",
        f"| N labeled     | {result.n_labeled} |",
        f"| N tested      | {result.n_tested} |",
        f"| TP            | {c.get('tp', 0)} |",
        f"| FP            | {c.get('fp', 0)} |",
        f"| FN            | {c.get('fn', 0)} |",
        f"| TN            | {c.get('tn', 0)} |",
    ]
    print("\n".join(lines))  # noqa: T201


def _classify_record(
    record: dict,
    line_no: int,
    labels_path: str,
    classifier_fn: Callable[[CandidateDoc], ClassificationResult],
) -> tuple[str, str] | None:
    """Parse a single label record and call the classifier.

    Args:
        record: Parsed JSON object from the labels file.
        line_no: 1-based line number (used in warning messages).
        labels_path: Path to the labels file (used in warning messages).
        classifier_fn: Classifier to call on the candidate.

    Returns:
        A ``(label_decision, predicted_decision)`` tuple, or ``None`` if the
        record should be skipped (``"unsure"`` decision or missing fields).
    """
    label_decision: str = record.get("decision", "").lower()
    if label_decision == DECISION_UNSURE:
        return None

    repo: str = record.get("repo", "")
    path: str = record.get("path", "")
    if not repo or not path:
        logger.warning(f"Skipping line {line_no}: missing 'repo' or 'path' field in {labels_path}")
        return None

    candidate = _build_candidate(repo, path)
    result = classifier_fn(candidate)
    return label_decision, result.decision.lower()


def _count_from_labels(
    labels_path: str,
    classifier_fn: Callable[[CandidateDoc], ClassificationResult],
) -> tuple[int, int, int, int, int, int]:
    """Read the labels file and return raw confusion counts and skipped total.

    Args:
        labels_path: Path to the ``.jsonl`` labels file.
        classifier_fn: Classifier to call on each candidate.

    Returns:
        A tuple ``(tp, fp, fn, tn, n_tested, skipped_unsure)``.
    """
    import json as _json

    tp = fp = fn = tn = skipped = n_tested = 0

    with open(labels_path, encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = _json.loads(line)
            except _json.JSONDecodeError:
                logger.warning(f"Skipping malformed JSON on line {line_no} of {labels_path}")
                continue

            outcome = _classify_record(record, line_no, labels_path, classifier_fn)
            if outcome is None:
                if record.get("decision", "").lower() == DECISION_UNSURE:
                    skipped += 1
                continue

            label_decision, predicted = outcome
            n_tested += 1
            label_positive = label_decision == DECISION_INCLUDE
            pred_positive = predicted == DECISION_INCLUDE

            if label_positive and pred_positive:
                tp += 1
            elif not label_positive and pred_positive:
                fp += 1
            elif label_positive and not pred_positive:
                fn += 1
            else:
                tn += 1

    return tp, fp, fn, tn, n_tested, skipped


def _check_floors(precision: float, recall: float, config: CuratorConfig) -> bool:
    """Log errors for any metric below its quality floor.

    Args:
        precision: Measured precision.
        recall: Measured recall.
        config: Config holding floor thresholds.

    Returns:
        ``True`` if any floor was violated, ``False`` otherwise.
    """
    failed = False
    if precision < config.floor_precision:
        logger.error(
            f"Precision {precision:.4f} is below the floor {config.floor_precision:.4f}. "
            "Improve the classifier or lower the floor threshold."
        )
        failed = True
    if recall < config.floor_recall:
        logger.error(
            f"Recall {recall:.4f} is below the floor {config.floor_recall:.4f}. "
            "Improve the classifier or lower the floor threshold."
        )
        failed = True
    return failed


def run_eval(
    labels_path: str,
    classifier_fn: Callable[[CandidateDoc], ClassificationResult],
    config: CuratorConfig,
) -> EvalResult:
    """Evaluate *classifier_fn* against the labeled dataset at *labels_path*.

    Reads the JSONL file, builds :class:`CandidateDoc` instances, calls
    ``classifier_fn`` for each, computes precision/recall/F1, and prints a
    Markdown summary table.  Exits the process with code 1 if precision falls
    below ``config.floor_precision`` or recall falls below
    ``config.floor_recall``.

    Args:
        labels_path: Path to the ``.jsonl`` file with labeled examples.
        classifier_fn: A callable that accepts a :class:`CandidateDoc` and
            returns a :class:`ClassificationResult`.
        config: :class:`CuratorConfig` that carries quality-floor thresholds.

    Returns:
        An :class:`EvalResult` with the computed metrics and confusion counts.
    """
    tp, fp, fn, tn, n_tested, skipped = _count_from_labels(labels_path, classifier_fn)

    n_labeled = tp + fp + fn + tn
    precision = _safe_precision(tp, fp)
    recall = _safe_recall(tp, fn)
    f1 = _safe_f1(precision, recall)

    eval_result = EvalResult(
        precision=precision,
        recall=recall,
        f1=f1,
        n_labeled=n_labeled,
        n_tested=n_tested,
        confusion={"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    )

    logger.info(
        "Eval complete",
        extra={
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "n_labeled": n_labeled,
            "n_tested": n_tested,
            "skipped_unsure": skipped,
        },
    )
    _print_markdown_table(eval_result)

    if _check_floors(precision, recall, config):
        sys.exit(1)

    return eval_result
