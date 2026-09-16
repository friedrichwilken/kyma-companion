# BM25 Doc Search -- Evaluation Findings

This document summarizes the evaluation of replacing HANA/RAG-based doc search with an
in-process BM25 index (`DocSearchTool` backed by `DocIndex`). The goal is to determine
whether BM25 is a viable replacement and what improvements would close the gap with RAG.

## Context

- **Branch**: `feat/doc-artifact-bm25` on `friedrichwilken/kyma-companion` (targeting `kyma-project/kyma-companion`)
- **Approach**: Docs are fetched and indexed at build time into a file artifact. At runtime the
  app loads the artifact into an in-process BM25 index (rank-bm25 / BM25Okapi). No vector DB,
  no embedding model, no network calls at query time.
- **Test**: A2A blackbox evaluation (`tests/blackbox/src/run_a2a_evaluation.py`) -- 23 scenarios,
  each with multiple expectations, up to 3 retry attempts per scenario.
- **LLM queries are the callers**: the search tool is invoked by the Kyma ReAct agent, not by
  humans, so queries are precise and technical (no typos, consistent terminology).

---

## Evaluation test results -- 10 runs

### BM25 (local, 2026-09-15)

| Run | Score | Failed scenarios |
|-----|-------|-----------------|
| 1 | 94.95% | test-question-23 |
| 2 | 94.65% | test-question-23 |
| 3 | 94.75% | test-question-23 |
| 4 | 94.85% | test-question-23 |
| 5 | 92.77% | test-question-23 |
| 6 | 95.45% | test-question-23 |
| 7 | 90.89% | test-question-23 |
| 8 | 92.77% | test-question-23 |
| 9 | 94.46% | test-question-23 |
| 10 | 93.07% | test-question-23 |
| **mean** | **93.86%** | |
| **std dev** | **~1.5pp** | |
| **min / max** | **90.89% / 95.45%** | |

`test-question-23` fails in every run -- see note below.

### RAG baseline (CI, `kyma-project/kyma-companion`, 2026-09-03 to 2026-09-14)

| Run ID | Score | Branch |
|--------|-------|--------|
| 34843466122 | 95.94% | chore/remove-dead-code |
| 34842190316 | 94.36% | chore/remove-dead-code |
| 34839777421 | 95.05% | chore/remove-dead-code |
| 34831411594 | 93.96% | chore/remove-dead-code |
| 34829744654 | 95.45% | chore/remove-dead-code |
| 33967127730 | 94.95% | main |
| 33888335037 | 95.54% | scratch-runtime-image |
| 33886319084 | 96.14% | scratch-runtime-image |
| 33882137038 | 94.65% | main |
| 33864902831 | 95.64% | fix/harden-runtime-images |
| **mean** | **95.17%** | |
| **std dev** | **~0.6pp** | |
| **min / max** | **93.96% / 96.14%** | |

### Comparison

| Metric | RAG | BM25 | Delta |
|--------|-----|------|-------|
| Mean | 95.17% | 93.86% | -1.31pp |
| Std dev | ~0.6pp | ~1.5pp | BM25 has 2.5x more variance |
| Min | 93.96% | 90.89% | BM25 dips lower |
| Max | 96.14% | 95.45% | comparable ceiling |

**Conclusion**: BM25 is 1.3pp below RAG on average, with significantly higher variance. The gap
is real but small. The higher variance in BM25 runs suggests it occasionally misses something
RAG would catch -- see log analysis below for candidates.

### Note on test-question-23

`test-question-23` fails in every single BM25 run (3 attempts each). It is the scenario
"How can I use Istio in Kyma?" with the single required expectation "points out that Istio comes
preinstalled in Kyma". The RAG baseline (`tests/blackbox/baseline_metrics.json`) passes it.

This is a retrieval regression, not a flaky test: both the Istio module README
(`istio/docs/user/README.md`) and its SAP Help copy (`istio-module-26ffe00.md`) state that the
module "is automatically added when you create a Kyma runtime instance", both are in the corpus,
and neither appeared in the top 5 for the query "How to use Istio in Kyma" in any of the 33 logged
searches. The tokenizer and title fixes below bring the Istio Module page to rank 3; see
[`retrieval-eval-2026-09-16.md`](retrieval-eval-2026-09-16.md).

---

## Doc search log analysis

145 search calls were logged across all 10 runs. Full logs: `doc_search_logs.json` on branch `docs/bm25-eval-logs`.

### Summary statistics

| Metric | Value |
|--------|-------|
| Total search calls | 145 |
| Unique queries | 16 |
| Zero-result queries | 0 |
| Results with empty title | 33 / 725 (4.6%) |
| Results with duplicate title in top-5 | 99 / 145 searches (68%) |
| Results with populated module field | 0 / 725 (0%) |

### Finding 1: Module field always empty (100%)

Every result has an empty `module` field. `DocIndex` is not populating `DocPage.module` when
loading the docs artifact, which means:

- The module-scoped search path in `DocIndex.search()` is dead code
- The agent cannot scope searches to a specific Kyma module (e.g. "search only in Istio docs")
- Log entries show `"module": ""` for all 725 results

**Root cause (found)**: `DocIndex` reads an optional `meta.json` per source directory, but the
fetcher never wrote one. The same gap left every `url` a bare relative path
(`btp-cloud-platform/docs/...`) instead of a link. The fetcher now writes `meta.json` with the
repo slug, module (source name), a base URL pinned to the fetched commit, and the commit itself.

### Finding 2: Duplicate results in 68% of searches

99 out of 145 search calls return at least one repeated title in the top-5 results. Example:

```
query: "expose endpoint using Kyma APIRule"
results:
  -> Expose and Secure Workloads          (api-gateway/docs/user/expose-workloads/README.md)
  -> Expose and Secure Workloads          (btp-cloud-platform/docs/30-development/expose-and-secure-workloads-19e332b.md)
  -> Deploy the SAPUI5 Frontend in SAP BTP, Kyma Runtime
  -> Expose a Function Using the APIRule Custom Resource
  -> Expose and Secure a Workload with OAuth2 Proxy ...
```

The index holds whole pages, not chunks, and no search ever returned the same URL twice. The
repeats are the same page in two sources: the module repository on kyma-project and its copy in
the SAP Help repository (`btp-cloud-platform`). The corpus has 207 title groups covering 461 pages
this way. The agent receives the same content twice, wasting context window.

**Fix (applied)**: collapse results by tokenized title while walking the ranked list, keeping the
highest-scoring copy. De-duplicating by URL, as first proposed, would not have removed anything.

### Finding 3: Empty titles for two query patterns

"Kyma vs Cloud Foundry differences" and "Kyma vs other Kubernetes environments hyperscalers
differences" consistently return results with empty titles (22 and 11 empty titles respectively
across all runs). These are SAP tutorials (`btp-dev-guidance`) that carry the title in YAML frontmatter and start
with an H2; the title extractor only looked for an H1. It now falls back to the frontmatter
`title` key, which leaves 2 untitled pages in the corpus instead of 14.

---

## Recommendations

Listed roughly by expected impact / ease of implementation.

### 0. Root causes found in the index itself (applied on this branch)

The log analysis above pointed at symptoms; reading `DocIndex` found the causes. Two of them are
outright bugs and explain most of the gap to RAG:

- **Tokenizer kept punctuation and Markdown.** `text.lower().split()` made `Kyma?`, `` `APIRule` ``
  and `**Istio**` distinct, rare, high-IDF tokens. "Kyma vs Cloud Foundry" matched "VS Code" in the
  MCP server pages. Fixed: alphanumeric tokenization, small stopword list, frontmatter and HTML
  comments stripped from content, link targets and HTML tags dropped from the indexed text.
- **Title weighting was broken.** `page.title * 3` produced `Kyma ModulesKyma ModulesKyma Modules`,
  so multi-word titles got no boost and garbage tokens. Fixed: repeat the token list, not the string.
- **Retrieval is deterministic.** Every one of the 16 distinct queries returned exactly one result
  set across all 10 runs. The run-to-run variance in the table above is LLM noise, not retrieval.

### 1. De-duplicate results (applied)

See Finding 2. Same-title pages are collapsed at search time.

### 2. Module field population (applied)

See Finding 1. `meta.json` is now written by the fetcher; module-scoped search works.

### 3. Empty-title docs (applied)

See Finding 3. Frontmatter `title` is used when there is no H1.

### 4. Expose BM25 scores in results (observability)

`DocIndex.search()` computes scores but drops them before returning. Returning
`list[tuple[DocPage, float]]` (or adding a `score` field to `DocPage`) would allow:
- Better logging (score distribution tells you how confident the retrieval was)
- Score-threshold filtering (drop results below a minimum score)
- Hybrid reranking (combine BM25 score with an embedding similarity score)

### 5. Query expansion / synonym injection (medium impact, more complex)

BM25 is exact-match. For queries like "Kyma vs Cloud Foundry" there may be no docs that
literally contain "Cloud Foundry" -- a synonym or query-expansion step (e.g. expanding known
Kyma terminology) could help. Low priority given LLM callers are already precise.

### 6. Hybrid BM25 + dense reranking (higher impact, significant complexity)

HANA vector DB is already available. A hybrid approach would:
1. Run BM25 to get top-N candidates (fast, exact)
2. Rerank with embedding similarity (semantic, handles synonyms)

This is the natural next step if the 1.3pp gap matters for production. Worth doing after
fixes 1-3 are in place, to isolate the contribution of each improvement.

### 7. test-question-23 (resolved as a retrieval regression)

See the note above. The scenario passes on RAG and fails on BM25 because the Istio module page was
not retrieved. Re-run the A2A evaluation on this branch to confirm the fix end to end.

### 8. Next candidates

- **Corpus scoping.** 2064 of 2584 pages come from `btp-cloud-platform` (`docs/*` matches every
  file) and 53% of all returned results came from there. Restrict it to the Kyma section of its
  table of contents, as proposed in `docs/doc-indexer-improvement-options.md`.
- **Section-level indexing.** Long overview pages lose to short pages under BM25 length
  normalisation ("What is Kyma?" returns Kyma CLI command pages). Index H2 sections, return the
  page. Alternatively tune `b` (length normalisation) downwards and measure.
- **Snippets instead of full pages.** Search returns five full pages. With page IDs now in the
  output, `read_kyma_doc` could fetch the full text on demand. `read_kyma_doc` and
  `list_kyma_docs` exist but are not bound into the agent; decide whether to bind or delete them.
- **Grow the eval set from the logs.** The 16 logged agent queries are real callers; add them with
  expected pages. Fix the query-set issues listed in `retrieval-eval-2026-09-16.md`.

---

## Files in this directory

| File | Description |
|------|-------------|
| `README.md` | This document |
| `doc_search_logs.json` | All 145 `doc_search` log entries; moved to branch `docs/bm25-eval-logs` with the run logs |
| run logs | The full A2A output of the 10 BM25 runs (70,000 lines) lives on branch `docs/bm25-eval-logs` of the fork, not here |
| `retrieval-eval-2026-09-16.md` | Retrieval eval (recall@k, MRR) before and after the index fixes |
