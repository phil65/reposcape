"""Repository map generation using tree-sitter for code analysis.

Adapted from aider's repomap module with full type annotations.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
import colorsys
from importlib import resources
import math
import os
from pathlib import Path
import random
import shutil
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, cast


if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from diskcache import Cache
    import networkx as nx


# Important files that should be prioritized in repo map
ROOT_IMPORTANT_FILES: list[str] = [
    "requirements.txt",
    "setup.py",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "build.gradle",
    "pom.xml",
    "Makefile",
    "CMakeLists.txt",
    "Gemfile",
    "composer.json",
    ".env.example",
    "Dockerfile",
    "docker-compose.yml",
    "README.md",
    "README.rst",
    "README",
]

NORMALIZED_ROOT_IMPORTANT_FILES: set[str] = {
    os.path.normpath(path) for path in ROOT_IMPORTANT_FILES
}

# Type aliases
type FileReader = Callable[[str], str | None]
type TokenCounter = Callable[[str], int]


class Tag(NamedTuple):
    """Represents a code tag (definition or reference)."""

    rel_fname: str
    fname: str
    line: int
    name: str
    kind: str


type RankedTag = Tag | tuple[str]  # Either full Tag or just (filename,)


CACHE_VERSION = 4

# Thresholds
MIN_TOKEN_SAMPLE_SIZE: int = 256
LARGE_CACHE_DIFF_THRESHOLD: int = 25
MIN_IDENT_LENGTH: int = 4
MAX_DEFINERS_THRESHOLD: int = 5


def _get_mtime(fname: str) -> float | None:
    """Get file modification time."""
    try:
        return Path(fname).stat().st_mtime
    except FileNotFoundError:
        return None


def is_important(fname: str) -> bool:
    """Check if a file is considered important (like config files)."""
    normalized = os.path.normpath(fname)
    if normalized in NORMALIZED_ROOT_IMPORTANT_FILES:
        return True
    # Check basename
    base = Path(normalized).name
    return base in NORMALIZED_ROOT_IMPORTANT_FILES


def filter_important_files(fnames: list[str]) -> list[str]:
    """Filter and return only important files from a list."""
    return [fname for fname in fnames if is_important(fname)]


class AiderRepoMap:
    """Generates a map of a repository's code structure using tree-sitter."""

    TAGS_CACHE_DIR: ClassVar[str] = f".reposcape.tags.cache.v{CACHE_VERSION}"

    warned_files: ClassVar[set[str]] = set()

    def __init__(
        self,
        root: str | Path,
        *,
        max_tokens: int = 1024,
        read_file: FileReader | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        """Initialize AiderRepoMap.

        Args:
            root: Root directory of the repository.
            max_tokens: Maximum tokens for the generated map.
            read_file: Callable to read file contents. Defaults to Path.read_text.
            token_counter: Callable to count tokens. Defaults to len(text) / 4.
        """
        self.root = str(root)
        self.max_tokens = max_tokens
        self._read_file = read_file or self._default_read_file
        self._token_counter = token_counter

        self._load_tags_cache()

        self.tree_cache: dict[tuple[str, tuple[int, ...], float | None], str] = {}
        self.tree_context_cache: dict[str, dict[str, Any]] = {}
        self.map_cache: dict[tuple[Any, ...], str | None] = {}
        self.map_processing_time: float = 0
        self.last_map: str | None = None
        self.TAGS_CACHE: Cache | dict[str, Any] = {}

    @staticmethod
    def _default_read_file(fname: str) -> str | None:
        """Default file reader using Path.read_text."""
        try:
            return Path(fname).read_text()
        except (OSError, UnicodeDecodeError):
            return None

    def token_count(self, text: str) -> float:
        """Estimate token count for text."""
        if self._token_counter:
            len_text = len(text)
            if len_text < MIN_TOKEN_SAMPLE_SIZE:
                return self._token_counter(text)

            # Sample for large texts
            lines = text.splitlines(keepends=True)
            num_lines = len(lines)
            step = num_lines // 100 or 1
            sampled_lines = lines[::step]
            sample_text = "".join(sampled_lines)
            sample_tokens = self._token_counter(sample_text)
            return sample_tokens / len(sample_text) * len_text

        # Rough estimate: ~4 chars per token
        return len(text) / 4

    def get_map(
        self,
        files: Sequence[str],
        *,
        exclude: set[str] | None = None,
        boost_files: set[str] | None = None,
        boost_idents: set[str] | None = None,
    ) -> str | None:
        """Generate a repository map for the given files.

        Args:
            files: Files to include in the map.
            exclude: Files to exclude from the map output (but still used for ranking).
            boost_files: Files to boost in ranking.
            boost_idents: Identifiers to boost in ranking.

        Returns:
            The generated repository map as a string, or None if no map could be generated.
        """
        if not files:
            return None

        exclude = exclude or set()
        boost_files = boost_files or set()
        boost_idents = boost_idents or set()

        return self._get_ranked_tags_map(
            files=files,
            exclude=exclude,
            boost_files=boost_files,
            boost_idents=boost_idents,
        )

    def get_rel_fname(self, fname: str) -> str:
        """Get relative filename from root."""
        try:
            return os.path.relpath(fname, self.root)
        except ValueError:
            # ValueError: path is on mount 'C:', start on mount 'D:'
            return fname

    def _tags_cache_error(self, original_error: Exception | None = None) -> None:
        """Handle SQLite errors by trying to recreate cache, falling back to dict."""
        import sqlite3

        from diskcache import Cache

        if isinstance(self.TAGS_CACHE, dict):
            return

        path = Path(self.root) / self.TAGS_CACHE_DIR

        try:
            if path.exists():
                shutil.rmtree(path)

            new_cache = Cache(path)

            # Test that it works
            test_key = "test"
            new_cache[test_key] = "test"
            _ = new_cache[test_key]
            del new_cache[test_key]

            self.TAGS_CACHE = new_cache
        except (sqlite3.OperationalError, sqlite3.DatabaseError, OSError):
            self.TAGS_CACHE = {}  # type: ignore[assignment]

    def _load_tags_cache(self) -> None:
        """Load the tags cache from disk."""
        import sqlite3

        from diskcache import Cache

        path = Path(self.root) / self.TAGS_CACHE_DIR
        try:
            self.TAGS_CACHE = Cache(path)
        except (sqlite3.OperationalError, sqlite3.DatabaseError, OSError) as e:
            self._tags_cache_error(e)

    def _get_tags(self, fname: str, rel_fname: str) -> list[Tag]:
        """Get tags for a file, using cache when possible."""
        import sqlite3

        file_mtime = _get_mtime(fname)
        if file_mtime is None:
            return []

        cache_key = fname
        val: dict[str, Any] | None = None
        try:
            val = self.TAGS_CACHE.get(cache_key)  # type: ignore[union-attr]
        except (sqlite3.OperationalError, sqlite3.DatabaseError, OSError) as e:
            self._tags_cache_error(e)
            val = self.TAGS_CACHE.get(cache_key)  # type: ignore[union-attr]

        if val is not None and val.get("mtime") == file_mtime:
            try:
                return cast(list[Tag], self.TAGS_CACHE[cache_key]["data"])  # type: ignore[index]
            except (sqlite3.OperationalError, sqlite3.DatabaseError, OSError) as e:
                self._tags_cache_error(e)
                return cast(list[Tag], self.TAGS_CACHE[cache_key]["data"])  # type: ignore[index]

        # Cache miss
        data = list(self._get_tags_raw(fname, rel_fname))

        try:
            self.TAGS_CACHE[cache_key] = {"mtime": file_mtime, "data": data}  # type: ignore[index]
        except (sqlite3.OperationalError, sqlite3.DatabaseError, OSError) as e:
            self._tags_cache_error(e)
            self.TAGS_CACHE[cache_key] = {"mtime": file_mtime, "data": data}  # type: ignore[index]

        return data

    def _get_tags_raw(self, fname: str, rel_fname: str) -> Iterator[Tag]:  # noqa: PLR0911
        """Extract tags from a file using tree-sitter."""
        from grep_ast import filename_to_lang
        from grep_ast.tsl import get_language, get_parser
        from pygments.lexers import guess_lexer_for_filename
        from pygments.token import Token
        from tree_sitter import Query, QueryCursor

        lang = filename_to_lang(fname)
        if not lang:
            return

        try:
            language = get_language(lang)  # type: ignore[arg-type]
            parser = get_parser(lang)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            return

        query_scm = get_scm_fname(lang)
        if not query_scm or not query_scm.exists():
            return
        query_scm_text = query_scm.read_text()

        code = self._read_file(fname)
        if not code:
            return
        tree = parser.parse(bytes(code, "utf-8"))

        query = Query(language, query_scm_text)
        cursor = QueryCursor(query)

        saw: set[str] = set()
        all_nodes: list[tuple[Any, str]] = []
        for _pattern_index, captures_dict in cursor.matches(tree.root_node):
            for tag, nodes in captures_dict.items():
                all_nodes.extend((node, tag) for node in nodes)

        for node, tag in all_nodes:
            if tag.startswith("name.definition."):
                kind = "def"
            elif tag.startswith("name.reference."):
                kind = "ref"
            else:
                continue

            saw.add(kind)

            yield Tag(
                rel_fname=rel_fname,
                fname=fname,
                name=node.text.decode("utf-8"),
                kind=kind,
                line=node.start_point[0],
            )

        if "ref" in saw:
            return
        if "def" not in saw:
            return

        # We saw defs without refs - use pygments to backfill refs
        try:
            lexer = guess_lexer_for_filename(fname, code)
        except Exception:  # noqa: BLE001
            return

        tokens = list(lexer.get_tokens(code))
        name_tokens = [token[1] for token in tokens if token[0] in Token.Name]

        for token in name_tokens:
            yield Tag(
                rel_fname=rel_fname,
                fname=fname,
                name=token,
                kind="ref",
                line=-1,
            )

    def _get_ranked_tags(
        self,
        files: Sequence[str],
        exclude: set[str],
        boost_files: set[str],
        boost_idents: set[str],
    ) -> list[RankedTag]:
        """Rank tags using PageRank algorithm."""
        import networkx as nx

        defines: defaultdict[str, set[str]] = defaultdict(set)
        references: defaultdict[str, list[str]] = defaultdict(list)
        definitions: defaultdict[tuple[str, str], set[Tag]] = defaultdict(set)

        personalization: dict[str, float] = {}

        exclude_rel_fnames: set[str] = set()
        sorted_fnames = sorted(files)

        # Default personalization for unspecified files
        personalize = 100 / len(sorted_fnames) if sorted_fnames else 0

        fnames_iter: Iterable[str] = sorted_fnames

        for fname in fnames_iter:
            try:
                file_ok = Path(fname).is_file()
            except OSError:
                file_ok = False

            if not file_ok:
                if fname not in self.warned_files:
                    self.warned_files.add(fname)
                continue

            rel_fname = self.get_rel_fname(fname)
            current_pers = 0.0

            if fname in exclude:
                current_pers += personalize
                exclude_rel_fnames.add(rel_fname)

            if rel_fname in boost_files:
                current_pers = max(current_pers, personalize)

            # Check path components against boost_idents
            path_obj = Path(rel_fname)
            path_components = set(path_obj.parts)
            basename_with_ext = path_obj.name
            basename_without_ext = path_obj.stem
            components_to_check = path_components.union({basename_with_ext, basename_without_ext})

            matched_idents = components_to_check.intersection(boost_idents)
            if matched_idents:
                current_pers += personalize

            if current_pers > 0:
                personalization[rel_fname] = current_pers

            tags = list(self._get_tags(fname, rel_fname))

            for tag in tags:
                if tag.kind == "def":
                    defines[tag.name].add(rel_fname)
                    key = (rel_fname, tag.name)
                    definitions[key].add(tag)
                elif tag.kind == "ref":
                    references[tag.name].append(rel_fname)

        if not references:
            references = defaultdict(list, {k: list(v) for k, v in defines.items()})

        idents = set(defines.keys()).intersection(set(references.keys()))

        graph: nx.MultiDiGraph = nx.MultiDiGraph()

        # Add self-edges for definitions without references
        for ident in defines:
            if ident in references:
                continue
            for definer in defines[ident]:
                graph.add_edge(definer, definer, weight=0.1, ident=ident)

        for ident in idents:
            definers = defines[ident]

            mul = 1.0

            is_snake = ("_" in ident) and any(c.isalpha() for c in ident)
            is_kebab = ("-" in ident) and any(c.isalpha() for c in ident)
            is_camel = any(c.isupper() for c in ident) and any(c.islower() for c in ident)
            if ident in boost_idents:
                mul *= 10
            if (is_snake or is_kebab or is_camel) and len(ident) >= MIN_IDENT_LENGTH:
                mul *= 10
            if ident.startswith("_"):
                mul *= 0.1
            if len(defines[ident]) > MAX_DEFINERS_THRESHOLD:
                mul *= 0.1

            for referencer, num_refs in Counter(references[ident]).items():
                for definer in definers:
                    use_mul = mul
                    if referencer in exclude_rel_fnames:
                        use_mul *= 50

                    # Scale down high frequency mentions
                    scaled_refs = math.sqrt(num_refs)

                    graph.add_edge(referencer, definer, weight=use_mul * scaled_refs, ident=ident)

        pers_args: dict[str, Any] = {}
        if personalization:
            pers_args = {"personalization": personalization, "dangling": personalization}

        try:
            ranked: dict[str, float] = nx.pagerank(graph, weight="weight", **pers_args)
        except ZeroDivisionError:
            try:
                ranked = nx.pagerank(graph, weight="weight")
            except ZeroDivisionError:
                return []

        # Distribute rank across out edges
        ranked_definitions: defaultdict[tuple[str, str], float] = defaultdict(float)
        for src in graph.nodes:
            src_rank = ranked[src]
            total_weight = sum(data["weight"] for _, _, data in graph.out_edges(src, data=True))
            for _, dst, data in graph.out_edges(src, data=True):
                data["rank"] = src_rank * data["weight"] / total_weight
                ident = data["ident"]
                ranked_definitions[(dst, ident)] += data["rank"]

        ranked_tags: list[RankedTag] = []
        sorted_definitions = sorted(
            ranked_definitions.items(), reverse=True, key=lambda x: (x[1], x[0])
        )

        for (fname, ident), _rank in sorted_definitions:
            if fname in exclude_rel_fnames:
                continue
            ranked_tags += list(definitions.get((fname, ident), []))

        rel_fnames_without_tags = {self.get_rel_fname(fname) for fname in files}
        for fname in exclude:
            rel = self.get_rel_fname(fname)
            rel_fnames_without_tags.discard(rel)

        fnames_already_included = {rt[0] for rt in ranked_tags}

        top_rank = sorted([(rank, node) for (node, rank) in ranked.items()], reverse=True)
        for _rank, fname in top_rank:
            if fname in rel_fnames_without_tags:
                rel_fnames_without_tags.remove(fname)
            if fname not in fnames_already_included:
                ranked_tags.append((fname,))

        for fname in rel_fnames_without_tags:
            ranked_tags.append((fname,))

        return ranked_tags

    def _get_ranked_tags_map(
        self,
        files: Sequence[str],
        exclude: set[str],
        boost_files: set[str],
        boost_idents: set[str],
        max_tokens: int | None = None,
    ) -> str | None:
        """Generate a ranked tags map."""
        if not max_tokens:
            max_tokens = self.max_tokens

        ranked_tags = self._get_ranked_tags(
            files=files,
            exclude=exclude,
            boost_files=boost_files,
            boost_idents=boost_idents,
        )

        rel_fnames = sorted({self.get_rel_fname(fname) for fname in files})
        special_fnames = filter_important_files(rel_fnames)
        ranked_tags_fnames = {tag[0] for tag in ranked_tags}
        special_fnames = [fn for fn in special_fnames if fn not in ranked_tags_fnames]
        special_tags: list[RankedTag] = [(fn,) for fn in special_fnames]

        ranked_tags = special_tags + ranked_tags

        num_tags = len(ranked_tags)
        lower_bound = 0
        upper_bound = num_tags
        best_tree: str | None = None
        best_tree_tokens: float = 0

        exclude_rel_fnames = {self.get_rel_fname(fname) for fname in exclude}

        self.tree_cache = {}

        middle = min(int(max_tokens // 25), num_tags)
        while lower_bound <= upper_bound:
            tree = self._to_tree(ranked_tags[:middle], exclude_rel_fnames)
            num_tokens = self.token_count(tree)

            pct_err = abs(num_tokens - max_tokens) / max_tokens if max_tokens else 0
            ok_err = 0.15
            if (num_tokens <= max_tokens and num_tokens > best_tree_tokens) or pct_err < ok_err:
                best_tree = tree
                best_tree_tokens = num_tokens

                if pct_err < ok_err:
                    break

            if num_tokens < max_tokens:
                lower_bound = middle + 1
            else:
                upper_bound = middle - 1

            middle = (lower_bound + upper_bound) // 2

        return best_tree

    def _render_tree(self, abs_fname: str, rel_fname: str, lois: list[int]) -> str:
        """Render a tree representation of a file with lines of interest."""
        from grep_ast import TreeContext

        mtime = _get_mtime(abs_fname)
        key = (rel_fname, tuple(sorted(lois)), mtime)

        if key in self.tree_cache:
            return self.tree_cache[key]

        cached = self.tree_context_cache.get(rel_fname)
        if cached is None or cached["mtime"] != mtime:
            code = self._read_file(abs_fname) or ""
            if not code.endswith("\n"):
                code += "\n"

            context = TreeContext(
                rel_fname,
                code,
                color=False,
                line_number=False,
                child_context=False,
                last_line=False,
                margin=0,
                mark_lois=False,
                loi_pad=0,
                show_top_of_file_parent_scope=False,
            )
            self.tree_context_cache[rel_fname] = {"context": context, "mtime": mtime}  # type: ignore[assignment]

        context = self.tree_context_cache[rel_fname]["context"]
        context.lines_of_interest = set()
        context.add_lines_of_interest(lois)
        context.add_context()
        res: str = context.format()
        self.tree_cache[key] = res
        return res

    def _to_tree(self, tags: list[RankedTag], exclude_rel_fnames: set[str]) -> str:
        """Convert ranked tags to a tree representation."""
        if not tags:
            return ""

        cur_fname: str | None = None
        cur_abs_fname: str | None = None
        lois: list[int] | None = None
        output = ""

        # Add bogus tag to trigger final output
        dummy_tag: tuple[None] = (None,)
        for tag in [*sorted(tags), dummy_tag]:  # type: ignore[type-var]
            this_rel_fname = tag[0]
            if this_rel_fname in exclude_rel_fnames:
                continue

            if this_rel_fname != cur_fname:
                if lois is not None and cur_fname and cur_abs_fname:
                    output += "\n"
                    output += cur_fname + ":\n"
                    output += self._render_tree(cur_abs_fname, cur_fname, lois)
                    lois = None
                elif cur_fname:
                    output += "\n" + cur_fname + "\n"
                if isinstance(tag, Tag):
                    lois = []
                    cur_abs_fname = tag.fname
                cur_fname = this_rel_fname

            if lois is not None and isinstance(tag, Tag):
                lois.append(tag.line)

        # Truncate long lines
        return "\n".join([line[:100] for line in output.splitlines()]) + "\n"


def find_src_files(directory: str | Path) -> list[str]:
    """Find all source files in a directory."""
    directory_path = Path(directory)
    if not directory_path.is_dir():
        return [str(directory)]

    src_files: list[str] = []
    for root, _dirs, files in os.walk(directory_path):
        root_path = Path(root)
        src_files.extend(str(root_path / file) for file in files)
    return src_files


def get_random_color() -> str:
    """Generate a random color in hex format."""
    hue = random.random()
    r, g, b = (int(x * 255) for x in colorsys.hsv_to_rgb(hue, 1, 0.75))
    return f"#{r:02x}{g:02x}{b:02x}"


def get_scm_fname(lang: str) -> Path | None:
    """Get the path to the SCM query file for a language."""
    package = __package__ or "reposcape"
    subdir = "tree-sitter-language-pack"
    try:
        path = resources.files(package).joinpath(
            "queries",
            subdir,
            f"{lang}-tags.scm",
        )
        if path.is_file():  # type: ignore[union-attr]
            return Path(str(path))
    except KeyError:
        pass

    # Fall back to tree-sitter-languages
    subdir = "tree-sitter-languages"
    try:
        path = resources.files(package).joinpath(
            "queries",
            subdir,
            f"{lang}-tags.scm",
        )
        return Path(str(path))
    except KeyError:
        return None


def get_supported_languages_md() -> str:
    """Generate markdown table of supported languages."""
    from grep_ast.parsers import PARSERS

    res = """
| Language | File extension | Repo map |
|:--------:|:--------------:|:--------:|
"""
    data = sorted((lang, ext) for ext, lang in PARSERS.items())
    for lang, ext in data:
        fn = get_scm_fname(lang)
        repo_map = "✓" if fn and Path(fn).exists() else ""
        res += f"| {lang:20} | {ext:20} | {repo_map:^8} |\n"

    res += "\n"
    return res


if __name__ == "__main__":
    # Quick test: generate repo map for project itself
    project_root = Path(__file__).parent.parent.parent
    src_dir = project_root / "src" / "reposcape"
    all_py_files = [f for f in find_src_files(src_dir) if f.endswith(".py")]
    print(f"Generating repo map for {len(all_py_files)} Python files...")
    rm = AiderRepoMap(root=project_root)
    repo_map = rm.get_map(all_py_files)

    if repo_map:
        print(f"Repo map ({len(repo_map)} chars):\n")
        print(repo_map)
    else:
        print("No repo map generated")
