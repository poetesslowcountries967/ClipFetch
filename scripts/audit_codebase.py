\
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "main.py", *sorted((ROOT / "clipfetch").rglob("*.py"))]

# Qt invokes these by virtual dispatch, so there may be no lexical caller.

LAYER_RULES = {
    "config": {"config"},
    "core": {"core"},
    "infrastructure": {"config", "infrastructure"},
    "persistence": {"config", "core", "infrastructure", "persistence"},
    "services": {"config", "core", "infrastructure", "services"},
    "download": {"config", "core", "infrastructure", "download"},
    "i18n": {"config", "i18n"},
    "ui": {
        "config",
        "core",
        "download",
        "i18n",
        "infrastructure",
        "persistence",
        "services",
        "ui",
    },
}


def clipfetch_dependencies(tree):
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("clipfetch."):
                parts = module.split(".")
                if len(parts) >= 2:
                    result.add(parts[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("clipfetch."):
                    parts = alias.name.split(".")
                    if len(parts) >= 2:
                        result.add(parts[1])
    return result

FRAMEWORK_CALLBACKS = {
    "closeEvent",
    "dragEnterEvent",
    "dropEvent",
    "eventFilter",
}


def imported_names(tree):
    result = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.append((alias.asname or alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for alias in node.names:
                if alias.name != "*":
                    result.append((alias.asname or alias.name, node.lineno))
    return result


def used_names(tree):
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def main():
    errors = []
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in SOURCES)

    for path in SOURCES:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        used = used_names(tree)

        relative = path.relative_to(ROOT)

        if relative.parts and relative.parts[0] == "clipfetch" and len(relative.parts) >= 2:
            layer = relative.parts[1]
            allowed = LAYER_RULES.get(layer)
            if allowed is not None:
                forbidden = sorted(
                    dependency
                    for dependency in clipfetch_dependencies(tree)
                    if dependency not in allowed
                )
                for dependency in forbidden:
                    errors.append(
                        "dependência de camada inválida: "
                        f"{relative}: {layer} -> {dependency}"
                    )

        for name, line in imported_names(tree):
            if path.name == "__init__.py":
                continue
            if name not in used:
                errors.append(
                    f"import não usado: {path.relative_to(ROOT)}:{line}: {name}"
                )

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("__") or node.name in FRAMEWORK_CALLBACKS:
                continue
            occurrences = len(
                re.findall(r"\b" + re.escape(node.name) + r"\b", all_text)
            )
            if occurrences <= 1:
                errors.append(
                    "função/método sem referência: "
                    f"{path.relative_to(ROOT)}:{node.lineno}: {node.name}"
                )

    if errors:
        raise SystemExit(
            "ERRO NA AUDITORIA ESTÁTICA:\n- "
            + "\n- ".join(sorted(set(errors)))
        )

    print("✓ imports sem resíduos óbvios")
    print("✓ nenhuma função/método claramente órfão")
    print("✓ regras de dependência entre camadas respeitadas")


if __name__ == "__main__":
    main()
