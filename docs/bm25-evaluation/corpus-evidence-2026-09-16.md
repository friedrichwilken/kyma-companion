# What the documentation corpus looks like today -- evidence (2026-09-16)

All numbers come from fetching the sources in `doc_indexer/docs_sources.json` as configured on
`main` (the corpus the HANA index is built from) and, for the "after" column, from the
resolver-based configuration on `feat/docs-stack`. Reproduction commands are at the end.

## 1. Most of the corpus is not about Kyma

| | Pages |
|---|---|
| Markdown pages fetched with the `main` configuration | 2584 |
| of which from the SAP Help repository (`docs/*` matches every file) | 2064 |
| pages that never contain the word "kyma" | **1866 (72%)** |
| SAP Help pages under Kyma-titled entries of its own table of contents | 285 |

Sample titles of fetched pages that never mention Kyma: "Create Clone", "User Provisioning",
"Add Users from SAP ID Service for Multi-Environment Subaccounts", "Create Destinations",
"Read Execution Log", "Download Certificate", "Inbound Communication via Communication User".
Every one of these is embedded, stored in HANA and eligible to be returned to the agent.

The pattern `docs/*` was meant as "the docs folder". `fnmatch` lets `*` cross `/`, so it
selects all 2064 files of an SAP BTP documentation repository of which roughly 14% concern Kyma.

## 2. The same page is indexed several times

| | Count |
|---|---|
| Groups of pages sharing a title | 207 groups, **461 pages** |
| Pages from non-kyma-project sources whose title or H1 matches a kyma-project page (mirrors) | **139** |
| Byte-identical files | 1 pair (`serverless` and `keda-manager` troubleshooting READMEs) |

The SAP Help Portal republishes the module documentation from the kyma-project repositories.
Examples of the same page under two sources: "Eventing Module", "Istio Gateways", "Expose and
Secure Workloads", "Subscription CR", "Kyma Modules" (three copies). In the ten BM25
evaluation runs, **68% of searches (99 of 145)** returned the same page twice in the top five, and
53% of all returned results came from the SAP Help copy set.

## 3. Upstream navigation is ignored

| | |
|---|---|
| Module repositories that ship `docs/user/_sidebar.ts`, the navigation kyma-project.io publishes | 16 |
| Sidebar files read by the indexer | 0 (the exclusion `*/_sidebar.md` dates from the docsify era; `.ts` is never fetched) |
| Pages the sidebars select across the 16 modules | 364 (landing READMEs included) |
| `docs/user` pages no sidebar links, which the glob fetches anyway | 20 (plus the CLI command reference, allowlisted on purpose) |
| Sidebar links pointing at deleted pages (stale upstream navigation) | 2 (api-gateway) |

Sidebars carry the canonical title and the section (Tutorials, Technical Reference,
Troubleshooting). Because they are not read, the index derives titles from the H1 and has no
document type at all.

## 4. Dead and mislabelled content

| | |
|---|---|
| Archived repositories still fetched | 2: `warden` (archived 2025-08), `auditlog-manager`, 11 pages together |
| Pages indexed with an empty title | 14 (SAP tutorials carry the title in frontmatter; the extractor only looked for an H1) |
| Module field populated on any indexed page | 0 of 725 results in the evaluation logs; module-scoped search was dead code |
| Source URL on a result | none: `Source: btp-cloud-platform/docs/...` is a relative path, the agent cannot cite |

## 5. What the agent actually got back (from 145 logged searches)

| Query the agent sent | Top results |
|---|---|
| "What is Kyma?" | Docker Registry Module, Application Connector Module (twice), Managing Spaces |
| "Kyma vs Cloud Foundry differences" | Connect to the MCP Server for SAP BTP Administration, Troubleshooting the MCP Server (the pages contain "VS Code") |
| "Kyma available regions SAP BTP" | Regions, Providing Details for SAP HANA Service Database Problems, Account Administration Using APIs |
| "How to use Istio in Kyma" (33 times) | sidecar and gateway pages; never the Istio module page that says the module is preinstalled |

The last row is the A2A scenario `test-question-23`, which failed in all ten BM25 runs and passes
on the RAG baseline. The page that answers it was in the corpus every time.

## 6. After curation on `feat/docs-stack`

| | Before | After |
|---|---|---|
| Pages fetched | 2584 | 775 |
| Pages in the search corpus (mirrors removed) | 2584 | 636 |
| SAP Help pages | 2064 | 285 |
| Archived repositories | 2 | 0 |
| Pages with empty title | 14 | 2 |
| Pages with a document type | 0 | 677 (all resolver-selected) |
| Citable source URL, pinned to a commit | no | yes |
| Retrieval eval, recall@5 (41 queries) | 0.707 | **0.829** |
| Retrieval eval, MRR | 0.565 | **0.683** |
| Istio module page, rank for "How can I use Istio in Kyma?" | absent from top 10 | **2** |

## Reproduce

```bash
# corpus as on main
git checkout main && cd doc_indexer && python src/main.py fetch          # DOCS_PATH=<dir>
find <dir> -name '*.md' | wc -l                                          # 2584
grep -rLi kyma <dir> --include='*.md' | wc -l                            # 1866
# corpus and eval as on feat/docs-stack
git checkout feat/docs-stack && cd doc_indexer && python src/main.py fetch
python evaluation/run_retrieval_eval.py --mode bm25 --docs-path <dir> --k 10 --queries evaluation/queries.jsonl
```

Related: `README.md` (ten-run evaluation and log analysis), `retrieval-eval-2026-09-16.md`
(per-query before and after the index fixes), `docs-stack-2026-09-16.md` (the curated branch).
