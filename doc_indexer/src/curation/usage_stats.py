"""Query Langfuse for doc-retrieval usage statistics.

Phase 3 -- issue #55.  Not yet active.
"""

from curation.types import UsageStats


def fetch_usage_stats(
    langfuse_host: str,
    langfuse_public_key: str,
    langfuse_secret_key: str,
    days: int = 30,
) -> UsageStats:
    """Query Langfuse for search_kyma_doc traces and count retrievals/citations per page.

    Iterates over all ``search_kyma_doc`` tool spans created in the last
    *days* days.  For each span it counts how many times each canonical page
    URL appeared in the tool output (retrieval) and in the final agent reply
    (citation).  Pages that are present in the HANA index but were never
    retrieved are listed in ``UsageStats.zero_hit_pages`` as drop candidates.

    Zero-hit pages are surfaced in the curator PR description so that module
    docs owners can decide whether to remove or improve the content.

    Phase 3 -- not yet active.  Requires:

    - Page identity in the ``search_kyma_doc`` tool output (issue #65/#40).
    - A live Langfuse instance with production traces.

    Args:
        langfuse_host: Base URL of the Langfuse instance,
            e.g. ``https://cloud.langfuse.com``.
        langfuse_public_key: Public key for Langfuse API authentication.
        langfuse_secret_key: Secret key for Langfuse API authentication.
        days: How many calendar days of trace history to include.
            Defaults to ``30``.

    Returns:
        A :class:`~curation.types.UsageStats` dataclass with per-page
        retrieval counts, citation counts, and the zero-hit page list.

    Raises:
        NotImplementedError: Always -- this function is a Phase 3 stub.
    """
    # TODO(phase3, #55): Implement Langfuse query.
    #   Suggested approach:
    #   1. Authenticate against langfuse_host using langfuse_public_key /
    #      langfuse_secret_key (Basic Auth over HTTPS).
    #   2. Fetch all traces that contain a span named "search_kyma_doc" in the
    #      last *days* days using the Langfuse /api/public/traces endpoint
    #      (paginate with cursor).
    #   3. For each matching span parse the tool output to extract the list of
    #      returned page URLs (requires issue #65/#40 to surface page identity).
    #   4. Count occurrences per page URL -> retrievals_per_page.
    #   5. Walk the parent trace's final assistant message and count how many
    #      retrieved URLs appear in the reply text -> citations_per_page.
    #   6. Query the HANA index for all indexed page URLs and subtract the
    #      retrieved set -> zero_hit_pages.
    #   7. Return UsageStats(...).
    #
    # Blocked on: page identity in tool output (#65/#40), live Langfuse access.
    raise NotImplementedError("Phase 3: requires Langfuse access and page identity in tool output (#65/#40)")
