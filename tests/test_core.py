"""Regression tests for the modules refactored during static analysis."""

from pathlib import Path

import smoosh
from smoosh.analyzer.repository import (
    AnalysisError,
    RepositoryInfo,
    analyze_repository,
    load_file_contents,
)
from smoosh.analyzer.tree import generate_tree
from smoosh.composer.concatenator import compose_content, gather_statistics
from smoosh.utils.config import DEFAULT_CONFIG, deep_merge, load_config


def _make_sample(tmp_path: Path) -> Path:
    """Create a small sample tree and return its root."""
    pkg = tmp_path / "sample_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text("def foo():\n    return 42\n")
    (pkg / "notes.txt").write_text("hello\n")
    return tmp_path


def test_analysis_error_is_the_package_exception() -> None:
    """The analyzer must raise the public exception cli.py catches."""
    assert AnalysisError is smoosh.AnalysisError
    assert issubclass(AnalysisError, smoosh.SmooshError)


def test_analyze_repository_counts_files(tmp_path: Path) -> None:
    """The refactored analysis collects the expected files and totals."""
    root = _make_sample(tmp_path)
    config = load_config(root)

    repo = analyze_repository(root, config)

    assert isinstance(repo, RepositoryInfo)
    assert repo.total_files_count == 3
    assert repo.python_files_count == 2
    assert repo.total_size_mb > 0


def test_analyze_repository_respects_gitignore(tmp_path: Path) -> None:
    """Files listed in .gitignore are excluded from the analysis."""
    root = _make_sample(tmp_path)
    (root / "ignored.txt").write_text("secret\n")
    (root / ".gitignore").write_text("ignored.txt\n")
    config = load_config(root)

    repo = analyze_repository(root, config)

    relative = {str(f.relative_path) for f in repo.files}
    assert "ignored.txt" not in relative


def test_tree_contains_nested_files(tmp_path: Path) -> None:
    """The tree helper still renders nested paths after refactoring."""
    root = _make_sample(tmp_path)
    repo = analyze_repository(root, load_config(root))

    tree = repo.get_tree_representation()

    assert "sample_pkg/" in tree
    assert "mod.py" in tree
    assert generate_tree(str(root), repo.files) == tree


def test_compose_content_modes(tmp_path: Path) -> None:
    """cat/fold/smoosh modes all produce content and statistics."""
    root = _make_sample(tmp_path)
    config = load_config(root)
    repo = analyze_repository(root, config)
    load_file_contents(repo)

    content = compose_content(repo, "cat")
    assert "mod.py" in content

    stats = gather_statistics(repo, content)
    assert stats["Python Files"] == 2
    assert stats["Total Files"] == 3


def test_load_config_merges_user_values(tmp_path: Path) -> None:
    """User configuration is merged onto the single set of defaults."""
    (tmp_path / "smoosh.yaml").write_text("output:\n  max_tokens: 123\n")

    config = load_config(tmp_path)

    assert config["output"]["max_tokens"] == 123
    assert config["output"]["size_limits"]["file_max_mb"] == 1.0
    assert config["gitignore"]["respect"] is True


def test_deep_merge_is_recursive() -> None:
    """deep_merge combines nested dictionaries without dropping keys."""
    base = {"a": {"b": 1, "c": 2}}
    update = {"a": {"c": 3}}

    merged = deep_merge(base, update)

    assert merged == {"a": {"b": 1, "c": 3}}
    assert DEFAULT_CONFIG["output"]["max_tokens"] == 10000


def test_cli_writes_output_file(tmp_path: Path) -> None:
    """End-to-end: the CLI still produces an output file."""
    from click.testing import CliRunner

    from smoosh.cli import main

    root = _make_sample(tmp_path)
    out = tmp_path / "out.txt"

    result = CliRunner().invoke(main, [str(root), "-o", str(out)])

    assert result.exit_code == 0, result.output
    assert out.is_file()
    assert "mod.py" in out.read_text()
