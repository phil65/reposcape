"""Grep utility wrapping grep-ast for coding agents.

Provides structured, AST-aware code search with context.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass
class SearchMatch:
    """A single search match with context."""

    file: str
    matched_lines: set[int]
    formatted: str

    @property
    def match_count(self) -> int:
        return len(self.matched_lines)


@dataclass
class SearchResult:
    """Result of a grep search across files."""

    pattern: str
    matches: list[SearchMatch] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total_matches(self) -> int:
        return sum(m.match_count for m in self.matches)

    @property
    def files_matched(self) -> int:
        return len(self.matches)

    def format(self, max_files: int | None = None) -> str:
        """Format results as a string.

        Args:
            max_files: Maximum number of files to include. None for all.
        """
        if not self.matches:
            return f"No matches found for '{self.pattern}'"

        parts = [f"Found {self.total_matches} matches in {self.files_matched} files:\n"]

        matches_to_show = self.matches[:max_files] if max_files else self.matches
        for match in matches_to_show:
            parts.append(f"\n{match.file}:")
            parts.append(match.formatted)

        if max_files and len(self.matches) > max_files:
            remaining = len(self.matches) - max_files
            parts.append(f"\n... and {remaining} more files")

        return "\n".join(parts)


def _read_file(path: str) -> str | None:
    """Read file contents, returning None on error."""
    try:
        return Path(path).read_text()
    except (OSError, UnicodeDecodeError):
        return None


def _search_file(
    fname: str,
    pattern: str,
    ignore_case: bool,
    parent_context: bool,
    child_context: bool,
    margin: int,
) -> SearchMatch | tuple[str, str] | None:
    """Search a single file. Returns SearchMatch, error tuple, or None if no match."""
    from grep_ast import TreeContext, filename_to_lang

    code = _read_file(fname)
    if code is None:
        return (fname, "Failed to read file")

    # Check if language is supported
    if not filename_to_lang(fname):
        return None  # Silently skip unsupported files

    try:
        ctx = TreeContext(
            fname,
            code,
            color=False,
            parent_context=parent_context,
            child_context=child_context,
            margin=margin,
        )
        matched = ctx.grep(pattern, ignore_case)
        if not matched:
            return None

        ctx.add_lines_of_interest(matched)
        ctx.add_context()
        formatted = ctx.format()

        return SearchMatch(file=fname, matched_lines=matched, formatted=formatted)

    except ValueError as e:
        return (fname, str(e))


def grep(
    files: Iterable[str],
    pattern: str,
    *,
    ignore_case: bool = False,
    max_matches: int | None = None,
    parent_context: bool = True,
    child_context: bool = True,
    margin: int = 3,
    max_workers: int | None = None,
) -> SearchResult:
    """Search files for a pattern with AST-aware context.

    Args:
        files: Files to search.
        pattern: Regex pattern to search for.
        ignore_case: Whether to ignore case.
        max_matches: Stop after finding this many matching files. None for no limit.
        parent_context: Include parent scope context.
        child_context: Include child context.
        margin: Lines of margin around matches.
        max_workers: Max parallel workers. None for default.

    Returns:
        SearchResult with matches and any errors.
    """
    result = SearchResult(pattern=pattern)
    files_list = list(files)

    if not files_list:
        return result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _search_file,
                fname,
                pattern,
                ignore_case,
                parent_context,
                child_context,
                margin,
            ): fname
            for fname in files_list
        }

        for future in as_completed(futures):
            match_result = future.result()

            if match_result is None:
                continue
            if isinstance(match_result, tuple):
                result.errors.append(match_result)
            else:
                result.matches.append(match_result)

                if max_matches and len(result.matches) >= max_matches:
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    break

    # Sort matches by file path for consistent output
    result.matches.sort(key=lambda m: m.file)

    return result


def grep_simple(
    files: Iterable[str],
    pattern: str,
    *,
    ignore_case: bool = False,
    max_files: int | None = 10,
) -> str:
    """Simple grep returning formatted string output.

    Convenience wrapper for coding agents that just need a string result.

    Args:
        files: Files to search.
        pattern: Regex pattern to search for.
        ignore_case: Whether to ignore case.
        max_files: Maximum files to show in output.

    Returns:
        Formatted string with search results.
    """
    result = grep(files, pattern, ignore_case=ignore_case, max_matches=max_files)
    return result.format(max_files=max_files)


if __name__ == "__main__":
    # Quick test
    from reposcape.repomap import find_src_files

    project_root = Path(__file__).parent.parent.parent
    src_dir = project_root / "src" / "reposcape"

    py_files = [f for f in find_src_files(src_dir) if f.endswith(".py")]

    print(f"Searching {len(py_files)} files for 'def grep'...\n")
    print(grep_simple(py_files, r"def grep"))
