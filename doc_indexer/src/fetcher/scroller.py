import fnmatch
import os
import shutil

from fetcher.resolvers import Selection
from fetcher.source import DocumentsSource

from utils.logging import get_logger

logger = get_logger(__name__)


class Scroller:
    """Scroller class to scroll through the files and save the required files."""

    dir_path: str
    output_dir: str
    source: DocumentsSource
    selection: Selection | None

    def __init__(
        self, dir_path: str, output_dir: str, source: DocumentsSource, selection: Selection | None = None
    ) -> None:
        """Initializes the Scroller class.

        Args:
            dir_path: Root of the downloaded repository.
            output_dir: Where selected files are copied to, preserving their relative path.
            source: The source configuration with include and exclude patterns.
            selection: Pages chosen by a resolver. When given, a file is saved if the
                selection contains it or an ``include_files`` pattern matches it.
        """
        self.dir_path = dir_path
        self.output_dir = output_dir
        self.source = source
        self.selection = selection

    def _save_file(self, file_dir: str, file_name: str) -> None:
        """Saves the file to the output directory."""
        source_file_path = os.path.join(self.dir_path, file_dir, file_name)

        target_dir = os.path.join(self.output_dir, file_dir)
        os.makedirs(target_dir, exist_ok=True)

        shutil.copy(source_file_path, target_dir)
        logger.info(f"Saved file {source_file_path} to {target_dir}")

    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if the file should be excluded."""
        if self.source.exclude_files is None:
            raise ValueError("exclude_files is None.")
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.source.exclude_files)

    def _should_include_file(self, file_path: str) -> bool:
        """Check if the file should be included."""
        if self.source.include_files is None:
            raise ValueError("include_files is None.")
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.source.include_files)

    def scroll(self) -> None:
        """Scroll through the files and save the required files."""
        for file_dir, _, files in os.walk(self.dir_path):
            relative_dir = file_dir.removeprefix(self.dir_path).lstrip("/")
            for file_name in files:
                file_path = os.path.join(relative_dir, file_name)

                # skip if file type is not allowed.
                if file_name.split(".")[-1] not in self.source.filter_file_types:
                    logger.debug(f"skipping file {file_path} because file type not allowed.")
                    continue

                if self.source.exclude_files is not None and self._should_exclude_file(file_path):
                    logger.debug(f"skipping file {file_path} because file is in exclude_files list.")
                    continue

                if self._is_selected(file_path):
                    self._save_file(relative_dir, file_name)
                else:
                    logger.debug(f"skipping file {file_path} because it is neither selected nor in include_files.")

    def _is_selected(self, file_path: str) -> bool:
        """Decide whether *file_path* is part of this source's documentation.

        With a resolver selection, the selection decides and ``include_files``
        adds extras. Without one, ``include_files`` decides, and a missing
        ``include_files`` means everything is included.
        """
        if self.selection is not None:
            if file_path in self.selection.pages:
                return True
            return self.source.include_files is not None and self._should_include_file(file_path)
        if self.source.include_files is None:
            return True
        return self._should_include_file(file_path)
