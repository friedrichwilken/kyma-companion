"""Unit tests for the docs.DocIndex class."""

import json
import os
from pathlib import Path

import pytest

from docs import DocIndex, DocPage

# Number of .md files created by the docs_dir fixture.
FIXTURE_PAGE_COUNT = 4
# Number of Eventing pages in the fixture (overview.md + advanced/scaling.md).
FIXTURE_EVENTING_PAGE_COUNT = 2
# top_k cap used in the top_k-limit test.
SEARCH_TOP_K_LIMIT = 2

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def docs_dir(tmp_path: pytest.TempPathFactory) -> str:
    """Build a minimal docs artifact directory with two modules.

    Layout::

        <tmp>/
          eventing-manager/
            meta.json           # repo, module, base_url
            overview.md
            advanced/
              scaling.md
          serverless/
            meta.json
            getting-started.md
          no-meta/              # module dir without meta.json
            plain.md
    """
    root = tmp_path  # type: ignore[arg-type]

    # --- eventing-manager module ---
    eventing = root / "eventing-manager"
    eventing.mkdir()
    (eventing / "meta.json").write_text(
        json.dumps(
            {
                "repo": "kyma-project/eventing-manager",
                "module": "Eventing",
                "base_url": "https://kyma-project.io/docs/eventing",
            }
        ),
        encoding="utf-8",
    )
    (eventing / "overview.md").write_text(
        "# Eventing Overview\n\nEventing lets you publish and subscribe to events.\n",
        encoding="utf-8",
    )
    advanced = eventing / "advanced"
    advanced.mkdir()
    (advanced / "scaling.md").write_text(
        "# Scaling Eventing\n\nYou can scale the NATS server by adjusting replicas.\n",
        encoding="utf-8",
    )

    # --- serverless module ---
    serverless = root / "serverless"
    serverless.mkdir()
    (serverless / "meta.json").write_text(
        json.dumps(
            {
                "repo": "kyma-project/serverless",
                "module": "Serverless",
                "base_url": "https://kyma-project.io/docs/serverless",
            }
        ),
        encoding="utf-8",
    )
    (serverless / "getting-started.md").write_text(
        "# Getting Started with Serverless\n\nDeploy your first serverless function.\n",
        encoding="utf-8",
    )

    # --- no-meta dir (no meta.json) ---
    no_meta = root / "no-meta"
    no_meta.mkdir()
    (no_meta / "plain.md").write_text(
        "# Plain Doc\n\nSome content without module metadata.\n",
        encoding="utf-8",
    )

    return str(root)


@pytest.fixture()
def loaded_index(docs_dir: str) -> DocIndex:
    """Return a DocIndex that has already been loaded from *docs_dir*."""
    index = DocIndex(docs_dir)
    index.load()
    return index


# ---------------------------------------------------------------------------
# Empty index
# ---------------------------------------------------------------------------


def test_empty_index_not_loaded() -> None:
    """A freshly constructed DocIndex reports is_loaded=False."""
    index = DocIndex("/nonexistent/path")
    assert not index.is_loaded
    assert index.page_count == 0


def test_empty_index_search_returns_empty(tmp_path: pytest.TempPathFactory) -> None:
    """Searching an unloaded (empty) index returns an empty list."""
    index = DocIndex(str(tmp_path))
    assert index.search("anything") == []


def test_empty_docs_dir(tmp_path: pytest.TempPathFactory) -> None:
    """Loading an empty directory succeeds and leaves the index empty."""
    index = DocIndex(str(tmp_path))
    index.load()
    assert index.is_loaded
    assert index.page_count == 0
    assert index.search("anything") == []


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def test_load_page_count(loaded_index: DocIndex) -> None:
    """All .md files under docs_dir are indexed (4 pages expected)."""
    assert loaded_index.page_count == FIXTURE_PAGE_COUNT


def test_load_is_loaded(loaded_index: DocIndex) -> None:
    """is_loaded is True after load() returns."""
    assert loaded_index.is_loaded


def test_load_title_extraction(loaded_index: DocIndex) -> None:
    """Title is extracted from the first H1 heading."""
    page = loaded_index.read("kyma-project/eventing-manager::overview.md")
    assert page is not None
    assert page.title == "Eventing Overview"


def test_load_url_with_base_url(loaded_index: DocIndex) -> None:
    """URL is formed from base_url + path when meta.json provides base_url."""
    page = loaded_index.read("kyma-project/eventing-manager::overview.md")
    assert page is not None
    assert page.url == "https://kyma-project.io/docs/eventing/overview.md"


def test_load_url_nested_file(loaded_index: DocIndex) -> None:
    """URL for a nested file includes the subdirectory segment."""
    page = loaded_index.read("kyma-project/eventing-manager::advanced/scaling.md")
    assert page is not None
    assert page.url == "https://kyma-project.io/docs/eventing/advanced/scaling.md"


def test_load_url_fallback_no_base_url(loaded_index: DocIndex) -> None:
    """URL falls back to repo/path when meta.json has no base_url."""
    page = loaded_index.read("no-meta::plain.md")
    assert page is not None
    # repo falls back to dir name "no-meta"
    assert "no-meta" in page.url
    assert "plain.md" in page.url


def test_load_module_from_meta(loaded_index: DocIndex) -> None:
    """Module name is read from meta.json."""
    page = loaded_index.read("kyma-project/eventing-manager::overview.md")
    assert page is not None
    assert page.module == "Eventing"


def test_load_module_empty_without_meta(loaded_index: DocIndex) -> None:
    """Module is empty string when no meta.json is present."""
    page = loaded_index.read("no-meta::plain.md")
    assert page is not None
    assert page.module == ""


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


def test_search_returns_results(loaded_index: DocIndex) -> None:
    """search() returns a non-empty list for a relevant query."""
    results = loaded_index.search("eventing overview")
    assert len(results) > 0
    assert all(isinstance(r, DocPage) for r in results)


def test_search_ranked_results(loaded_index: DocIndex) -> None:
    """The most relevant page appears first for a specific query."""
    results = loaded_index.search("NATS replicas scaling")
    assert len(results) > 0
    assert results[0].title == "Scaling Eventing"


def test_search_top_k_respected(loaded_index: DocIndex) -> None:
    """search() never returns more than top_k results."""
    results = loaded_index.search("the", top_k=SEARCH_TOP_K_LIMIT)
    assert len(results) <= SEARCH_TOP_K_LIMIT


def test_search_module_filter(loaded_index: DocIndex) -> None:
    """search() with a module filter only returns pages from that module."""
    results = loaded_index.search("overview", module="Serverless")
    assert all(r.module == "Serverless" for r in results)


def test_search_module_filter_fallback(loaded_index: DocIndex) -> None:
    """search() falls back to global results when the module filter yields nothing."""
    results = loaded_index.search("serverless function", module="NonexistentModule")
    assert len(results) > 0


def test_search_module_filter_case_insensitive(loaded_index: DocIndex) -> None:
    """Module filter comparison is case-insensitive."""
    results_lower = loaded_index.search("eventing", module="eventing")
    results_mixed = loaded_index.search("eventing", module="EVENTING")
    assert len(results_lower) == len(results_mixed)


# ---------------------------------------------------------------------------
# read()
# ---------------------------------------------------------------------------


def test_read_existing_page(loaded_index: DocIndex) -> None:
    """read() returns the correct DocPage for a valid page_id."""
    page = loaded_index.read("kyma-project/serverless::getting-started.md")
    assert page is not None
    assert page.repo == "kyma-project/serverless"
    assert page.path == "getting-started.md"
    assert page.module == "Serverless"


def test_read_nonexistent_page(loaded_index: DocIndex) -> None:
    """read() returns None for an unknown page_id."""
    assert loaded_index.read("kyma-project/unknown::no-such-file.md") is None


def test_read_page_content(loaded_index: DocIndex) -> None:
    """read() returns a page with the full Markdown content."""
    page = loaded_index.read("kyma-project/eventing-manager::overview.md")
    assert page is not None
    assert "publish and subscribe" in page.content


# ---------------------------------------------------------------------------
# list_module()
# ---------------------------------------------------------------------------


def test_list_module_all(loaded_index: DocIndex) -> None:
    """list_module() with no argument returns all pages."""
    pages = loaded_index.list_module()
    assert len(pages) == loaded_index.page_count


def test_list_module_filtered(loaded_index: DocIndex) -> None:
    """list_module('Eventing') returns only Eventing pages."""
    pages = loaded_index.list_module("Eventing")
    assert len(pages) == FIXTURE_EVENTING_PAGE_COUNT
    assert all(p.module == "Eventing" for p in pages)


def test_list_module_sorted(loaded_index: DocIndex) -> None:
    """list_module() results are sorted by (module, path)."""
    pages = loaded_index.list_module()
    keys = [(p.module, p.path) for p in pages]
    assert keys == sorted(keys)


def test_list_module_empty_filter(loaded_index: DocIndex) -> None:
    """list_module('NonexistentModule') returns an empty list."""
    pages = loaded_index.list_module("NonexistentModule")
    assert pages == []


def test_list_module_case_insensitive(loaded_index: DocIndex) -> None:
    """list_module() module matching is case-insensitive."""
    pages_lower = loaded_index.list_module("serverless")
    pages_upper = loaded_index.list_module("SERVERLESS")
    assert len(pages_lower) == len(pages_upper) == 1


# ---------------------------------------------------------------------------
# Idempotency / reload
# ---------------------------------------------------------------------------


def test_reload_is_idempotent(docs_dir: str) -> None:
    """Calling load() twice produces the same page count."""
    index = DocIndex(docs_dir)
    index.load()
    count_first = index.page_count
    index.load()
    assert index.page_count == count_first


def test_reload_with_new_file(docs_dir: str) -> None:
    """A new .md file is picked up after a reload."""
    index = DocIndex(docs_dir)
    index.load()
    before = index.page_count

    new_file = os.path.join(docs_dir, "eventing-manager", "new-page.md")
    with open(new_file, "w", encoding="utf-8") as fh:
        fh.write("# New Page\n\nFresh content.\n")

    index.load()
    assert index.page_count == before + 1


# ---------------------------------------------------------------------------
# Title weighting
# ---------------------------------------------------------------------------


def test_multi_word_title_outranks_body_mention(tmp_path: Path) -> None:
    """A page whose multi-word title matches the query ranks above a page that only mentions the words in its body.

    Regression test: repeating the title with string multiplication fused the
    last and first words of adjacent copies ("Kyma ModulesKyma Modules"), so
    multi-word titles received almost no weight and a body with two mentions
    outranked an exact title match.
    """
    root = tmp_path / "kyma"
    root.mkdir()
    (root / "modules.md").write_text("# Kyma Modules\n\nShort page about something.\n", encoding="utf-8")
    (root / "other.md").write_text("# Other Topic\n\nkyma modules kyma modules kyma modules\n", encoding="utf-8")
    # Filler pages so that the query terms are not present in every document
    # (BM25 IDF degenerates on a two-page corpus).
    for i in range(3):
        (root / f"filler-{i}.md").write_text(f"# Filler {i}\n\nUnrelated text about nothing.\n", encoding="utf-8")
    index = DocIndex(str(tmp_path))
    index.load()
    results = index.search("Kyma modules")
    assert results[0].title == "Kyma Modules"
