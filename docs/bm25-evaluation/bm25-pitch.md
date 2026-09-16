# Replace the vector search with BM25

One page, one question. Every number below is reproducible from this directory; links at the end.

## 1. "How can I use Istio in Kyma?"

That is evaluation scenario test-question-23. The only thing the answer has to contain is that
Istio comes preinstalled. The vector search passes it. BM25 failed it in ten runs out of ten,
three attempts each, while scoring within a point of the vector search on everything else.
To be clear about where the bug sat: in the new BM25 index on this branch, not on main. The
vector search on main passes the scenario. What follows is not "main is broken", it is "this is
what finding and fixing a retrieval failure looks like when the ranking can be read".

It looked like a flaky test. The logs said otherwise. The agent sent the same search, "How to
use Istio in Kyma", 33 times, and got the same five pages back 33 times:

1. Enabling Istio Sidecar Proxy Injection (SAP Help copy)
2. Secure Development in the Kyma Environment
3. Use Gateway API to Expose a Workload in SAP BTP, Kyma Runtime
4. Enabling Istio Sidecar Proxy Injection (kyma-project original)
5. Istio Gateways

The page that answers the question, the Istio module page, was in the corpus every time. Twice,
in fact: the kyma-project original and its SAP Help copy both say the module "is automatically
added when you create a Kyma runtime instance". Neither made the top ten.

Because BM25 is a formula over tokens, the ranking can be read. Reading it found two bugs in
the index and two problems in the corpus:

- The tokenizer kept punctuation and Markdown, so `Kyma?`, `` `Istio` `` and `**Istio**` were
  three rare tokens each. A query for "Kyma vs Cloud Foundry" matched "VS Code".
- The title boost repeated the string, not the tokens. "Istio Module" times three became
  "Istio ModuleIstio ModuleIstio Module", one token nobody searches for.
- The module page is long, and BM25 normalises by length, so short tutorials that mention Istio
  in every line outrank the overview that explains it.
- The SAP Help copy and the original split the score between them and pushed each other down.

Each fix was measured on the same query, one commit at a time:

| Step | Rank of the Istio module page |
|---|---|
| BM25 as evaluated in the ten runs | absent from the top 10 |
| tokenizer and title-weight bugs fixed | 3 |
| corpus trimmed from 2,584 to 636 pages, copies removed | 18 (worse: with the copy gone, length normalisation won) |
| pages ranked by their best section | **2** |

The row that got worse is the point. It was visible the same afternoon, on one query, in
under a second, and the next commit fixed it. With a vector index the same regression is a
number that moved by a point in an evaluation that moves by a point on its own.

## 2. What that proves

An in-process BM25 index over the Markdown files, built at image build time, loaded at start.
No HANA, no embedding model, no network call at query time.

- Deterministic: all 16 distinct queries in the ten runs returned exactly one result set each.
  The run-to-run variance in the end-to-end scores is the LLM, not the search.
- Explainable: a wrong answer is a ranking you can read, and a ranking you can read is a bug you
  can find.
- Testable: 41 questions with the page that answers each, scored in under a second, the same
  number every time, gated in CI before merge.

## 3. The numbers over all 41 questions

`recall@5` is "the right page is in the top five"; MRR is "how high it ranks", 1.0 meaning
always first.

| Step | Pages searched | recall@5 | recall@10 | MRR |
|---|---|---|---|---|
| BM25 as evaluated in the ten runs | 2584 | 0.707 | 0.805 | 0.565 |
| tokenizer and title-weight bugs fixed | 2584 | 0.805 | 0.829 | 0.532 |
| SAP Help copies removed from the search corpus | 636 | 0.805 | 0.805 | 0.672 |
| pages ranked by their best section | 636 | **0.829** | **0.854** | **0.683** |

End to end, before any of these fixes, BM25 scored 93.86% against 95.17% for the vector search,
ten runs each, with test-question-23 as the one consistent failure. The end-to-end run on the
fixed branch is still to do.

## 4. The corpus

Two of the four Istio findings were corpus problems, and every retriever shares them. The corpus
the vector index is built from has 2,584 pages: 1,866 never mention Kyma, 461 are the same page
under two sources, two repositories are archived, and the upstream sidebars that carry titles and
sections were never read. The fix is the same for any retriever: 2,117 pages out, 636 in, each
with a title, a section, a type and a source URL pinned to a commit. The evidence page and the
exclusions list are the backup slides.

## 5. The honest close

There is a bug-on-main story too, and it is a different one: content silently lost in
chunking (preamble, tiny sections, oversized sections), found by reading main's indexer and
fixed in upstream PR 1400. The corpus facts in section 4 are also facts about main today.

The same 41 questions can score the vector search too: the evaluation takes an HTTP endpoint as
a backend, so HANA can be measured with the same judge on the same corpus before anyone argues
about architecture. If the vector search wins on those numbers, we keep it and we still have the
evaluation. If BM25 wins, we drop a database, an embedding model and a network dependency from
the request path, and the next Istio question is an afternoon, not a mystery.

## Links

- Ten-run evaluation and log analysis: [README.md](README.md)
- Per-query retrieval eval before and after the index fixes: [retrieval-eval-2026-09-16.md](retrieval-eval-2026-09-16.md)
- Corpus evidence, with reproduction commands: [corpus-evidence-2026-09-16.md](corpus-evidence-2026-09-16.md)
- Step-by-step numbers on the proof-of-concept branch: [docs-stack-2026-09-16.md](docs-stack-2026-09-16.md)
- The 2,117 excluded pages, by rule, with links: [curator-exclusions.md](curator-exclusions.md)
- Raw logs: `run-*.txt`, `doc_search_logs.json` (the 33 Istio searches are in there)
- Code: [feat/docs-stack](https://github.com/friedrichwilken/kyma-companion/tree/feat/docs-stack) (BM25 index, section ranking, agent tools), [feat/curated-docs](https://github.com/friedrichwilken/kyma-companion/tree/feat/curated-docs) (the curated corpus and its weekly workflow)
