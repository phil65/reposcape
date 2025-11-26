"""Generate Python stub files programmatically.

This module provides helpers to generate .pyi stub content as strings
using mypy's stubgen infrastructure.

Requires mypy to be installed: `pip install mypy`
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence


def _get_mypy_imports():
    """Lazy import mypy modules to avoid hard dependency."""
    try:
        import mypy.errors
        import mypy.options
        import mypy.parse
        from mypy.stubgen import ASTStubGenerator
        import mypy.util
    except ImportError as e:
        msg = "mypy is required for stub generation. Install with: pip install mypy"
        raise ImportError(msg) from e
    return mypy, ASTStubGenerator


def generate_stub_from_source(
    source: str,
    *,
    module_name: str = "__main__",
    include_private: bool = False,
    include_docstrings: bool = True,
) -> str:
    """Generate a stub from Python source code string.

    Args:
        source: Python source code as a string
        module_name: Name to use for the module
        include_private: Include private members (single leading underscore)
        include_docstrings: Include docstrings in generated stubs

    Returns:
        The generated stub content as a string
    """
    mypy, ASTStubGenerator = _get_mypy_imports()

    options = mypy.options.Options()
    options.python_version = (3, 13)
    options.include_docstrings = include_docstrings

    errors = mypy.errors.Errors(options)
    ast = mypy.parse.parse(
        source,
        fnam="<string>",
        module=module_name,
        errors=errors,
        options=options,
    )
    ast._fullname = module_name

    if errors.is_blockers():
        error_messages = list(errors.new_messages())
        msg = "Syntax errors in source:\n" + "\n".join(error_messages)
        raise SyntaxError(msg)

    gen = ASTStubGenerator(
        _all_=None,
        include_private=include_private,
        analyzed=False,
        export_less=False,
        include_docstrings=include_docstrings,
    )
    ast.accept(gen)
    return gen.output()


def generate_stub_from_file(
    path: Path | str,
    *,
    include_private: bool = False,
    include_docstrings: bool = True,
) -> str:
    """Generate a stub from a Python file.

    Args:
        path: Path to the Python source file
        include_private: Include private members (single leading underscore)
        include_docstrings: Include docstrings in generated stubs

    Returns:
        The generated stub content as a string
    """
    path = Path(path)
    if not path.exists():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)

    source = path.read_text(encoding="utf-8")
    module_name = path.stem
    if module_name == "__init__":
        module_name = path.parent.name

    return generate_stub_from_source(
        source,
        module_name=module_name,
        include_private=include_private,
        include_docstrings=include_docstrings,
    )


def generate_stubs_from_directory(
    path: Path | str,
    *,
    include_private: bool = False,
    include_docstrings: bool = True,
    recursive: bool = True,
    exclude_patterns: Sequence[str] | None = None,
) -> dict[str, str]:
    """Generate stubs for all Python files in a directory.

    Args:
        path: Path to the directory containing Python files
        include_private: Include private members (single leading underscore)
        include_docstrings: Include docstrings in generated stubs
        recursive: Recursively process subdirectories
        exclude_patterns: Glob patterns to exclude (e.g., ["**/test_*.py"])

    Returns:
        Mapping from relative file paths (with .pyi extension) to stub content
    """
    path = Path(path)
    if not path.is_dir():
        msg = f"Not a directory: {path}"
        raise NotADirectoryError(msg)

    exclude_patterns = exclude_patterns or []
    results: dict[str, str] = {}

    pattern = "**/*.py" if recursive else "*.py"
    for py_file in path.glob(pattern):
        # Skip excluded patterns
        rel_path = py_file.relative_to(path)
        if any(rel_path.match(pat) for pat in exclude_patterns):
            continue

        # Skip __pycache__ and hidden directories
        if any(part.startswith(".") or part == "__pycache__" for part in rel_path.parts):
            continue

        try:
            stub_content = generate_stub_from_file(
                py_file,
                include_private=include_private,
                include_docstrings=include_docstrings,
            )
            # Convert .py path to .pyi
            stub_path = str(rel_path.with_suffix(".pyi"))
            results[stub_path] = stub_content
        except (SyntaxError, UnicodeDecodeError):
            # Skip files with syntax errors or encoding issues
            continue

    return results


def generate_stubs_analyzed(
    path: Path | str,
    *,
    include_private: bool = False,
    include_docstrings: bool = True,
    packages: Sequence[str] | None = None,
    modules: Sequence[str] | None = None,
) -> dict[str, str]:
    """Generate stubs with full semantic analysis.

    This provides higher quality stubs by running mypy's semantic analyzer,
    which resolves imports and infers more type information.

    Args:
        path: Path to directory or file
        include_private: Include private members (single leading underscore)
        include_docstrings: Include docstrings in generated stubs
        packages: Package names to generate stubs for (recursive)
        modules: Module names to generate stubs for

    Returns:
        Mapping from relative file paths (with .pyi extension) to stub content
    """
    from mypy.stubgen import (
        ASTStubGenerator,
        Options,
        collect_build_targets,
        generate_asts_for_modules,
        mypy_options,
    )

    path = Path(path)
    packages = list(packages) if packages else []
    modules = list(modules) if modules else []
    files = [str(path)] if path.exists() else []

    with tempfile.TemporaryDirectory() as tmpdir:
        options = Options(
            pyversion=(3, 13),
            no_import=True,
            inspect=False,
            doc_dir="",
            search_path=[str(path.parent)] if path.is_file() else [str(path)],
            interpreter="",
            parse_only=False,
            ignore_errors=True,
            include_private=include_private,
            output_dir=tmpdir,
            modules=modules,
            packages=packages,
            files=files,
            verbose=False,
            quiet=True,
            export_less=False,
            include_docstrings=include_docstrings,
        )

        mypy_opts = mypy_options(options)
        py_modules, pyc_modules, c_modules = collect_build_targets(options, mypy_opts)

        generate_asts_for_modules(py_modules, options.parse_only, mypy_opts, options.verbose)

        results: dict[str, str] = {}
        all_module_names = sorted(m.module for m in py_modules + pyc_modules + c_modules)

        for mod in py_modules + pyc_modules:
            if mod.ast is None:
                continue

            gen = ASTStubGenerator(
                mod.runtime_all,
                include_private=include_private,
                analyzed=not options.parse_only,
                export_less=options.export_less,
                include_docstrings=include_docstrings,
            )
            mod.ast.accept(gen)
            output = gen.output()

            # Determine stub path
            if mod.path:
                mod_path = Path(mod.path)
                if mod_path.name in ("__init__.py", "__init__.pyc"):
                    stub_name = mod.module.replace(".", "/") + "/__init__.pyi"
                else:
                    stub_name = mod.module.replace(".", "/") + ".pyi"
            else:
                stub_name = mod.module.replace(".", "/") + ".pyi"

            results[stub_name] = output

        return results


if __name__ == "__main__":
    stubs = generate_stub_from_file(__file__)
    print(stubs)
