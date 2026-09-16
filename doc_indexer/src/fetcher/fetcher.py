import hashlib
import json
import os
import re
import shutil
from datetime import UTC, datetime
from typing import Any

from fetcher.resolvers import Selection, resolve_sap_help_toc, resolve_sidebar, resolve_tutorials
from fetcher.scroller import Scroller
from fetcher.source import DocumentsSource, ResolverConfig, SourceType, get_documents_sources

from utils.logging import get_logger
from utils.utils import DownloadedRepo, download_repo, repo_is_archived

logger = get_logger(__name__)

# Name of the per-source metadata file read by the application's DocIndex.
META_FILE_NAME = "meta.json"
# Name of the build manifest written at the root of the output directory.
MANIFEST_FILE_NAME = "manifest.json"
# Directory under the output root that holds the files a resolver left out,
# per source, so the curator can classify them. The application's DocIndex
# skips directories starting with an underscore.
RESIDUE_DIR_NAME = "_residue"


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


def copy_residue(repo_dir: str, output_dir: str, source_name: str, selection: Selection) -> int:
    """Copy the Markdown files a resolver did not select into the residue area.

    Args:
        repo_dir: Root of the downloaded repository.
        output_dir: Root of the docs output directory.
        source_name: Name of the source, used as the sub-directory.
        selection: The resolver's selection with its orphans.

    Returns:
        Number of files copied.
    """
    copied = 0
    for rel in selection.orphans:
        src = os.path.join(repo_dir, rel)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(output_dir, RESIDUE_DIR_NAME, source_name, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
        copied += 1
    logger.info("Copied residue files", extra={"source": source_name, "count": copied})
    return copied


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


def _file_hashes(directory: str) -> dict[str, str]:
    """Return ``{relative path: sha256}`` for every Markdown file under *directory*."""
    hashes: dict[str, str] = {}
    for dirpath, _dirnames, filenames in os.walk(directory):
        for filename in sorted(filenames):
            if not filename.endswith(".md"):
                continue
            full = os.path.join(dirpath, filename)
            with open(full, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            hashes[os.path.relpath(full, directory).replace(os.sep, "/")] = digest
    return hashes


def write_manifest(output_dir: str, entries: dict[str, dict[str, Any]]) -> None:
    """Write ``manifest.json`` at the root of the docs output.

    The manifest records, per source, the commit that was fetched and the
    hash of every Markdown file, so two builds can be diffed page by page
    and a build can be traced back to exact upstream revisions.

    Args:
        output_dir: Root of the docs output directory.
        entries: Manifest entry per source name, as returned by
            :meth:`DocumentsFetcher.fetch_documents`.
    """
    manifest: dict[str, Any] = {"fetched_at": datetime.now(tz=UTC).isoformat(), "sources": {}}
    for name, entry in entries.items():
        manifest["sources"][name] = {**entry, "files": _file_hashes(os.path.join(output_dir, name))}
    path = os.path.join(output_dir, MANIFEST_FILE_NAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    logger.info("Wrote build manifest", extra={"path": path, "sources": len(entries)})


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

    def fetch_documents(self, source: DocumentsSource) -> dict[str, Any]:
        """Fetch the documents from the source.

        Returns:
            The manifest entry for the source: repository slug, commit,
            archived state, resolver name and selection counts.
        """
        logger.info("Fetching documents", extra={"source": source.name, "url": source.url})

        if not re.fullmatch(r"[A-Za-z0-9_-]+", source.name):
            raise ValueError(f"Invalid source name: {source.name}")

        if source.source_type == SourceType.GITHUB:
            archived = repo_is_archived(source.url)
            if archived:
                logger.warning("Source repository is archived; its documentation is frozen", extra={"url": source.url})
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
            if selection is not None:
                copy_residue(repo_dir, self.output_dir, source.name, selection)
            write_meta(module_output_dir, source, downloaded, selection)
        except Exception:
            logger.exception("Error while scrolling documents", extra={"source": source.name})
            raise
        finally:
            # delete the directories if they exist
            logger.debug(f"Deleting the temporary directory: {repo_dir}")
            shutil.rmtree(repo_dir, ignore_errors=False)

        return {
            "repo": downloaded.slug,
            "source_url": source.url,
            "commit": downloaded.commit,
            "archived": archived,
            "resolver": source.resolver.type if source.resolver else "",
            "pages": len(selection.pages) if selection else None,
            "orphans": len(selection.orphans) if selection else None,
            "unresolved": len(selection.unresolved) if selection else None,
        }

    def run(self) -> None:
        """Fetch the documents from all the sources and write the build manifest."""
        entries: dict[str, dict[str, Any]] = {}
        for source in self.sources:
            entries[source.name] = self.fetch_documents(source)
        logger.info("Documents fetched successfully from all sources!")
        write_manifest(self.output_dir, entries)

        # clean the temporary files.
        self.clean()

    def clean(self) -> None:
        """Clean the temporary files."""
        _empty_dir(self.tmp_dir)
