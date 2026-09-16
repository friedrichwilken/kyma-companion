# Replace the vector search with BM25

One page. Every number below is reproducible from this directory; links at the end.

## 1. The problem

The agent's documentation search returns the wrong page, and nobody can say why. From 145
logged searches over ten evaluation runs:

- "Kyma vs Cloud Foundry differences" returned the MCP server troubleshooting pages, because
  they contain "VS Code".
- "What is Kyma?" returned the Docker Registry and Application Connector module pages.
- "How to use Istio in Kyma", asked 33 times, never returned the Istio module page that says
  the module is preinstalled. The page was in the corpus every time.
- 68% of searches returned the same page twice in the top five.

The end-to-end evaluation could not have told us any of this. It is an LLM judging an LLM,
it moves by a percentage point between identical runs, and a scenario that fails ten times in a
row looks like a flaky test until someone reads the logs.

## 2. The claim

An in-process BM25 index over the Markdown files, built at image build time, loaded at start.
No HANA, no embedding model, no network call at query time.

- The index over 636 pages builds in under a second and answers in milliseconds.
- Retrieval is deterministic: all 16 distinct queries in the logs returned exactly one result
  set across all ten runs. The run-to-run variance in the scores is the LLM, not the search.
- A retrieval evaluation, 41 questions with the page that answers each, runs in under a second
  and gives the same number every time. It runs in CI before merge, like a unit test.

That is the sell: retrieval you can test, diff and explain.

## 3. The numbers

Retrieval evaluation, 41 queries, `recall@5` is "the right page is in the top five", MRR is
"how high it ranks" (1.0 means always first):

| Step | Pages searched | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| BM25 as first committed | 2584 | 0.707 | 0.805 | 0.565 |
| tokenizer and title-weight bugs fixed | 2584 | 0.805 | 0.829 | 0.532 |
| SAP Help copies of kyma-project pages removed from the search corpus | 636 | 0.805 | 0.805 | 0.672 |
| pages ranked by their best section | 636 | **0.829** | **0.854** | **0.683** |

The Istio module page for "How can I use Istio in Kyma?": absent from the top ten at the start,
rank 2 at the end.

What the numbers made visible: two outright bugs in the index. The tokenizer kept punctuation
and Markdown, so `Kyma?`, `` `APIRule` `` and `**Istio**` were three rare tokens each, and
"vs" matched "VS Code". The title boost repeated the string, not the tokens, so multi-word
titles got no boost at all. Both were found by reading the ranking of one failing query and
fixed in an afternoon. A vector index does not give you a ranking you can read.

End to end, before any of these fixes, BM25 scored 93.86% against 95.17% for the vector search
over ten runs each. The end-to-end run on the fixed branch is still to do. The retrieval
evaluation above is the number that changed and the one that will be measured on every PR.

## 4. The corpus

Half of the gain did not come from the retriever. The corpus the vector index is built from has
2,584 pages; 1,866 of them never mention Kyma, 461 are the same page under two sources, two
repositories are archived, and the upstream sidebars that carry titles and sections were never
read. Every retriever shares that problem, and the fix is the same for all of them: 2,117 pages
out, 636 in, each with a title, a section, a type and a source URL pinned to a commit. The
evidence page and the exclusions list are the backup slides.

## 5. The honest close

The same 41 questions can score the vector search too. The evaluation takes an HTTP endpoint as a
backend, so HANA can be measured with the same judge, on the same corpus, before anyone argues
about architecture. If the vector search wins on those numbers, we keep it and we still have the
evaluation. If BM25 wins, we drop a database, an embedding model and a network dependency from
the request path.

## Links

- Ten-run evaluation and log analysis: [README.md](README.md)
- Per-query retrieval eval before and after the index fixes: [retrieval-eval-2026-09-16.md](retrieval-eval-2026-09-16.md)
- Corpus evidence, with reproduction commands: [corpus-evidence-2026-09-16.md](corpus-evidence-2026-09-16.md)
- Step-by-step numbers on the proof-of-concept branch: [docs-stack-2026-09-16.md](docs-stack-2026-09-16.md)
- The 2,117 excluded pages, by rule, with links: [curator-exclusions.md](curator-exclusions.md)
- Raw logs: `run-*.txt`, `doc_search_logs.json`
- Code: [feat/docs-stack](https://github.com/friedrichwilken/kyma-companion/tree/feat/docs-stack) (BM25 index, section ranking, agent tools), [feat/curated-docs](https://github.com/friedrichwilken/kyma-companion/tree/feat/curated-docs) (the curated corpus and its weekly workflow)
