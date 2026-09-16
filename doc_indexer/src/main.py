import argparse
import json
import os
import sys
import time

from curation.classifier import classify_residue
from curation.decisions_cache import DecisionsCache
from curation.report import generate_pr_body
from curation.residue import find_residue
from curation.types import ClassificationResult, CuratorConfig
from fetcher.fetcher import DocumentsFetcher
from hdbcli import dbapi
from indexing.adaptive_indexer import AdaptiveSplitMarkdownIndexer
from langchain_core.embeddings import Embeddings
from utils.hana import create_hana_connection, drop_table, list_tables

from utils.logging import get_logger
from utils.models import (
    create_embedding_factory,
    openai_embedding_creator,
)
from utils.settings import (
    CURATOR_DECISIONS_FILE,
    CURATOR_MODEL_NAME,
    CURATOR_RESIDUE_TO_AGENT,
    DATABASE_PASSWORD,
    DATABASE_PORT,
    DATABASE_URL,
    DATABASE_USER,
    DOCS_PATH,
    DOCS_SOURCES_FILE_PATH,
    DOCS_TABLE_NAME,
    EMBEDDING_MODEL_NAME,
    TMP_DIR,
    get_embedding_model_config,
)

TASK_FETCH = "fetch"
TASK_INDEX = "index"
TASK_DROP = "drop"
TASK_TABLES = "tables"
TASK_CURATE = "curate"
TASK_REPORT = "report"
TASK_EVAL_CLASSIFIER = "eval-classifier"
logger = get_logger(__name__)


def run_fetcher() -> None:
    """Entry function to run the document fetcher."""
    logger.info("Starting fetch task")
    start = time.monotonic()
    fetcher = DocumentsFetcher(
        source_file=DOCS_SOURCES_FILE_PATH,
        output_dir=DOCS_PATH,
        tmp_dir=TMP_DIR,
    )
    fetcher.run()
    logger.info(f"Fetch completed in {time.monotonic() - start:.1f}s")
    for root, _dirs, files in os.walk(DOCS_PATH):
        level = root.replace(DOCS_PATH, "").count(os.sep)
        indent = "  " * level
        logger.info(f"{indent}{os.path.basename(root)}/")
        for fname in files:
            logger.info(f"{indent}  {fname}")


def run_indexer(
    embeddings_model: Embeddings | None = None,
    hana_conn: dbapi.Connection | None = None,
    docs_path: str = DOCS_PATH,
    table_name: str = DOCS_TABLE_NAME,
) -> None:
    """Entry function to run the indexer.

    Args:
        embeddings_model: Embedding model to use. If None, created from config.
        hana_conn: Hana DB connection to use. If None, created from config.
        docs_path: Path to the documents to index. Defaults to DOCS_PATH from config.
        table_name: Name of the table to index into. Defaults to DOCS_TABLE_NAME from config.
    """
    logger.info("Starting index task")
    start = time.monotonic()

    if embeddings_model is None:
        embedding_model = get_embedding_model_config(EMBEDDING_MODEL_NAME)
        create_embedding = create_embedding_factory(openai_embedding_creator)
        embeddings_model = create_embedding(embedding_model.name)

    if hana_conn is None:
        hana_conn = create_hana_connection(DATABASE_URL, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWORD)
        if not hana_conn:
            logger.error("Failed to connect to the database. Exiting.")
            raise RuntimeError("Failed to connect to the database.")

    indexer = AdaptiveSplitMarkdownIndexer(docs_path, embeddings_model, hana_conn, table_name)
    indexer.index()
    logger.info(f"Index completed in {time.monotonic() - start:.1f}s")


def run_drop(
    hana_conn: dbapi.Connection | None = None,
    table_name: str = DOCS_TABLE_NAME,
) -> None:
    """Entry function to drop the HANA table created by the indexer.

    Args:
        hana_conn: Hana DB connection to use. If None, created from config.
        table_name: Name of the table to drop. Defaults to DOCS_TABLE_NAME from config.
    """
    logger.info("Starting drop task", extra={"table": table_name})
    if hana_conn is None:
        hana_conn = create_hana_connection(DATABASE_URL, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWORD)
        if not hana_conn:
            logger.error("Failed to connect to the database. Exiting.")
            raise RuntimeError("Failed to connect to the database.")

    drop_table(hana_conn, DATABASE_USER, table_name)


def run_list_tables(
    hana_conn: dbapi.Connection | None = None,
) -> None:
    """Entry function to list all HANA tables owned by the configured user.

    Args:
        hana_conn: Hana DB connection to use. If None, created from config.
    """
    if hana_conn is None:
        hana_conn = create_hana_connection(DATABASE_URL, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWORD)
        if not hana_conn:
            logger.error("Failed to connect to the database. Exiting.")
            raise RuntimeError("Failed to connect to the database.")

    rows = list_tables(hana_conn, DATABASE_USER)
    if not rows:
        logger.info("No tables found.")
        return
    header = f"{'TABLE_NAME':<60} {'ROWS':>10} {'SIZE (bytes)':>14}"
    separator = "-" * 88
    logger.info(f"HANA tables:\n{header}\n{separator}")
    for name, records, size in rows:
        logger.info(f"{name:<60} {records:>10} {size:>14}")
    logger.info(f"{len(rows)} table(s) total.")


def run_curator(
    docs_path: str = DOCS_PATH,
    sources_file: str = DOCS_SOURCES_FILE_PATH,
    residue_to_agent: bool = CURATOR_RESIDUE_TO_AGENT,
    decisions_file: str = CURATOR_DECISIONS_FILE,
    model_name: str | None = CURATOR_MODEL_NAME,
) -> None:
    """Entry function to curate residue documentation files.

    Walks *docs_path* for .md files that fall outside the configured
    ``include_files`` patterns, checks a persistent decisions cache, and
    optionally classifies uncached files using an LLM agent.

    Prints a summary to the logger on completion.

    Args:
        docs_path: Root directory containing per-module sub-directories.
        sources_file: Path to the docs_sources.json file.
        residue_to_agent: When True, send uncached residue to the LLM classifier.
        decisions_file: Path to the JSONL decisions cache file.
        model_name: SAP AI Core model name override (None = use SDK default).
    """
    logger.info("Starting curate task")

    # 1. Load docs sources
    try:
        with open(sources_file, encoding="utf-8") as f:
            sources = json.load(f)
    except FileNotFoundError:
        logger.error(f"Sources file not found: {sources_file}")
        raise
    except Exception:
        logger.exception(f"Failed to read sources file: {sources_file}")
        raise

    # 2. Find residue
    candidates = find_residue(docs_path, sources)
    total_residue = len(candidates)

    # 3. Load decisions cache
    cache = DecisionsCache(decisions_file)
    cache.load()

    # 4. Filter out already-cached candidates
    uncached = [c for c in candidates if not cache.is_cached(c)]
    cached_count = total_residue - len(uncached)

    # 5. Classify uncached candidates if enabled
    new_results = []
    if residue_to_agent and uncached:
        cfg = CuratorConfig(
            residue_to_agent=True,
            decisions_file=decisions_file,
            model_name=model_name,
        )
        new_results = classify_residue(uncached, cfg)
        cache.save(new_results)

    # 6. Print summary
    include_count = sum(1 for r in new_results if r.decision == "include")
    exclude_count = sum(1 for r in new_results if r.decision == "exclude")
    unsure_count = sum(1 for r in new_results if r.decision == "unsure")
    unclassified_count = len(uncached) - len(new_results)

    col_w = 40
    val_w = 10
    header = f"{'METRIC':<{col_w}} {'VALUE':>{val_w}}"
    separator = "-" * (col_w + val_w + 1)

    def _row(label: str, value: int | str) -> str:
        return f"{label:<{col_w}} {str(value):>{val_w}}"

    lines = ["Curate summary", header, separator]
    lines.append(_row("Total residue files", total_residue))
    lines.append(_row("Cached (skipped)", cached_count))
    lines.append(_row("Newly classified", len(new_results)))
    lines.append(_row("  include", include_count))
    lines.append(_row("  exclude", exclude_count))
    lines.append(_row("  unsure", unsure_count))
    if unclassified_count or not residue_to_agent:
        label = "  unclassified (agent disabled)" if not residue_to_agent else "  unclassified"
        lines.append(_row(label, unclassified_count))

    logger.info("\n".join(lines))


def run_report(
    decisions_file: str = "curation/decisions.jsonl",
    out_file: str | None = None,
    repo_url: str = "",
) -> None:
    """Generate a Markdown PR body from curation decisions.

    Reads classification results from a JSONL file and writes a Markdown PR
    body to stdout or a file.

    Args:
        decisions_file: Path to the JSONL file with classification results.
        out_file: If set, write the Markdown to this file path instead of stdout.
        repo_url: Base URL for generating file links in the report.
    """
    # Read classification results
    cache = DecisionsCache(decisions_file)
    results: list[ClassificationResult] = cache.results()

    # added_pages / removed_pages represent the diff vs a previous snapshot.
    # docs_sources.json contains include_files glob patterns, not resolved file
    # paths, so we cannot reconstruct a reliable baseline from it here.
    # Pass empty lists; callers that track snapshots across runs can supply them
    # via a future --added-pages / --removed-pages flag.
    added_pages: list[str] = []
    removed_pages: list[str] = []

    body = generate_pr_body(results, added_pages, removed_pages, repo_url=repo_url)

    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(body)
        logger.info(f"PR body written to {out_file}")
    else:
        sys.stdout.write(body)


def run_eval_classifier(
    labels_path: str = "curation/labels.jsonl",
    floor_precision: float = 0.85,
    floor_recall: float = 0.80,
) -> None:
    """Entry function to evaluate the classifier against the labeled dataset.

    Reads the JSONL labels file, runs every labeled candidate through a
    stub classifier (always-include), and reports precision/recall/F1.
    Exits with code 1 if either metric is below the configured floor.

    Args:
        labels_path: Path to the JSONL labels file.
        floor_precision: Minimum acceptable precision (quality floor).
        floor_recall: Minimum acceptable recall (quality floor).
    """
    from curation.eval_classifier import run_eval
    from curation.types import CandidateDoc

    logger.info(
        "Starting eval-classifier task",
        extra={"labels_path": labels_path, "floor_precision": floor_precision, "floor_recall": floor_recall},
    )

    def _stub_classifier(candidate: CandidateDoc) -> ClassificationResult:
        """Stub classifier: always predicts 'include'."""
        return ClassificationResult(candidate=candidate, decision="include", rationale="stub: always include")

    cfg = CuratorConfig(floor_precision=floor_precision, floor_recall=floor_recall)
    run_eval(labels_path, _stub_classifier, cfg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kyma Documentation Fetcher and Indexer.")
    subparsers = parser.add_subparsers(dest="task")

    subparsers.add_parser(TASK_FETCH, help="Fetch documents from configured sources.")
    subparsers.add_parser(TASK_INDEX, help="Index fetched documents into HANA.")
    subparsers.add_parser(TASK_DROP, help="Drop the HANA documentation table.")
    subparsers.add_parser(TASK_TABLES, help="List all HANA tables owned by the configured user.")
    subparsers.add_parser(TASK_CURATE, help="Detect and classify residue documentation files.")

    report_parser = subparsers.add_parser(TASK_REPORT, help="Generate a Markdown PR body from curation decisions.")
    report_parser.add_argument(
        "--decisions",
        default="curation/decisions.jsonl",
        help="Path to the JSONL file with classification results (default: curation/decisions.jsonl).",
    )
    report_parser.add_argument("--out", default=None, help="Write the Markdown to this file path instead of stdout.")
    report_parser.add_argument("--repo-url", default="", help="Base repository URL for generating file links.")

    eval_parser = subparsers.add_parser(TASK_EVAL_CLASSIFIER, help="Evaluate classifier against labeled dataset.")
    eval_parser.add_argument(
        "--labels",
        default="curation/labels.jsonl",
        help="Path to the JSONL labels file (default: curation/labels.jsonl).",
    )
    eval_parser.add_argument(
        "--floor-precision", type=float, default=0.85, help="Minimum acceptable precision (default: 0.85)."
    )
    eval_parser.add_argument(
        "--floor-recall", type=float, default=0.80, help="Minimum acceptable recall (default: 0.80)."
    )

    args = parser.parse_args()
    if args.task is None:
        parser.print_help()
        sys.exit(1)

    logger.info("Indexer job starting", extra={"task": args.task})

    if args.task == TASK_FETCH:
        run_fetcher()
    elif args.task == TASK_INDEX:
        run_indexer()
    elif args.task == TASK_DROP:
        run_drop()
    elif args.task == TASK_TABLES:
        run_list_tables()
    elif args.task == TASK_CURATE:
        run_curator()
    elif args.task == TASK_REPORT:
        run_report(decisions_file=args.decisions, out_file=args.out, repo_url=args.repo_url)
    elif args.task == TASK_EVAL_CLASSIFIER:
        run_eval_classifier(
            labels_path=args.labels, floor_precision=args.floor_precision, floor_recall=args.floor_recall
        )
