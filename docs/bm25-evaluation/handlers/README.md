# What the custom handlers do to a document

Two extension points of pinakes are used on `feat/curated-docs`. This directory shows each one
on a real document: the input on GitHub, the output as produced by `pinakes resolve` (1.0.3)
from the committed manifest.

## 1. The OpenAPI/CRD renderer (built-in `render: openapi`)

Input: the Subscription CRD of the Eventing module, plain Kubernetes YAML with an
`openAPIV3Schema`:
https://github.com/kyma-project/eventing-manager/blob/2c8aaf6d35375df777764b87ddae555ec44abbd4/config/crd/bases/eventing.kyma-project.io_subscriptions.yaml

Output: one reference page per served version, [`rendered-subscription-v1alpha2.md`](rendered-subscription-v1alpha2.md):
the title `Subscription (eventing.kyma-project.io/v1alpha2)`, the scope line, a Fields table with
dotted paths (`spec.sink`, `spec.types[]`, `spec.config.*`), required flags, allowed values and
the descriptions the schema carries, then the Status table. The page is indexed like any other,
with `doc_type: reference` and the CRD's group as its section, so a question about `spec.sink`
finds it directly.

A second example, the Istio module CR: [`rendered-istio-v1alpha2.md`](rendered-istio-v1alpha2.md), from
https://github.com/kyma-project/istio/blob/4427d7ba863973c2cea9da74ed8675c5c74aee77/config/crd/bases/operator.kyma-project.io_istios.yaml

## 2. The external resolver (`resolver: external`)

Input: the SAP Help Portal repository, 2,063 Markdown pages under `docs/`, and its table of
contents `docs/index.md`.

The script: [`doc_indexer/resolvers/sap_help_toc.py`](https://github.com/friedrichwilken/kyma-companion/blob/feat/curated-docs/doc_indexer/resolvers/sap_help_toc.py)
on `feat/curated-docs`, standard library only. It walks the table of contents, keeps the subtrees
whose entry title matches `(?i)kyma`, and prints one JSON line per Markdown file: selected pages
with title, doc type and section taken from the table of contents; every other page with
`"selected": false`.

Output on the real repository: 285 selected, 1,778 not. A sample of both kinds is in
[`sap_help_toc-sample-output.jsonl`](sap_help_toc-sample-output.jsonl). pinakes fetches only the
selected pages, reports the unselected ones that mention Kyma as residue, and never sees the rest.

The same contract serves the tutorial repositories through
[`resolvers/tutorials.py`](https://github.com/friedrichwilken/kyma-companion/blob/feat/curated-docs/doc_indexer/resolvers/tutorials.py),
which selects by path or frontmatter tag instead of a table of contents.
