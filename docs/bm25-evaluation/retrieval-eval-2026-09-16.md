# BM25 retrieval eval -- before and after the index fixes (2026-09-16)

Retrieval-level evaluation of `DocIndex` with `doc_indexer/evaluation/run_retrieval_eval.py`
(`--mode bm25 --k 10`) on the corpus fetched from `doc_indexer/docs_sources.json` on 2026-09-16
(2584 pages). The query set is `doc_indexer/evaluation/queries.jsonl`; the question of the
always-failing A2A scenario `test-question-23` ("How can I use Istio in Kyma?") was added as
`concept-istio-preinstalled`, expecting the Istio module page (kyma-project or SAP Help copy).

"Before" is commit `bfa1c492` (the state evaluated in the 10 A2A runs), "after" is the branch
with the tokenizer, title weighting, mirror de-duplication, meta.json and frontmatter-title fixes.

## Summary

| Slice | n | recall@5 before | recall@5 after | recall@10 before | recall@10 after | MRR before | MRR after |
|---|---|---|---|---|---|---|---|
| overall | 41 | 0.707 | 0.805 | 0.805 | 0.829 | 0.565 | 0.532 |
| concept | 13 | 0.538 | 0.615 | 0.615 | 0.615 | 0.392 | 0.359 |
| howto | 14 | 0.714 | 0.929 | 0.857 | 0.929 | 0.567 | 0.649 |
| troubleshooting | 14 | 0.857 | 0.857 | 0.929 | 0.929 | 0.724 | 0.577 |

Recall@5 improves from 0.707 to 0.805. MRR falls, but the table below shows why: in 10 of the
11 queries whose reciprocal rank dropped, the page at rank 1 is the SAP Help copy of the
expected kyma-project page (same title, same content). The eval's expected paths only list the
kyma-project copy, so those hits count as misses. Mirror de-duplication then removes the
kyma-project copy from the list, which turns a rank-2 hit into no hit. For the agent both copies
are equivalent. The one genuine drop is `ts-apirule-accessstrategies`, where the migration page
moved from rank 2 to rank 5 behind the "retrieve v1beta1 spec" page.

## Per-query changes

Only queries whose reciprocal rank changed are listed.

| query | RR before | RR after | note |
|---|---|---|---|
| concept-istio-preinstalled (test-question-23) | 0.00 | 0.33 | Istio Module page now at rank 3; it was absent from the top 10 |
| howto-enable-istio-sidecar | 0.33 | 1.00 | |
| howto-create-btp-service-binding | 0.14 | 1.00 | |
| howto-create-serverless-function | 0.12 | 0.50 | |
| howto-busola-custom-resource | 0.00 | 0.50 | |
| concept-istio-overview | 0.25 | 0.50 | |
| concept-btp-service-binding | 0.25 | 0.50 | |
| ts-istio-peer-authentication | 0.14 | 0.25 | |
| concept-eventing-nats | 1.00 | 0.50 | SAP Help copy of the expected page at rank 1 |
| concept-serverless-overview | 1.00 | 0.50 | SAP Help copy of the expected page at rank 1 |
| concept-telemetry-overview | 0.50 | 0.33 | SAP Help copy of the expected page at rank 1 |
| howto-subscribe-to-events | 1.00 | 0.25 | SAP Help copy of the expected page at rank 1 |
| howto-configure-telemetry-tracing | 1.00 | 0.50 | SAP Help copy of the expected page at rank 1 |
| ts-subscription-invalid-sink | 1.00 | 0.50 | SAP Help copy of the expected page at rank 1 |
| ts-eventing-cr-not-ready | 1.00 | 0.50 | SAP Help copy of the expected page at rank 1 |
| ts-nats-not-ready | 1.00 | 0.12 | SAP Help copy of the expected page at rank 1 |
| concept-kyma-modules | 0.10 | 0.00 | same-title copy at rank 9 |
| ts-apirule-accessstrategies | 0.50 | 0.20 | genuine drop, migration page rank 2 to 5 |

## What each fix contributed (40-query set, before the Istio query was added)

| Step | recall@5 | recall@10 | MRR |
|---|---|---|---|
| bfa1c492 | 0.725 | 0.825 | 0.579 |
| + title weighting fix | 0.725 | 0.825 | 0.580 |
| + tokenizer and content cleaning | 0.800 | 0.825 | 0.555 |
| + same-title de-duplication | 0.800 | 0.825 | 0.537 |
| + meta.json, frontmatter titles | 0.800 | 0.825 | 0.537 |

## Known limits of the query set

- `concept-kyma-vs-cloudfoundry` expects `kyma/docs/01-overview`, but that page does not mention
  Cloud Foundry. No lexical search can satisfy it; the A2A scenario passes from model knowledge.
- Expected paths list only the kyma-project copy of pages that also exist in SAP Help
  (`btp-cloud-platform`). Either list both copies or decide which copy the index should prefer.
- Concept queries remain the weakest slice (recall@5 0.615). "What is Kyma?" still returns Kyma CLI
  command pages: the overview page is long and every page mentions Kyma, so BM25 has little to
  work with. Section-level indexing or a lower length-normalisation parameter are the next
  candidates, see the README.

## How to reproduce

```bash
# fetch the corpus (doc_indexer venv)
cd doc_indexer
PYTHONPATH=src python -c "from fetcher.fetcher import DocumentsFetcher; DocumentsFetcher('docs_sources.json', '/tmp/docs', '/tmp/docs-tmp').run()"
# run the eval (app venv)
cd ..
poetry run python doc_indexer/evaluation/run_retrieval_eval.py --mode bm25 --docs-path /tmp/docs --k 10 \
  --queries doc_indexer/evaluation/queries.jsonl --out /tmp/eval.json
```
