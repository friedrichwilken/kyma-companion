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

`test-question-23` fails in every single BM25 run (3 attempts each). It also fails in the
earlier local run before the 10-run series started. This scenario involves complex multi-error
cluster state (image pull errors, Subscription validation errors, scheduler errors) and may
be flaky independent of the search backend. It should be investigated separately to determine
whether it fails on RAG as well.

---

## Doc search log analysis

145 search calls were logged across all 10 runs. Full logs: [`doc_search_logs.json`](doc_search_logs.json).

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

**Root cause to investigate**: how `DocPage` objects are constructed when loading the artifact --
check whether the `module` field is written to the artifact JSON and whether it is read back.

### Finding 2: Duplicate results in 68% of searches

99 out of 145 search calls return at least one duplicate title in the top-5 results. Example:

```
query: "expose endpoint using Kyma APIRule"
results:
  -> Expose and Secure Workloads
  -> Expose and Secure Workloads    <-- duplicate
  -> Deploy the SAPUI5 Frontend in SAP BTP, Kyma Runtime
  -> Expose a Function Using the APIRule Custom Resource
  -> Expose and Secure a Workload with OAuth2 Proxy ...
```

The same page appears as multiple chunks (BM25 scores each chunk independently). The agent
receives repeated content, wasting context window and potentially confusing the LLM.

**Fix**: de-duplicate results by URL (or title) after scoring, keeping only the highest-scored
chunk per page. This is a one-liner in `DocIndex.search()`.

### Finding 3: Empty titles for two query patterns

"Kyma vs Cloud Foundry differences" and "Kyma vs other Kubernetes environments hyperscalers
differences" consistently return results with empty titles (22 and 11 empty titles respectively
across all runs). These are likely docs without a proper H1 header or with a frontmatter-only
title that is not being extracted.

---

## Recommendations

Listed roughly by expected impact / ease of implementation.

### 1. De-duplicate results by URL (high impact, trivial to implement)

In `DocIndex.search()`, after sorting by score, filter out pages with duplicate URLs:

```python
seen_urls: set[str] = set()
unique: list[tuple[int, float]] = []
for i, s in indexed[:top_k * 3]:  # over-fetch to have enough after dedup
    url = self._page_list[i].url
    if url not in seen_urls:
        seen_urls.add(url)
        unique.append((i, s))
    if len(unique) == top_k:
        break
return [self._page_list[i] for i, _ in unique]
```

This should immediately reduce the wasted context window and likely improve scores on queries
that currently get 2-3 unique docs instead of 5.

### 2. Fix module field population (medium impact, easy to implement)

Investigate the artifact loading path to ensure `DocPage.module` is populated. Once fixed,
the agent can use module-scoped search for Kyma-specific queries, reducing noise from
unrelated modules.

### 3. Fix empty-title docs (low-medium impact)

Docs without H1 titles return empty title strings. Options:
- Fall back to filename or path as title during indexing
- Use frontmatter `title:` field if present
- Skip titleless chunks entirely (they may be low-quality)

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

### 7. Investigate test-question-23 independently

Determine whether this scenario also fails on RAG (by checking CI run logs for failed
scenarios). If it fails on both, it is a flaky test unrelated to the search backend and
should be fixed or marked as known-flaky separately.

---

## Files in this directory

| File | Description |
|------|-------------|
| `README.md` | This document |
| `doc_search_logs.json` | All 145 `doc_search` log entries (query + results, no sensitive data) |
| `run-1-*.txt` through `run-10-*.txt` | Full A2A evaluation output for each of the 10 BM25 runs |
