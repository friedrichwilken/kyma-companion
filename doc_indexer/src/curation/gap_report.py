"""Generate the monthly docs-gap Markdown report.

Phase 3 -- issue #56.  Not yet active.
"""

from curation.types import UsageStats


def generate_gap_report(
    usage_stats: UsageStats,
    output_path: str | None = None,
) -> str:
    """Generate a monthly Markdown report of query themes with no retrieved or cited page.

    Reads zero-hit pages and low-citation pages from *usage_stats* and
    produces a structured Markdown document grouped by Kyma module.  The
    report is intended to be attached to a tracking GitHub issue or posted to
    the module docs teams' Slack channel.

    Section structure (per module):

    - **Never retrieved** -- pages in the index that appeared zero times in
      ``search_kyma_doc`` calls during the reporting period.
    - **Rarely cited** -- pages that were retrieved but never (or rarely)
      appeared in the final agent reply, indicating retrieval noise.

    Phase 3 -- not yet active.  Requires:

    - :func:`~curation.usage_stats.fetch_usage_stats` to be implemented
      (issue #55).

    Args:
        usage_stats: Aggregated usage statistics from Langfuse, produced by
            :func:`~curation.usage_stats.fetch_usage_stats`.
        output_path: Optional file path to write the Markdown report to.  When
            ``None`` the report is returned as a string only and not written to
            disk.

    Returns:
        The Markdown report as a string.

    Raises:
        NotImplementedError: Always -- this function is a Phase 3 stub.
    """
    # TODO(phase3, #56): Implement Markdown report generation.
    #   Suggested approach:
    #   1. Group zero_hit_pages by module (parse the URL or path prefix).
    #   2. Group low-citation pages: pages where citations_per_page[url] == 0
    #      but retrievals_per_page[url] > 0.
    #   3. Build a Markdown document with one H2 section per module.
    #      Each section has two sub-lists: "Never retrieved" and "Rarely cited".
    #   4. Add a summary table at the top: module | zero-hit | rarely-cited.
    #   5. If output_path is not None, write the report to that file.
    #   6. Return the report string.
    #
    # Blocked on: fetch_usage_stats (#55).
    raise NotImplementedError("Phase 3: requires Langfuse usage stats (#55)")
