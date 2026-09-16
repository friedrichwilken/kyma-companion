# Docs stack proof of concept -- feat/docs-stack (2026-09-16)

Branch `feat/docs-stack` builds on `feat/doc-artifact-bm25` and applies every documentation-handling
improvement available so far, commit by commit: the curator, resolver-based selection, the BM25 index
fixes, section-level ranking, and the agent-side changes. This page records what each step did to the
corpus and to retrieval, measured with `doc_indexer/evaluation/run_retrieval_eval.py` (41 queries).

## Corpus

| Step | Pages fetched | Pages searched |
|---|---|---|
| hand-picked globs (`docs/*` for SAP Help) | 2584 | 2584 |
| resolvers: sidebars, SAP Help TOC subtrees, tutorial tags; archived repos dropped | 775 | 775 |
| SAP Help copies of kyma-project pages marked as mirrors | 775 | 636 |

The module landing READMEs are not linked from the sidebars; the sidebar resolver includes them
explicitly. Orphans (Markdown under `docs/user` that no sidebar links) and unresolved links are
recorded in each source's `meta.json` for the curator; a `manifest.json` at the root records the
fetched commit and the sha256 of every file.

## Retrieval

| Step | corpus | recall@5 | recall@10 | MRR | concept recall@5 |
|---|---|---|---|---|---|
| bfa1c492 (before any index fix) | 2584 | 0.707 | 0.805 | 0.565 | 0.538 |
| index fixes: tokenizer, title weight, same-title dedup, titles | 2584 | 0.805 | 0.829 | 0.532 | 0.615 |
| resolver-selected corpus, landing READMEs included | 775 | 0.780 | 0.805 | 0.549 | 0.538 |
| mirrors excluded from the search corpus | 636 | 0.805 | 0.805 | 0.672 | 0.538 |
| section-level ranking (best H2 section per page) | 636 | **0.829** | **0.854** | **0.683** | **0.615** |

The MRR dips in the middle rows are the eval counting an SAP Help copy at rank 1 as a miss; once the
copies are out of the corpus the kyma-project page is at rank 1 and MRR reflects it.

The A2A scenario that failed in all ten BM25 runs ("How can I use Istio in Kyma?", expecting the
statement that Istio is preinstalled) needs the Istio module landing page. Its rank for that query:
absent from the top 10 at bfa1c492, rank 3 after the index fixes, rank 18 on the trimmed corpus
before section ranking, **rank 2** at the end of the branch.

Still weak: "What is Kyma?" returns Kyma CLI command reference pages (`kyma alpha`, `kyma module`),
which are in the corpus through the explicit `docs/user/gen-docs/*` allowlist for the CLI source and
carry "kyma" in every title. Dropping that allowlist, or demoting reference pages for concept
questions, is the next experiment.

## What the agent sees now

- Search results carry title, source URL pinned to the fetched commit, module, doc type, page ID and
  the matched section. Pages over 12,000 characters are shortened to intro plus matched section.
- `read_kyma_doc` (full page by ID) and `list_kyma_docs` (modules, or one module's pages) are bound.
- The Busola resource kind is mapped to a module and named in the context message; the search tool
  and the REST endpoint accept a `module` filter.
- The prompt asks for a "Sources:" list of retrieved page URLs.

## Not done

- No end-to-end A2A evaluation run on this branch yet. Run `tests/blackbox/run_eval_10x.sh` against
  a deployment built from this branch to compare with the 93.86% BM25 mean and the 95.17% RAG mean.
- The curator's LLM classification has not been exercised on the new orphan lists.
- Phase 1 of the curator design (`docs_sources.yaml` and a committed lockfile with a CI check) is
  replaced here by the resolver config inside `docs_sources.json` and the generated `manifest.json`;
  a diff-and-PR workflow on top of the manifest does not exist yet.
