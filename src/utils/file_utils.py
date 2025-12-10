"""File filtering utilities including gitignore support."""

import logging
from pathlib import Path
from typing import List, Optional, Set

import pathspec

from config.settings import settings

logger = logging.getLogger(__name__)


class FileFilter:
    """Filter files based on patterns and .gitignore."""

    def __init__(
        self,
        codebase_root: Path,
        additional_patterns: Optional[List[str]] = None
    ):
        """Initialize file filter.

        Args:
            codebase_root: Root directory of codebase
            additional_patterns: Additional patterns to exclude
        """
        self.codebase_root = Path(codebase_root)
        self.additional_patterns = additional_patterns or []

        # Load patterns
        self.default_patterns = settings.default_exclude_patterns
        self.gitignore_spec = self._load_gitignore()

    def _load_gitignore(self) -> Optional[pathspec.PathSpec]:
        """Load and parse .gitignore file.

        Returns:
            PathSpec object or None if .gitignore not found
        """
        gitignore_path = self.codebase_root / ".gitignore"

        if not gitignore_path.exists():
            logger.debug(f"No .gitignore found at {gitignore_path}")
            return None

        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                patterns = f.read().splitlines()

            # Remove comments and empty lines
            patterns = [
                p.strip() for p in patterns
                if p.strip() and not p.strip().startswith('#')
            ]

            spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)
            logger.info(f"Loaded {len(patterns)} patterns from .gitignore")
            return spec

        except Exception as e:
            logger.warning(f"Error loading .gitignore: {e}")
            return None

    def _matches_pattern(self, file_path: Path, patterns: List[str]) -> bool:
        """Check if file matches any pattern.

        Args:
            file_path: Path to check
            patterns: List of glob patterns

        Returns:
            True if matches any pattern
        """
        try:
            # Create PathSpec from patterns
            spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

            # Get relative path
            try:
                rel_path = file_path.relative_to(self.codebase_root)
            except ValueError:
                rel_path = file_path

            return spec.match_file(str(rel_path))

        except Exception as e:
            logger.debug(f"Error matching pattern for {file_path}: {e}")
            return False

    def should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded.

        Args:
            file_path: Path to check

        Returns:
            True if file should be excluded
        """
        try:
            # Get relative path for checking
            rel_path = file_path.relative_to(self.codebase_root)
        except ValueError:
            rel_path = file_path

        rel_path_str = str(rel_path)

        # Check gitignore
        if self.gitignore_spec and self.gitignore_spec.match_file(rel_path_str):
            logger.debug(f"Excluded by .gitignore: {rel_path}")
            return True

        # Check default patterns
        if self._matches_pattern(file_path, self.default_patterns):
            logger.debug(f"Excluded by default patterns: {rel_path}")
            return True

        # Check additional patterns
        if self.additional_patterns and self._matches_pattern(file_path, self.additional_patterns):
            logger.debug(f"Excluded by additional patterns: {rel_path}")
            return True

        return False

    def walk_files(self, show_progress: bool = False) -> List[Path]:
        """Walk directory and return filtered file paths.

        Args:
            show_progress: Whether to show progress

        Returns:
            List of file paths to process
        """
        files = []

        if show_progress:
            logger.info(f"Scanning {self.codebase_root}...")

        for path in self.codebase_root.rglob('*'):
            # Skip directories
            if not path.is_file():
                continue

            # Check if should exclude
            if self.should_exclude(path):
                continue

            files.append(path)

        logger.info(f"Found {len(files)} files to process (after filtering)")
        return files


def get_all_files(
    codebase_path: Path,
    additional_exclude: Optional[List[str]] = None
) -> List[Path]:
    """Get all files from codebase with filtering.

    Args:
        codebase_path: Path to codebase
        additional_exclude: Additional patterns to exclude

    Returns:
        List of file paths
    """
    file_filter = FileFilter(codebase_path, additional_exclude)
    return file_filter.walk_files()


def count_files_by_extension(files: List[Path]) -> dict:
    """Count files by extension.

    Args:
        files: List of file paths

    Returns:
        Dictionary of extension -> count
    """
    counts = {}
    for file in files:
        ext = file.suffix or 'no_extension'
        counts[ext] = counts.get(ext, 0) + 1

    return counts
