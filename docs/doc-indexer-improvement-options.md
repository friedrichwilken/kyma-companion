# Doc Indexer: Improvement Options

Status: discussion document, 2026-09-10. Not a decision.

This document summarizes the findings from a review of the `doc_indexer/` subproject and the RAG
path in the main application, and lays out the options for improving how Kyma Companion works
with documentation.

## 1. Current state

### Pipeline

1. **Fetch:** download tarballs of about 25 GitHub repos at `HEAD`, copy whitelisted Markdown files
   (`doc_indexer/docs_sources.json`).
2. **Chunk:** split each file by headers (H1, then H2, then H3, only when a section exceeds 1000
   tokens), drop sections of 20 tokens or fewer, prefix each chunk with a breadcrumb title.
3. **Embed and store:** `text-embedding-3-large`, written into one HANA table in batches of 200
   with a 3-second sleep between batches, after deleting all existing rows.
4. **Query (main app, `src/rag/`):** generate 4 alternative queries, run pure vector search for each,
   fuse with RRF, rerank with an LLM, return 4 to 5 chunks to the agent.

### Problems found

| Area | Finding |
|---|---|
| Atomicity | `index()` deletes all rows, then inserts. A failure halfway leaves a partial index. The backup/restore logic in `MarkdownIndexer` is dead code. |
| Metadata | Every chunk gets `module="kyma"`, `version="latest"`; source is a local path. No repo URL, commit SHA or public URL, so the agent cannot cite and nothing can be filtered by module. |
| Reproducibility | Sources are fetched at `HEAD`. No record of which commit an index came from. |
| Content loss | Sections of 20 tokens or fewer are dropped. Preamble before the first header of a long document is skipped. Sections still over 1000 tokens at H3 are kept whole and truncated by the embedding model at 8191 tokens. |
| Input noise | No preprocessing. YAML frontmatter, `<!-- loio -->` comments, VitePress markup, badges and link tables go into the embeddings. |
| Evaluation | No retrieval-level eval (query to document, recall@k). Only end-to-end blackbox tests exist. |
| Retrieval | Pure vector search. Kyma questions are full of exact identifiers where lexical search is strong. Two extra LLM calls per search (query generation, reranking). |
| Bugs | `bool(config("INDEX_TO_FILE", default=False))` is `True` for any non-empty string, including `"false"`. Hard-coded rate-limit sleeps. Unused `tree` subprocess call. |

### Source list problems

| Finding | Detail |
|---|---|
| Archived repos indexed | `warden` (archived 2025-08) and `auditlog-manager` are archived. |
| Sidebars excluded instead of used | `*/_sidebar.md` exclusion is from the docsify era. Module repos now ship `docs/user/_sidebar.ts`, which is the authoritative list of user-facing pages. |
| SAP BTP docs mostly noise | Pattern `docs/*` matches all 2063 Markdown files in `SAP-docs/btp-cloud-platform` (fnmatch `*` crosses `/`). Only about 282 pages sit under Kyma-titled entries in `docs/index.md`. Roughly 85% of that source is unrelated BTP content. |
| Not on the public site | `lifecycle-manager`, `modulectl`, `kyma-environment-broker` are control-plane and tooling repos. Keeping them should be an explicit decision. |
| Titles and order lost | Sidebars provide canonical titles and hierarchy; the indexer derives titles from H1 text. |

### Upstream facts worth knowing

- kyma-project.io is a VitePress site built from `kyma-project/kyma`. Its deploy workflow runs
  three times daily and copies `docs/user` from an explicit list of 16 repos (matrix in
  `.github/workflows/deploy.yml`, mirrored in `hack/copy_external_content.sh`).
- The built site publishes 447 pages and exposes `https://kyma-project.io/hashmap.json`, a list of
  every published page.
- Each module repo has `docs/user/_sidebar.ts` with titles, links and hierarchy.
- The site's edit-link pattern maps every page to its GitHub source, giving provenance for free.
- `SAP-docs/btp-cloud-platform/docs/index.md` is a complete table of contents; Kyma pages sit under
  Kyma-titled entries.
- `sap-tutorials` files carry frontmatter with `primary_tag: software-product>sap-btp, kyma-runtime`.
- Module repos ship CRD schemas under `config/crd/bases/` with per-field descriptions, and some
  keep per-release notes under `docs/release-notes/`.
- Module docs do not use VitePress frontmatter (description, tags), so those site search fields are empty.

### Corpus size

| Source family | Pages |
|---|---|
| kyma-project.io (kyma repo + 16 module repos) | 447 |
| SAP Help, Kyma section of btp-cloud-platform | ~282 |
| sap-tutorials, Kyma-tagged | a few dozen |

Roughly one million tokens in total. Any single module is 10 to 60 pages.

## 2. Groundwork needed regardless of pathway

These apply to every option below and should be done first.

1. **Discovery from upstream sources of truth.** Replace the hand-picked path list with resolvers:
   - Kyma site: repo list from the site deploy matrix (or `hashmap.json`), page list from each
     repo's `_sidebar.ts`.
   - SAP Help: parse `docs/index.md`, take Kyma-titled subtrees, plus a small explicit allowlist.
   - Tutorials: select by frontmatter tag.
   - Remaining `kyma-project` repos: convention `docs/user/**`, denylist, drop archived repos via
     the GitHub API.
2. **Lockfile and change PRs.** A `docs_sources.lock` with resolved SHAs and a manifest of every
   file (path, content hash, title). A scheduled workflow resolves new HEADs, diffs manifests, and
   opens a PR listing added, removed and changed pages, new repos in the site matrix, newly archived
   repos, and fetched files that no sidebar references. Merging the PR triggers the rebuild or
   reindex.
3. **Retrieval eval set.** Real user questions mapped to the pages that answer them, scored with
   recall@5 and MRR, run in CI. Grow it from production retrieval logs (see add-ons).
4. **Content preparation.** Strip frontmatter and HTML comments, rewrite relative links to public
   URLs, replace images with alt text, keep tab blocks and callouts intact, deduplicate by content
   hash (root README vs `docs/user/README.md`), merge tiny sections into their parent instead of
   dropping them.
5. **Fail loudly.** Assert that every sidebar link resolves to a fetched file, report orphans, and
   fail the job on regressions.

## 3. Pathways (mutually exclusive at the storage layer)

### Pathway A: keep HANA vector RAG, fix it in place

- Index into `kyma_docs_<sha>`, verify, then rename (atomic swap).
- Real metadata: module, version, repo, path, commit SHA, public URL, section type.
- Incremental upserts keyed on source path and content hash; delete rows whose source vanished.
- Hybrid search: lexical (in-process BM25 or HANA full-text) fused with vector via the existing RRF.
- Document-level results: embed small chunks, return the whole page or H2 section.
- Optional: contextual chunk prefixes generated by an LLM.
- Then measure whether query generation and LLM reranking still earn their latency.

Keeps: indexer service, its image and CI, k3d-based e2e tests, HANA docs table, embedding model
dependency on both sides. Choose only if HANA for docs is a fixed requirement.

### Pathway B: docs as a build artifact with in-process search and agent tools (recommended)

- Docs fetched at build time from the lockfile, shipped in the app image or as a separate docs
  artifact (see section 4).
- Lexical index (BM25 or similar) built in-process at startup; a few megabytes, under a second.
- Agent tools: `search` (titles, URLs, snippets), `read` (full page or section by id), `list`
  (sidebar tree per module). The table of contents can live in the system prompt if the serving
  model caches prompts.
- Whole pages returned, with citable public URLs.
- If the eval shows vague queries need semantic recall, add embeddings computed at build time and
  stored as a file next to the docs (small in-memory matrix), still without HANA.

Removes: indexer service, its e2e tests, the HANA docs table, and the query-generation and reranking
calls. Costs: one to three agent turns per docs question, freshness bounded by rebuild cadence.

### Pathway C: pure agentic navigation, no index

- Table of contents in the prompt, plus `grep` and `read` tools.
- Simplest possible build. Relies entirely on the model choosing from titles; vague queries suffer.
- B is C plus a search tool, so C is the minimal form of B rather than a separate bet.

### Comparison

| | A: fix HANA RAG | B: artifact + tools | C: navigation only |
|---|---|---|---|
| Components removed | none | indexer, HANA docs table, k3d e2e | same as B |
| Freshness | scheduled index run | rebuild or artifact cadence | rebuild or artifact cadence |
| Per-query cost | 2 LLM calls + 5 embeddings before the agent acts | 1 to 3 agent turns | 2 to 4 agent turns |
| Vague-query recall | good | good with embeddings file, fair without | weak |
| Provenance and links | needs metadata work | by construction | by construction |
| Effort | medium, many separate fixes | medium, one rebuild | low |

### Alternatives considered and rejected

- **Whole corpus in context:** not viable as the only method (about one million tokens). Viable per
  module, which Pathway B's `read` tool covers.
- **Fine-tuning:** docs change too often; model availability on SAP AI Core.
- **GraphRAG / knowledge graph:** overkill for a corpus of this size and structure.
- **Server-side embeddings in HANA:** removes SAP AI Core embedding calls but ties both sides to
  HANA's embedding model. Not a starting point.
- **External doc-site search APIs:** less control, external dependency.

## 4. Delivery options for Pathway B (how docs reach the pod)

All fetch the pinned commits from the lockfile, so builds are reproducible. They differ in how
tightly docs freshness is coupled to app releases.

| Option | How | When to pick |
|---|---|---|
| Docs inside the app image | Docs update = lockfile merge + normal image build. | App releases are frequent. |
| Separate docs artifact + init container | Small docs image built from its own lockfile, tagged by date or lock hash. Init container copies files into an emptyDir; the app builds its index from files. Pinned by digest in the deployment. | App releases are infrequent. Recommended default. |
| Docs service sidecar | Long-running container owning docs and index, exposing `search`/`read`/`list` over localhost. Native sidecar (init container with `restartPolicy: Always`) works on Kyma's Kubernetes versions; localhost calls need no Istio configuration. | Index gets heavier (embeddings), or other consumers appear (Busola, bots). Same docs image, promoted without changing agent tools. |
| Syncing sidecar (git-sync style) | Pulls upstream at runtime. | Avoid. Reintroduces the invisible moving target, needs network and credentials on every pod. |
| Fetch at startup from GitHub | No rebuild. | Avoid. Loses reproducibility, startup depends on GitHub. |

## 5. Add-ons that fit any pathway

- **CRD schemas as reference entries:** kind, field path, description from `config/crd/bases/`.
  Answers exact-identifier questions that prose handles badly.
- **Release notes with version metadata:** per-module release notes, filterable by the module
  version seen on the cluster.
- **Section type from the sidebar:** concept, tutorial, reference, troubleshooting. Lets error
  queries prefer troubleshooting pages.
- **Filter or boost by installed modules:** the agent can read the module list from the cluster.
- **Version-aware retrieval:** pin sources to the release branch matching the channel users run.
- **Synthetic questions per document:** generated once, embedded alongside the page.
- **Retrieval logging in Langfuse:** query, candidates, cited documents. Queries with no cited
  document are docs gaps and become the eval set. Report gap themes upstream to module docs teams.
- **Kubernetes docs:** kubernetes.io content repo (Hugo, frontmatter, clear tree). Large; scope to
  concepts and tasks and decide deliberately.
- **Snapshot tests for chunking or page preparation:** commit the prepared output for fixture docs
  so every change is a reviewable diff.
- **Verify command:** counts per module, empty modules, oversized pages, duplicates, unresolved
  sidebar links.
- **Housekeeping:** delete `MarkdownIndexer`, the `tree` subprocess call, fix the `INDEX_TO_FILE`
  boolean parsing.

## 6. Suggested sequence

1. Build the retrieval eval set and the discovery/lockfile groundwork. Both are needed by every
   pathway.
2. Prototype Pathway B in a branch. The agent tool interface already exists, so the change is small.
3. Run the eval against the current system.
4. If B matches or beats A on recall, cut the indexer. If it loses on vague queries, add the
   embeddings file before considering A.
5. Deliver docs via a separate artifact and init container; promote to a service sidecar only when
   the index or the consumer set grows.
6. Add CRD schemas, link rewriting and retrieval logging first among the add-ons, since they change
   what users see in answers.

## 7. How Kyma Companion uses the RAG system (added 2026-09-11)

Reviewed after the options above were written. It reinforces Pathway B and reorders priorities.

### Consumers

- One consumer: the `search_kyma_doc` tool bound into `KymaReActAgent`, plus
  `POST /api/tools/kyma/search`, which exposes the same tool to external callers and returns a
  list of plain strings. Follow-up and initial question generation do not use docs.
- The agent prompt (`REACT_AGENT_INSTRUCTIONS`) calls for doc search in two cases: after
  `kyma_query_tool` finds a Kyma-related problem in a resource, and for concept or how-to questions.
  It is forbidden when the resource is healthy or the problem is not Kyma-related.
- The dominant path is therefore troubleshooting-driven. The agent has already seen a resource
  kind, a status condition and often an error message, and formulates the search query itself.
- The tool returns bare page text joined by separators. No titles, URLs or module. The agent cannot
  cite, and the A2A response has no field for references, so Busola cannot render links.
- Busola sends navigation context (resource kind, name, namespace). The module is derivable from
  the kind, but nothing uses it to scope retrieval.
- Langfuse traces the search tool unmasked (`allowed_tools`), so retrieval logging is nearly free.

### What the blackbox eval shows

- Baseline: `search_kyma_doc` called in 9 of 25 queries; all 8 concept scenarios pass.
- Concept expectations are loose ("mentions Kubernetes", "mentions BTP") and satisfiable from model
  knowledge alone. No scenario checks the troubleshooting path where docs matter most, and none
  checks grounding in a specific document.
- Consequence: it is currently impossible to tell whether the RAG stack contributes anything.
- Cheap first experiment: run the suite with the search tool stubbed to return
  "No relevant documentation found." and compare scores.

### What changes in the recommendation

- Design the agent's documentation capability first, not the indexer. Inputs: user query, resource
  kind, module, status or error text, installed modules and versions. Outputs: page content plus
  title and public URL, so answers can carry citations. The retrieval implementation behind that
  interface is a swappable detail.
- The search step must handle error text and identifiers well: lexical search, troubleshooting
  pages tagged by section type. CRD schemas and status-condition documentation move from add-on to
  core.
- Whole pages matter more than weighted above: troubleshooting pages are short symptom, cause and
  remedy documents that lose meaning as chunks.
- Module scoping from the Busola context is a free precision win and belongs in the tool interface.
- Add eval scenarios with doc-grounded expectations for the troubleshooting path (for example,
  "explains the deprecated `accessStrategies` field on APIRule v2 and names the replacement").
- The REST search endpoint is a contract with an unknown consumer. Adding titles and URLs to its
  response needs coordination.
- Minor: `KYMA_AGENT_PROMPT` says "always call `search_kyma_doc` before technical guidance" while
  the active `REACT_AGENT_INSTRUCTIONS` say "only when". The former appears unused; confirm and
  delete.

## 8. Agentic doc-selection workflow (added 2026-09-11)

Context: the production indexer runs as a weekly CronJob outside this repo. Proposal: replace the
hand-picked source list with an agent that selects docs. Assessment: yes, with the constraint that
the agent proposes and a merged PR decides. An agent writing the index directly reintroduces the
invisible moving target, with nondeterminism on top.

### Shape

1. **Deterministic resolvers first** (section 2): site deploy matrix, sidebars, SAP Help TOC,
   tutorial tags, archived-repo detection. Cheap, testable, reproducible.
2. **Agent classifies the residue**, with a one-line rationale per item:
   - fetched Markdown files that no sidebar references;
   - new repos in the `kyma-project` org or newly added to the site matrix;
   - SAP Help pages outside Kyma-titled subtrees that mention Kyma;
   - pages with substantial changes that may affect eval coverage;
   - sources never retrieved or cited in production (from Langfuse traces), as drop candidates.
3. **Output is a PR**: bumps the lockfile and source config; body is the change report with
   added, removed and changed pages, the agent's include/exclude proposals with reasons, and
   anything it was unsure about. A human merges.
4. **Merge triggers the build**: under Pathway A the CronJob becomes "index from the lockfile",
   triggered by the merge rather than the calendar; under Pathway B the CronJob disappears and the
   merge triggers a docs artifact build.

### Beyond selection

The agent sees every changed page, so it can also draft eval questions for new or changed docs,
flag broken or duplicated pages, and compile a monthly docs-gap list for upstream module teams.
This makes it a docs curator rather than only a selector.

### Guardrails

- Labeled set of past include/exclude decisions; measure agreement before trusting it.
- Restrict it to the weekly delta, never the whole corpus.
- Explicit allowlist and denylist override the agent.
- All decisions land in git via the PR, so they are reviewable and reversible.

## 9. Docs curator: concrete design (added 2026-09-11)

A concrete design for the workflow described in section 8. Names are proposals.

### Design decisions

- **Plain Python CLI, not a free-form coding agent.** The decisions must be structured, cached,
  diffable and evaluated against labels. A Python tool that calls the LLM only for the residue
  gives that; a free-form agent action does not. The tool reuses the model factory and the AI Core
  config secret the indexer already has.
- **Three files carry the state**, all in git:
  - `docs_sources.yaml`: declarative intent (which resolvers, which repos, allow/deny lists).
  - `docs_sources.lock.json`: the resolved truth (commit per repo, every selected file with hash,
    title, URL, module, doc type, and who decided: resolver, allowlist or agent).
  - `curation/decisions.jsonl`: the agent's past decisions keyed by repo, path and content hash,
    so a file is classified once and re-runs are free and deterministic.
- **The lock is derived, never hand-edited.** A CI check re-runs the resolver and fails if the
  committed lock differs from the computed one. Reviewers change the YAML or the decisions file,
  not the lock.
- **Phased delivery.** Phase 1 has no LLM at all and already delivers the visibility. Phase 2 adds
  the classifier. Phase 3 adds eval drafting and usage statistics.

### Layout

```
doc_indexer/
  docs_sources.yaml            # intent
  docs_sources.lock.json       # resolved truth (derived)
  curation/
    decisions.jsonl            # agent decisions cache, committed
    labels.jsonl               # human-labeled include/exclude set for classifier eval
    report-template.md
  src/curator/
    cli.py                     # resolve | classify | diff | write-lock | check | eval-classifier
    resolvers/
      kyma_site.py             # deploy matrix + _sidebar.ts
      sap_help_toc.py          # docs/index.md subtrees
      frontmatter_tag.py       # sap-tutorials
      docs_user_convention.py  # kyma-project repos with docs/user, archived detection
    github.py                  # API: branch head, repo metadata, tarball at SHA
    classify.py                # LLM classification of the residue
    lock.py                    # lock model, load/write/compare
    report.py                  # PR body
.github/workflows/
  docs-curator.yaml            # weekly + manual
  docs-lock-check.yaml         # PR check: lock == resolve(config)
```

### `docs_sources.yaml`

```yaml
sources:
  - name: kyma-site
    resolver: kyma-site
    site_repo: kyma-project/kyma          # deploy matrix read from .github/workflows/deploy.yml
    ref: main
  - name: sap-help
    resolver: sap-help-toc
    repo: SAP-docs/btp-cloud-platform
    ref: main
    toc: docs/index.md
    subtree_title_match: "(?i)kyma"
    allow: []                              # pages outside the subtrees, by path
  - name: sap-tutorials
    resolver: frontmatter-tag
    repos: [sap-tutorials/btp-foundation, sap-tutorials/btp-dev-guidance]
    tag: "software-product>sap-btp, kyma-runtime"
  - name: kyma-org-extra
    resolver: docs-user-convention
    org: kyma-project
    repos: [lifecycle-manager, modulectl, kyma-environment-broker]   # explicit opt-in
policy:
  deny_globs: ["**/_sidebar.*", "**/CLAUDE.md", "**/adr/**"]
  residue_to_agent: true                   # phase 2 switch
```

### Lock entry

```json
{
  "repo": "kyma-project/istio",
  "commit": "3f2c…",
  "path": "docs/user/troubleshooting/03-20-connection-refused.md",
  "sha256": "9a1b…",
  "title": "Connection Refused Errors",
  "url": "https://kyma-project.io/external-content/istio/docs/user/troubleshooting/03-20-connection-refused",
  "module": "istio",
  "doc_type": "troubleshooting",
  "decided_by": "resolver:kyma-site",
  "rationale": null
}
```

`doc_type` comes from the sidebar section title (Tutorials, Technical Reference, Troubleshooting)
for the site resolver, from the TOC branch for SAP Help, and from the agent for residue.

### Weekly workflow, step by step

1. **Resolve refs.** For every repo, read the branch head via the GitHub API. Record commit and
   whether the repo is archived. Download the tarball at that exact commit.
2. **Run resolvers.** Each produces `selected` entries and `residue` candidates:
   - kyma-site: parse the deploy matrix for the repo list; parse each `_sidebar.ts` for links,
     titles and section; every linked file is selected. Markdown under `docs/user` not linked from
     the sidebar is residue with reason `orphan`. Repos in the matrix but not in the last lock are
     residue with reason `new-repo`.
   - sap-help-toc: parse `docs/index.md`; files under Kyma-titled subtrees are selected; files
     elsewhere whose text mentions Kyma are residue with reason `outside-toc`.
   - frontmatter-tag: files with the tag are selected.
   - docs-user-convention: `docs/user/**` for opted-in repos; archived repos are dropped and
     reported. New non-archived org repos with a `docs/user` directory and not in any list are
     residue with reason `new-org-repo`.
   - Changed pages: any selected file whose hash differs from the lock is tagged `changed`, with
     line counts from a diff against the previous content.
3. **Classify residue** (phase 2). Skip anything present in `decisions.jsonl` with the same
   content hash. Batch the rest, about 20 per call, to the mini model with structured output:

   ```json
   {"decision": "include|exclude|unsure",
    "doc_type": "concept|tutorial|reference|troubleshooting|release-notes|contributor|other",
    "module": "istio|null",
    "confidence": 0.0,
    "rationale": "one sentence"}
   ```

   Input per candidate: repo, path, H1, first 600 tokens, directory, residue reason, and the
   sidebar or TOC context if any. The prompt states the rule: user-facing Kyma or SAP BTP Kyma
   runtime documentation is included; contributor, ADR, CI, benchmark and internal design material
   is excluded; anything else is unsure. Few-shot examples come from `labels.jsonl`. Temperature 0.
   Results are appended to `decisions.jsonl`. `unsure` never enters the lock; it goes to the PR.
   If the LLM call fails, the run still completes and the residue is reported as unclassified.
4. **Write the lock** from selected plus agent-included entries.
5. **Diff against the committed lock** and render the report.
6. **Open or update the PR** on branch `docs-curator/weekly` with the lock, decisions file and
   report. Reuse the open PR if one exists. Label `docs-sources`. No PR when the diff is empty.

Workflow essentials: `schedule` weekly plus `workflow_dispatch`; permissions `contents: write`
and `pull-requests: write`; `concurrency` on the branch name; secrets are the existing AI Core
config and the default `GITHUB_TOKEN` (public repos only, well within rate limits).

### PR body

- Summary counts: pages selected, added, removed, changed; repos added, archived.
- **Needs a decision**: task-list checkboxes for `unsure` items and `new-repo` findings, each with
  the agent's rationale and a link to the file. The reviewer resolves them by editing
  `docs_sources.yaml` (allow or deny) or `decisions.jsonl` in the same PR.
- **Added pages** grouped by module, with `decided_by` and rationale where the agent decided.
- **Removed pages** with reason: deleted upstream, dropped from sidebar, repo archived, agent
  exclusion.
- **Changed pages** with lines added and removed and a link to the file at the new commit, and a
  compare link between the two commits per repo.
- **Unclassified** (only if the LLM step failed).

### Review and merge

- The `docs-lock-check` workflow runs on the PR: recompute the lock from the YAML and decisions
  file at the pinned commits and fail if it differs. This makes the lock a pure function of the
  reviewed inputs.
- Merge to `main` triggers, by path filter on the lock file:
  - Pathway A: the indexer image build; the weekly CronJob picks up the new image on the next
    deploy. To index immediately, a manual job run on the cluster is still needed and lives
    outside this repo.
  - Pathway B: the docs artifact build, tagged with the lock hash; the app deployment pins it.

### Classifier quality

- `labels.jsonl` starts from the current `docs_sources.json`: every currently included file is a
  positive, every explicit exclusion and every contributor or ADR file is a negative. Add every
  reviewer correction from PRs.
- `curator eval-classifier` reports precision and recall on `labels.jsonl` and runs in CI whenever
  the prompt or the model changes. Set a floor before phase 2 is switched on.

### Phase 3 additions

- **Eval drafts.** For each substantially changed or added page, ask the model for one or two
  questions and the statement a correct answer must contain. Written to
  `curation/retrieval_eval_proposals.jsonl` in the PR; the reviewer keeps or deletes them and
  accepted ones move into the retrieval eval set.
- **Usage statistics.** Query Langfuse for `search_kyma_doc` traces over the last 30 days, count
  retrievals and citations per page, and list pages with zero hits as drop candidates. Requires
  page identity in the tool output, which Pathway B provides.
- **Upstream gap report.** Monthly list of query themes with no retrieved or cited page, grouped by
  module, for the module docs teams.

### Known fiddly bits

- `_sidebar.ts` is TypeScript, not JSON. The files are uniform object literals, so a small
  tolerant parser works; validate it against all 16 sidebars in a unit test and fail loudly on a
  parse error rather than silently selecting nothing.
- Some sidebar links omit the `.md` suffix or point to directories with a README. Normalize before
  matching.
- The SAP Help TOC nests by indentation; one page can appear under several branches. Deduplicate
  by path and keep the first Kyma branch as the doc type source.
- Codeload tarballs at a full SHA are supported, so pinned downloads need no git.
