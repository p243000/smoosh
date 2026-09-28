"""Repository analysis functionality for smoosh."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

from .. import AnalysisError
from ..custom_types import FileInfo
from ..utils.config import ConfigDict
from ..utils.file_utils import (
    find_git_root,
    get_file_size_mb,
    get_gitignore_patterns,
    walk_repository,
)
from ..utils.logger import logger

# Define PathLike type consistently with other modules
PathLike = Union[str, "os.PathLike[str]"]


@dataclass
class RepositoryInfo:
    """Information about the analyzed repository."""

    root: Path
    files: List[FileInfo]
    gitignore_patterns: Set[str]
    total_size_mb: float
    python_files_count: int
    total_files_count: int

    def get_tree_representation(self) -> str:
        """Compose a tree-style representation of the repository structure."""
        from .tree import generate_tree

        return generate_tree(str(self.root), self.files)


def _resolve_root(input_path: Path) -> Tuple[Path, Optional[Path]]:
    """Resolve the directory to analyse and the enclosing git root, if any.

    Args:
    ----
        input_path: Path supplied by the caller

    Returns:
    -------
        Tuple of (directory to walk, git root or None)

    """
    git_root = find_git_root(input_path)
    if git_root and git_root == input_path:
        logger.info("Git repository root detected at %s", input_path)
        return git_root, git_root

    logger.info("Processing directory at %s", input_path)
    return input_path, git_root


def _collect_ignore_patterns(
    config: ConfigDict, git_root: Optional[Path], root_path: Path, force_cat: bool
) -> Set[str]:
    """Build the set of ignore patterns to apply while walking the repository.

    Args:
    ----
        config: Configuration dictionary
        git_root: Git root path if one was detected
        root_path: Directory being analysed
        force_cat: Whether concatenation was forced by the caller

    Returns:
    -------
        Set of gitignore-style patterns, always including ``.git/``

    """
    patterns: Set[str] = set()
    if config["gitignore"]["respect"] and not force_cat:
        gitignore_root = git_root if git_root else root_path
        patterns = get_gitignore_patterns(str(gitignore_root))

    # Always exclude the .git directory
    patterns.add(".git/")
    return patterns


def _build_file_info(file_path: Path, root_path: Path) -> FileInfo:
    """Create a :class:`FileInfo` record for a single file.

    Args:
    ----
        file_path: Absolute path to the file
        root_path: Repository root used to compute the relative path

    Returns:
    -------
        Populated FileInfo record

    """
    return FileInfo(
        path=file_path,
        relative_path=file_path.relative_to(root_path),
        size_mb=get_file_size_mb(file_path),
        is_python=file_path.suffix == ".py",
    )


def _collect_files(
    root_path: Path, ignore_patterns: Set[str], max_size_mb: Optional[float]
) -> Tuple[List[FileInfo], float, int]:
    """Walk the repository and return file records plus aggregate statistics.

    Args:
    ----
        root_path: Directory being analysed
        ignore_patterns: Patterns describing paths to skip
        max_size_mb: Maximum file size to include, or None for no limit

    Returns:
    -------
        Tuple of (files sorted by relative path, total size in MB,
        number of Python files)

    """
    files: List[FileInfo] = []
    total_size_mb = 0.0
    python_files_count = 0

    for file_path in walk_repository(str(root_path), ignore_patterns, max_size_mb):
        try:
            file_info = _build_file_info(file_path, root_path)
        except (OSError, ValueError) as e:
            logger.warning("Error processing file %s: %s", file_path, e)
            continue

        files.append(file_info)
        total_size_mb += file_info.size_mb
        if file_info.is_python:
            python_files_count += 1

    files.sort(key=lambda f: str(f.relative_path))
    return files, total_size_mb, python_files_count


def analyze_repository(
    path: PathLike, config: ConfigDict, force_cat: bool = False
) -> RepositoryInfo:
    """Analyze a repository and gather information about its structure.

    Args:
    ----
        path: Path to the repository
        config: Configuration dictionary
        force_cat: Whether to force concatenation mode

    Returns:
    -------
        RepositoryInfo object containing analysis results

    Raises:
    ------
        AnalysisError: If analysis fails

    """
    input_path = Path(str(path))
    root_path, git_root = _resolve_root(input_path)

    try:
        ignore_patterns = _collect_ignore_patterns(config, git_root, root_path, force_cat)
        max_size_mb: Optional[float] = (
            None if force_cat else config["output"]["size_limits"]["file_max_mb"]
        )
        files, total_size_mb, python_files_count = _collect_files(
            root_path, ignore_patterns, max_size_mb
        )
    except OSError as e:
        raise AnalysisError(f"Failed to analyze repository: {e}") from e

    return RepositoryInfo(
        root=root_path,
        files=files,
        gitignore_patterns=ignore_patterns,
        total_size_mb=total_size_mb,
        python_files_count=python_files_count,
        total_files_count=len(files),
    )


def load_file_contents(repo_info: RepositoryInfo) -> None:
    """Load the contents of all files in the repository info.

    Args:
    ----
        repo_info: Repository information object

    """
    for file_info in repo_info.files:
        try:
            with open(file_info.path, encoding="utf-8") as f:
                file_info.content = f.read()
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("Error reading file %s: %s", file_info.path, e)
            file_info.content = None
