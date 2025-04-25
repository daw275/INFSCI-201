from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Mapping, Sequence, Tuple

def read_source(path: Path) -> Tuple[str, Tuple[str, ...]]:
    """Return the UTF‑8 source text and an *immutable* tuple of its lines."""
    text: str = path.read_text(encoding="utf-8")
    return text, tuple(text.splitlines())


def parse_tree(source: str) -> ast.AST:
    """AST‑parse *source* and return the tree."""
    return ast.parse(source)

# AST utilities - kept pure & free of mutation

def build_parent_map(tree: ast.AST) -> Mapping[ast.AST, ast.AST | None]:
    """Return an immutable mapping *child → parent* for the whole *tree*."""
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    } | {tree: None}  # type: ignore[arg-type]


def is_method(node: ast.AST, parents: Mapping[ast.AST, ast.AST | None]) -> bool:
    """True if *node* is a method defined inside a class."""
    return isinstance(parents.get(node), ast.ClassDef)

# Structure & metrics

def packages_imported(tree: ast.AST) -> Tuple[str, ...]:
    imports = {
        alias.name
        for n in ast.walk(tree)
        if isinstance(n, ast.Import)
        for alias in n.names
    } | {
        n.module  # type: ignore[union-attr]
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.module
    }
    return tuple(sorted(imports))


def classes_defined(tree: ast.AST) -> Tuple[str, ...]:
    return tuple(sorted({n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}))


def functions_defined(tree: ast.AST, parents: Mapping[ast.AST, ast.AST | None]) -> Tuple[str, ...]:
    return tuple(
        sorted(
            {
                n.name
                for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and not is_method(n, parents)
            }
        )
    )


# Doc‑string & annotation analysis

def docstring_entries(tree: ast.AST, parents: Mapping[ast.AST, ast.AST | None]) -> Tuple[str, ...]:
    def fmt(node: ast.AST) -> str:
        name = (
            f"{parents[node].name}.{node.name}"  # type: ignore[union-attr]
            if isinstance(node, ast.FunctionDef) and is_method(node, parents)
            else node.name  # type: ignore[attr-defined]
        )
        doc = ast.get_docstring(node)
        return f"{name}: {doc}" if doc else f"{name}: DocString not found."

    return tuple(
        fmt(n) for n in ast.walk(tree) if isinstance(n, (ast.ClassDef, ast.FunctionDef))
    )


def missing_type_annotations(
    tree: ast.AST, parents: Mapping[ast.AST, ast.AST | None]
) -> Tuple[str, ...]:
    def incomplete(fn: ast.FunctionDef) -> bool:
        return any(arg.annotation is None for arg in fn.args.args) or fn.returns is None

    return tuple(
        sorted(
            (
                f"{parents[n].name}.{n.name}"  # type: ignore[union-attr]
                if is_method(n, parents)
                else n.name
            )
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and incomplete(n)
        )
    )

# Naming‑convention helpers

def _violates_camel(name: str) -> bool:
    return not (name and name[0].isupper() and "_" not in name)


def _violates_snake(name: str) -> bool:
    return name != name.lower() or any(c.isupper() for c in name if c != "_")


def naming_violations(
    tree: ast.AST, parents: Mapping[ast.AST, ast.AST | None]
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    bad_classes = tuple(
        sorted({n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and _violates_camel(n.name)})
    )
    bad_funcs = tuple(
        sorted(
            {
                (
                    f"{parents[n].name}.{n.name}"
                    if is_method(n, parents)
                    else n.name
                )
                for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and _violates_snake(n.name)
            }
        )
    )
    return bad_classes, bad_funcs

# Report renderer (pure)

def render_report(
    path: Path,
    total_lines: int,
    packages: Sequence[str],
    classes: Sequence[str],
    functions: Sequence[str],
    docstrings: Sequence[str],
    missing_ann: Sequence[str],
    bad_classes: Sequence[str],
    bad_funcs: Sequence[str],
) -> str:
    lines: list[str] = [
        f"File analysed: {path.name}",
        f"Total number of lines of code: {total_lines}",
        "",
        "File Structure",
        f"Packages imported: {', '.join(packages) if packages else 'None'}",
        f"Classes defined: {', '.join(classes) if classes else 'None'}",
        f"Functions defined: {', '.join(functions) if functions else 'None'}",
        "",
        "DocStrings",
        *docstrings,
        "",
        "Type Annotation Check",
        (
            "All functions and methods use type annotations."
            if not missing_ann
            else "Missing type annotations:\n" + "\n".join(missing_ann)
        ),
        "",
        "Naming Convention Check",
        (
            "All names adhere to the specified conventions."
            if not bad_classes and not bad_funcs
            else "\n".join(
                filter(
                    None,
                    [
                        f"Classes not using CamelCase: {', '.join(bad_classes)}" if bad_classes else "",
                        f"Functions/methods not using snake_case: {', '.join(bad_funcs)}" if bad_funcs else "",
                    ],
                )
            )
        ),
    ]
    return "\n".join(lines)

# Side‑effectful orchestration - kept at the very edge

def main() -> None:
    target = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(input("Enter the path of the Python file to check: ").strip())
    ).expanduser().resolve()

    source, lines = read_source(target)
    tree = parse_tree(source)
    parents = build_parent_map(tree)

    report = render_report(
        path=target,
        total_lines=len(lines),
        packages=packages_imported(tree),
        classes=classes_defined(tree),
        functions=functions_defined(tree, parents),
        docstrings=docstring_entries(tree, parents),
        missing_ann=missing_type_annotations(tree, parents),
        bad_classes=naming_violations(tree, parents)[0],
        bad_funcs=naming_violations(tree, parents)[1],
    )

    report_path = target.with_name(f"style_report_{target.stem}.txt")
    report_path.write_text(report, encoding="utf-8")
    print(f"Style report written to {report_path}")


if __name__ == "__main__":
    main()
