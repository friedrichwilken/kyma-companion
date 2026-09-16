import json
import os
import re
import shutil
from typing import Any

from fetcher.resolvers import Selection, resolve_sap_help_toc, resolve_sidebar, resolve_tutorials
from fetcher.scroller import Scroller
from fetcher.source import DocumentsSource, ResolverConfig, SourceType, get_documents_sources

from utils.logging import get_logger
from utils.utils import DownloadedRepo, download_repo

logger = get_logger(__name__)

# Name of the per-source metadata file read by the application's DocIndex.
META_FILE_NAME = "meta.json"


def _empty_dir(path: str) -> None:
    """Remove everything *inside* a directory, leaving the directory itself.

    Deleting the directory itself would require write access to its parent,
    which the non-root container user does not have for /app-rooted paths
    (see the doc_indexer Dockerfile). Emptying the contents only needs write
    access to the directory, which the user does have.
    """
    if not os.path.isdir(path):
        return
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            shutil.rmtree(entry.path)
        else:
            os.remove(entry.path)


def run_resolver(repo_dir: str, config: ResolverConfig) -> Selection:
    """Run the configured resolver over a downloaded repository.

    Args:
        repo_dir: Root of the downloaded repository.
        config: Which resolver to run and its options.

    Returns:
        The resolver's selection.
    """
    if config.type == "sidebar":
        return resolve_sidebar(repo_dir, config.path or "docs/user/_sidebar.ts")
    if config.type == "sap_help_toc":
        return resolve_sap_help_toc(repo_dir, config.path or "docs/index.md", config.title_match or r"(?i)kyma")
    return resolve_tutorials(repo_dir, config.path or "tutorials", config.match or "kyma")


def write_meta(
    output_dir: str, source: DocumentsSource, repo: DownloadedRepo, selection: Selection | None = None
) -> None:
    """Write ``meta.json`` next to the fetched Markdown files of one source.

    The application's ``DocIndex`` reads this file to attach a repository
    slug, a module name and a base URL to every page of the source, so that
    search results carry a citable link pinned to the fetched commit and can
    be filtered by module. With a resolver selection it also carries the
    canonical title, doc type and section of every selected page, and the
    files the resolver left out (orphans) for the curator to review.
    """
    meta: dict[str, Any] = {
        "repo": repo.slug,
        "module": source.name,
        "base_url": repo.blob_base_url,
        "commit": repo.commit,
        "source_url": source.url,
    }
    if selection is not None:
        meta["resolver"] = source.resolver.type if source.resolver else ""
        meta["pages"] = {
            path: {"title": page.title, "doc_type": page.doc_type, "section": page.section}
            for path, page in sorted(selection.pages.items())
        }
        meta["orphans"] = sorted(selection.orphans)
        meta["unresolved"] = sorted(selection.unresolved)
    meta_path = os.path.join(output_dir, META_FILE_NAME)
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
        fh.write("\n")
    logger.info("Wrote source metadata", extra={"path": meta_path, "commit": repo.commit})


class DocumentsFetcher:
    """Class to fetch the documents from the specified sources"""

    output_dir: str
    tmp_dir: str
    sources: list[DocumentsSource]

    def __init__(self, source_file: str, output_dir: str, tmp_dir: str) -> None:
        """Initializes the DocumentsFetcher class."""
        self.output_dir = output_dir
        self.tmp_dir = tmp_dir

        # Create the directories if they don't exist, then clear their contents.
        # Emptying (rather than removing) the dirs keeps them usable by a non-root
        # user that lacks write access to the parent directory.
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.tmp_dir, exist_ok=True)
        _empty_dir(self.output_dir)
        _empty_dir(self.tmp_dir)

        # read the documents sources from the json file.
        self.sources = get_documents_sources(source_file)

    def fetch_documents(self, source: DocumentsSource) -> None:
        """Fetch the documents from the source."""
        logger.info("Fetching documents", extra={"source": source.name, "url": source.url})

        if not re.fullmatch(r"[A-Za-z0-9_-]+", source.name):
            raise ValueError(f"Invalid source name: {source.name}")

        if source.source_type == SourceType.GITHUB:
            logger.debug("Downloading repository", extra={"url": source.url})
            # download and extract the repository tarball (no git required).
            downloaded = download_repo(source.url, self.tmp_dir)
            repo_dir = downloaded.path
        else:
            raise ValueError(f"unsupported source_type: {source.source_type}")

        module_output_dir = os.path.join(self.output_dir, source.name)
        logger.debug(f"Creating a temporary directory: {module_output_dir}")
        os.makedirs(module_output_dir, exist_ok=True)

        # select and extract markdown files
        try:
            selection = run_resolver(repo_dir, source.resolver) if source.resolver else None
            scroller = Scroller(repo_dir, module_output_dir, source, selection)
            scroller.scroll()
            write_meta(module_output_dir, source, downloaded, selection)
        except Exception:
            logger.exception("Error while scrolling documents", extra={"source": source.name})
            raise
        finally:
            # delete the directories if they exist
            logger.debug(f"Deleting the temporary directory: {repo_dir}")
            shutil.rmtree(repo_dir, ignore_errors=False)

    def run(self) -> None:
        """Fetch the documents from all the sources."""
        for source in self.sources:
            self.fetch_documents(source)
        logger.info("Documents fetched successfully from all sources!")

        # clean the temporary files.
        self.clean()

    def clean(self) -> None:
        """Clean the temporary files."""
        _empty_dir(self.tmp_dir)
