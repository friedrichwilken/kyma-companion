# Kyma Documentation Indexer

Kyma Documentation Indexer
This project implements a documentation indexing system for Kyma that stores the indexed content in SAP HANA Cloud DB. 
The system processes Markdown files, splits them into meaningful chunks based on headers, and creates searchable vector embeddings.

## Concepts
The indexer splits the documentation content into chunks based on the provided headers and creates vector embeddings for each chunk. 
It uses GPT embedding models to create the embeddings. 
The embeddings are stored in SAP HANA Cloud DB, which allows for fast and efficient search queries.

## Development

To run the project locally, follow these steps:

1. Install the dependencies:

```bash
poetry install
```

2. Prepare the `config-doc-indexer.json` file based on the [template](../config/config-example.json).

3. Run the fetcher to pull documents from the specified sources in the `docs_sources.json` [file](./docs_sources.json):

```bash
poetry run python src/main.py fetch
```

4. Run the indexer to create embeddings for the fetched documents:
```bash
poetry run python src/main.py index
```

## Testing

The `config.json` file must be present for integration tests (see [template](../config/config-example.json)).

### Test structure

| Layer | Location | Description |
|---|---|---|
| Unit | `tests/unit/` | Fast tests with no external dependencies. All external calls are mocked. |
| Integration | `tests/integration/` | Tests that make real API calls to the embedding service and SAP AI Core, including a full end-to-end test that writes to a temporary Hana DB table. |

A missing config is a hard failure — there are no silent skips.

In CI, the e2e table is named `kc_pr_<PR number>_e2e` so orphaned tables can be traced back to the PR that created them. Locally a UUID is used (`test_e2e_<uuid>_e2e`).

### Running tests

Run unit tests:
```bash
poetry run poe test-unit
```

Run integration tests:
```bash
poetry run poe test-integration
```

Run all tests:
```bash
poetry run poe test
```

### Key regression tests

- **`tests/unit/test_main.py::test_run_indexer_passes_model_name_not_deployment_id`** — verifies that `run_indexer()` passes the model name (not the deployment ID) to the embedding factory.
- **`tests/integration/test_main.py::test_run_indexer_embedding_model_creation`** — positive check: model creation via the exact production sequence produces a working embeddings model.
- **`tests/integration/test_main.py::test_run_indexer_fails_when_deployment_id_passed_as_model_name`** — negative check: passing a deployment ID instead of a model name raises `ValueError`.
- **`tests/integration/test_main.py::test_run_indexer_e2e`** — full end-to-end: indexes real documents into a temporary Hana DB table and verifies chunks were stored.

## Static Code Analysis
```bash
poetry run poe codecheck
```

## Curated corpus with pinakes

The documentation corpus can also be compiled with [pinakes](https://github.com/friedrichwilken/pinakes), a
standalone Rust tool that turns `pinakes.yaml` into a reproducible, measured corpus: a committed
`manifest.json` (every selected page, its hash, title and what selected it), `residue.jsonl` (what a
resolver left out, for review), `duplicates.jsonl` (near-duplicate and mirror pages across sources) and
an `artifact/` directory in the exact layout `src/docs/index.py` already reads. It is a drop-in
alternative to `python src/main.py fetch`, not a replacement for it yet — see "What still uses the
Python fetch" below.

### What the config is

`doc_indexer/pinakes.yaml` declares the same sources as `docs_sources.json`, converted to pinakes's
resolver types:

- Module repositories with a `docs/user/_sidebar.ts` use the built-in `vitepress` resolver.
- `btp-cloud-platform` (the SAP Help table of contents) and the two `sap-tutorials` repositories use
  `external` resolvers backed by `doc_indexer/resolvers/sap_help_toc.py` and `tutorials.py` — dependency
  -free reimplementations of the retired `sap_help_toc` / `tutorials` Python resolvers in
  `src/fetcher/resolvers.py`, emitting pinakes's external resolver JSONL contract on stdout.
- Repositories with no sidebar (`kyma`, `lifecycle-manager`, `modulectl`, `kyma-environment-broker`) use
  a `glob` resolver with the old hand-picked include patterns.
- Eight module repos also get a second `<name>-crds` source that renders `config/crd/bases/*.yaml` into
  reference pages with pinakes's built-in `openapi` renderer.

pinakes's `vitepress` resolver has no per-source `include` key, unlike the retired Python `sidebar`
resolver, which always added a module's landing README even when the sidebar does not link it. The
equivalent here is `decisions.jsonl`: the resolver's residue `scope` is widened to also cover the landing
README and the old `include_files` extras, and `pinakes decide <id> include --reason "…"` selects them
once resolved, without changing which source a page belongs to (which matters because
`evaluation/queries.jsonl` expects ids of the form `<source>/<path>`).

### Running it locally

```bash
cd doc_indexer
pinakes resolve          # network: downloads every source, writes manifest.json, residue.jsonl, artifact/
pinakes eval              # measures evaluation/queries.jsonl against the artifact: table on stderr, JSON on stdout
pinakes duplicates > duplicates.jsonl
pinakes verify            # checks the committed manifest still matches the config, the artifact and policy
pinakes report --old manifest.json > report.md   # sanity-check the report renders; a real diff needs an older manifest
```

`pinakes` is not packaged for this repository; build it from
[friedrichwilken/pinakes](https://github.com/friedrichwilken/pinakes) (pinned commit
`a990185fa22ba4c93b8f9c1c191a92cdd7f50bbe` — see `.github/workflows/curate-docs.yaml` for the exact
steps) with `cargo build --release` and put `target/release/pinakes` on `PATH`.

After a fresh `resolve`, some pages the vitepress resolver did not select land in `residue.jsonl`
instead of the manifest; if they should be part of the corpus, decide them and re-resolve:

```bash
pinakes decide '<source>::<path>' include --reason "…" --by "<you>"
pinakes resolve
```

### What the workflow does

`.github/workflows/curate-docs.yaml` (`workflow_dispatch` only) builds pinakes from source at the pinned
commit, re-resolves `pinakes.yaml`, diffs the result against the committed `manifest.json` and stops when
nothing changed (unless the `force` input is set), measures recall/MRR before and after with `pinakes
eval`, runs `pinakes duplicates`, and opens a pull request on branch `pinakes/curated-docs` with
`manifest.json`, `residue.jsonl` and `duplicates.jsonl` and the rendered `report.md` as the PR body.
`decisions.jsonl` is not touched by the workflow — new residue is left for a human (or the `curate` skill
in the pinakes repository) to decide in a follow-up commit.

### How a reviewer reads the PR

The PR body (`pinakes report`) is ordered: a summary (source, page and residue counts, how many
decisions exist); the eval table before and after, overall and per query kind; added, removed and
changed pages (changed pages link to the upstream compare when both commits are known); new residue,
grouped by reason with an excerpt; expired decisions (a decided page's content changed, so its `sha256`
no longer matches and it needs a fresh look); unresolved sidebar links; and archived sources.

- **New residue** is the main thing to triage: run `pinakes residue list --source <name>` for the
  full excerpt and context, then `pinakes decide <id> include|exclude|unsure --reason "…"` (append-only,
  keyed to the page's hash, so a later content change makes pinakes ask again).
- **Duplicates** (`duplicates.jsonl`) are already resolved automatically at search time by the same-title
  mirror rule (the higher-`priority` source wins), so acting on them is optional curation, not a
  correctness fix; `pinakes decide <duplicate-id> exclude --superseded-by <canonical-id>` records a
  verdict when a mirror is confirmed unwanted.
- An eval regression beyond `eval.max_recall_drop` (0.05) is called out in the report but does not block
  the PR — the workflow does not run `eval --gate`, so a curator decides whether the drop is
  acceptable (e.g. a source that genuinely lost pages upstream) before merging.

### What still uses the Python fetch

`python src/main.py fetch` (`DocumentsFetcher`, `src/fetcher/`) remains the corpus builder's input until
the image build switches to `pinakes resolve --from-manifest doc_indexer/manifest.json --artifact
<DOCS_PATH>`, which reproduces the committed manifest byte for byte without needing network resolution
logic at build time. Until then, `pinakes.yaml`, `manifest.json`, `residue.jsonl` and `duplicates.jsonl`
are curated independently of `docs_sources.json`; keeping both in sync is manual.
