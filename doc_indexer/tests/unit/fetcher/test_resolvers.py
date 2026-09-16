import glob
import os
from pathlib import Path

import pytest
from fetcher.resolvers import (
    DOC_TYPE_CONCEPT,
    DOC_TYPE_REFERENCE,
    DOC_TYPE_TROUBLESHOOTING,
    DOC_TYPE_TUTORIAL,
    classify_doc_type,
    parse_sidebar,
    resolve_sap_help_toc,
    resolve_sidebar,
    resolve_tutorials,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sidebars"
SIDEBAR_FIXTURE_COUNT = 16


def _count_links(nodes) -> int:
    return sum((1 if n.link else 0) + _count_links(n.items) for n in nodes)


def test_parse_every_published_module_sidebar() -> None:
    """Every sidebar the Kyma site publishes parses, and no link is lost."""
    files = sorted(glob.glob(str(FIXTURES / "*.ts")))
    assert len(files) == SIDEBAR_FIXTURE_COUNT
    for file in files:
        source = Path(file).read_text(encoding="utf-8")
        nodes = parse_sidebar(source)
        assert _count_links(nodes) == source.count("link:"), file


def test_parse_sidebar_keeps_hierarchy_and_unescapes_quotes() -> None:
    source = """export default [
      { text: 'Tutorials', link: './tutorials/README', collapsed: true, items: [
        { text: 'Reverting the module\\'s deletion', link: './tutorials/01-10-revert' },
      ] },
      { text: "Double quoted", link: "./double.md" },
    ];"""
    nodes = parse_sidebar(source)
    assert [n.text for n in nodes] == ["Tutorials", "Double quoted"]
    assert nodes[0].items[0].text == "Reverting the module's deletion"
    assert nodes[0].items[0].link == "./tutorials/01-10-revert"


def test_parse_sidebar_rejects_unbalanced_brackets() -> None:
    with pytest.raises(ValueError, match="unbalanced"):
        parse_sidebar("export default [ { text: 'a', link: './a.md' }")


@pytest.mark.parametrize(
    "title,ancestors,expected",
    [
        ("Istio Version", [], DOC_TYPE_CONCEPT),
        ("Connection Refused Errors", ["Troubleshooting"], DOC_TYPE_TROUBLESHOOTING),
        ("Enabling Istio Sidecar Injection", ["Istio Service Mesh"], DOC_TYPE_TUTORIAL),
        ("Istio Controller Parameters", ["Technical Reference"], DOC_TYPE_REFERENCE),
        ("Subscription CR", ["Resources"], DOC_TYPE_REFERENCE),
        ("Expose a Function", ["Tutorials"], DOC_TYPE_TUTORIAL),
        ("Kyma Modules", ["Basic Platform Concepts", "Environments", "Kyma Environment"], DOC_TYPE_CONCEPT),
    ],
)
def test_classify_doc_type(title: str, ancestors: list[str], expected: str) -> None:
    assert classify_doc_type(title, ancestors) == expected


@pytest.fixture()
def module_repo(tmp_path: Path) -> Path:
    """A module repository with a sidebar using every link spelling."""
    user = tmp_path / "docs" / "user"
    (user / "tutorials").mkdir(parents=True)
    (user / "troubleshooting").mkdir()
    (user / "README.md").write_text("# Module\n", encoding="utf-8")
    (user / "00-10-concept.md").write_text("# Concept\n", encoding="utf-8")
    (user / "tutorials" / "README.md").write_text("# Tutorials\n", encoding="utf-8")
    (user / "tutorials" / "01-10-do-it.md").write_text("# Do It\n", encoding="utf-8")
    (user / "troubleshooting" / "03-10-broken.md").write_text("# Broken\n", encoding="utf-8")
    (user / "orphan.md").write_text("# Orphan\n", encoding="utf-8")
    (user / "_sidebar.ts").write_text(
        """export default [
          { text: 'Module', link: './README.md' },
          { text: 'A Concept', link: './00-10-concept#anchor' },
          { text: 'Tutorials', link: './tutorials/README', collapsed: true, items: [
            { text: 'Do It', link: './tutorials/01-10-do-it' },
          ] },
          { text: 'Troubleshooting', link: './troubleshooting', collapsed: true, items: [
            { text: 'Broken', link: './troubleshooting/03-10-broken' },
            { text: 'Gone', link: './troubleshooting/03-20-gone' },
          ] },
        ];""",
        encoding="utf-8",
    )
    return tmp_path


def test_resolve_sidebar_selects_linked_pages_with_titles_and_types(module_repo: Path) -> None:
    selection = resolve_sidebar(str(module_repo))
    assert set(selection.pages) == {
        "docs/user/README.md",
        "docs/user/00-10-concept.md",
        "docs/user/tutorials/README.md",
        "docs/user/tutorials/01-10-do-it.md",
        "docs/user/troubleshooting/03-10-broken.md",
    }
    assert selection.pages["docs/user/00-10-concept.md"].title == "A Concept"
    assert selection.pages["docs/user/tutorials/01-10-do-it.md"].doc_type == DOC_TYPE_TUTORIAL
    assert selection.pages["docs/user/tutorials/01-10-do-it.md"].section == "Tutorials"
    assert selection.pages["docs/user/troubleshooting/03-10-broken.md"].doc_type == DOC_TYPE_TROUBLESHOOTING
    assert selection.orphans == ["docs/user/orphan.md"]
    # a directory link without README.md and a deleted page are both reported
    assert selection.unresolved == ["./troubleshooting", "./troubleshooting/03-20-gone"]


def test_resolve_sidebar_always_includes_landing_readme(tmp_path: Path) -> None:
    """The module README is the landing page on the site and is selected even without a sidebar entry."""
    user = tmp_path / "docs" / "user"
    user.mkdir(parents=True)
    (user / "README.md").write_text("# Istio Module\n\nBy default, the Istio module is added.\n", encoding="utf-8")
    (user / "page.md").write_text("# Page\n", encoding="utf-8")
    (user / "_sidebar.ts").write_text("export default [ { text: 'Page', link: './page.md' } ];", encoding="utf-8")
    selection = resolve_sidebar(str(tmp_path))
    assert selection.pages["docs/user/README.md"].title == "Istio Module"
    assert selection.pages["docs/user/README.md"].doc_type == DOC_TYPE_CONCEPT
    assert selection.orphans == []


def test_resolve_sidebar_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_sidebar(str(tmp_path))


def test_resolve_sap_help_toc_selects_matching_subtrees(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "10-concepts").mkdir(parents=True)
    for name in ("regions", "regions-kyma", "cf-env", "kyma-env", "kyma-modules", "other"):
        (docs / "10-concepts" / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
    # an unselected page that talks about Kyma is worth the curator's attention; one that does not is not
    (docs / "10-concepts" / "other.md").write_text("# other\n\nAlso works with Kyma.\n", encoding="utf-8")
    (docs / "index.md").write_text(
        """# SAP BTP

-   [Basic Platform Concepts](10-concepts/basic.md)
    -   [Regions](10-concepts/regions.md)
        -   [Regions for the Kyma Environment](10-concepts/regions-kyma.md)
    -   [Environments](10-concepts/env.md)
        -   [Cloud Foundry Environment](10-concepts/cf-env.md)
        -   [Kyma Environment](10-concepts/kyma-env.md)
            -   [Kyma Modules](10-concepts/kyma-modules.md)
        -   [Other Environment](10-concepts/other.md)
""",
        encoding="utf-8",
    )
    selection = resolve_sap_help_toc(str(tmp_path))
    assert set(selection.pages) == {
        "docs/10-concepts/regions-kyma.md",
        "docs/10-concepts/kyma-env.md",
        "docs/10-concepts/kyma-modules.md",
    }
    assert (
        selection.pages["docs/10-concepts/kyma-modules.md"].section
        == "Basic Platform Concepts > Environments > Kyma Environment"
    )
    assert selection.orphans == ["docs/10-concepts/other.md"]
    # entries whose target file is missing are reported, not selected
    assert selection.unresolved == []


def test_resolve_tutorials_by_path_or_tag(tmp_path: Path) -> None:
    tutorials = tmp_path / "tutorials"
    for name, front in (
        (
            "cp-kyma-getting-started",
            "---\ntitle: Get Started\nprimary_tag: software-product>sap-btp--kyma-runtime\n---\n",
        ),
        ("deploy-app", "---\ntitle: Deploy App\ntags: [ software-product>sap-btp, kyma-runtime ]\n---\n"),
        ("abap-basics", "---\ntitle: ABAP\nprimary_tag: software-product>sap-btp--abap-environment\n---\n"),
    ):
        (tutorials / name).mkdir(parents=True)
        (tutorials / name / f"{name}.md").write_text(front + "## You will learn\n", encoding="utf-8")
    selection = resolve_tutorials(str(tmp_path))
    assert set(selection.pages) == {
        "tutorials/cp-kyma-getting-started/cp-kyma-getting-started.md",
        "tutorials/deploy-app/deploy-app.md",
    }
    assert selection.pages["tutorials/deploy-app/deploy-app.md"].title == "Deploy App"
    assert selection.pages["tutorials/deploy-app/deploy-app.md"].doc_type == DOC_TYPE_TUTORIAL
    assert selection.orphans == ["tutorials/abap-basics/abap-basics.md"]
    assert os.path.isfile(tmp_path / selection.orphans[0])
