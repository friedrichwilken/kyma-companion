"""Draft retrieval-eval questions for added or substantially changed pages.

Phase 3 -- issue #54.  Not yet active.
"""

from curation.types import ChangedPage, CuratorConfig, EvalQuestionProposal


async def draft_eval_questions(
    changed_pages: list[ChangedPage],
    config: CuratorConfig,
) -> list[EvalQuestionProposal]:
    """Draft retrieval-eval questions for added or substantially changed pages.

    For each page in *changed_pages* the function calls an LLM to propose
    ``config.eval_questions_per_page`` natural-language questions whose answer
    relies on content in that page.  Proposals are returned as a list and the
    caller is responsible for writing them to
    ``curation/retrieval_eval_proposals.jsonl``.

    The reviewer then accepts proposals into the live retrieval eval set at
    ``doc_indexer/evaluation/queries.jsonl``.

    Phase 3 -- not yet active.  Requires:

    - Live Langfuse instance to identify frequently-queried pages (issue #55).
    - LLM access via the curator agent (issue #53).

    Args:
        changed_pages: Pages that were added or substantially changed in the
            latest curator run.  Only pages where ``content_after`` is
            non-empty are processed.
        config: Curator configuration, including Langfuse credentials and the
            number of questions to draft per page.

    Returns:
        A list of :class:`~curation.types.EvalQuestionProposal` objects, one
        per drafted question.

    Raises:
        NotImplementedError: Always -- this function is a Phase 3 stub.
    """
    # TODO(phase3, #54): Call the curator LLM for each page in changed_pages.
    #   Suggested approach:
    #   1. Filter changed_pages to those with substantial content changes
    #      (e.g. >10 % diff by line count or content_before is None).
    #   2. For each qualifying page, build a prompt that includes content_after
    #      and asks the model to generate eval_questions_per_page
    #      (question, expected_statement) pairs.
    #   3. Parse the LLM output and create EvalQuestionProposal objects.
    #   4. Write proposals to curation/retrieval_eval_proposals.jsonl
    #      (append, not overwrite).
    #   5. Return the full list so the caller can log / surface a summary.
    #
    # Blocked on: LLM agent wiring (#53), Langfuse page-identity (#55/#65).
    raise NotImplementedError("Phase 3: not yet implemented")
