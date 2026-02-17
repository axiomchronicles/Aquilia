#!/usr/bin/env python3
"""
AST-based Serializer Dependency Graph Generator
================================================

Scans the aquilia/ source tree using the AST module to discover:
- Serializer class definitions and their inheritance chains
- Field declarations per serializer
- Consumer call sites (controller, DI, mail, etc.)

Outputs:
- serializer_audit/serializer_graph.dot  (Graphviz DOT)
- serializer_audit/serializer_graph.json (machine-readable adjacency list)

Usage:
    python serializer_audit/graph_gen.py
    python serializer_audit/graph_gen.py --output-dir /tmp/graphs
"""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path
from typing import Any


# Known serializer base classes
SERIALIZER_BASES = {
    "Serializer",
    "ModelSerializer",
    "ListSerializer",
    "StreamingSerializer",
}

# Known field class names
FIELD_NAMES = {
    "CharField", "IntegerField", "FloatField", "DecimalField",
    "BooleanField", "EmailField", "URLField", "UUIDField",
    "DateTimeField", "DateField", "TimeField", "DurationField",
    "ListField", "DictField", "JSONField",
    "ReadOnlyField", "HiddenField", "SerializerMethodField",
    "ChoiceField", "MultipleChoiceField", "ConstantField",
    "IPAddressField", "FilePathField", "SlugField",
    "PrimaryKeyRelatedField", "SlugRelatedField", "StringRelatedField",
}


def find_python_files(root: Path) -> list[Path]:
    """Find all .py files under root, excluding __pycache__ and env."""
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip virtual environments, caches, builds
        dirnames[:] = [
            d for d in dirnames
            if d not in {"__pycache__", "env", ".git", "build", "dist", "node_modules"}
        ]
        for fn in filenames:
            if fn.endswith(".py"):
                result.append(Path(dirpath) / fn)
    return result


def analyze_file(filepath: Path, root: Path) -> dict[str, Any]:
    """Parse a single Python file and extract serializer info."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return {"path": str(filepath.relative_to(root)), "classes": [], "usages": []}

    relative = str(filepath.relative_to(root))
    classes = []
    usages = []

    for node in ast.walk(tree):
        # Find class definitions
        if isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(f"{ast.dump(base)}")

            # Check if this is a serializer subclass
            is_serializer = any(b in SERIALIZER_BASES for b in bases)
            if is_serializer:
                fields = []
                methods = []
                for item in node.body:
                    # Field assignments
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and isinstance(item.value, ast.Call):
                                func = item.value.func
                                if isinstance(func, ast.Name) and func.id in FIELD_NAMES:
                                    fields.append({
                                        "name": target.id,
                                        "type": func.id,
                                        "line": item.lineno,
                                    })
                    # validate_* methods
                    if isinstance(item, ast.FunctionDef):
                        if item.name.startswith("validate_") or item.name == "validate":
                            methods.append(item.name)

                classes.append({
                    "name": node.name,
                    "bases": bases,
                    "fields": fields,
                    "validate_methods": methods,
                    "line": node.lineno,
                    "file": relative,
                })

        # Find serializer instantiations / references
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr

            if name and (name.endswith("Serializer") or name.endswith("serializer")):
                usages.append({
                    "name": name,
                    "file": relative,
                    "line": node.lineno,
                })

    return {"path": relative, "classes": classes, "usages": usages}


def generate_dot(all_classes: list[dict], all_usages: list[dict]) -> str:
    """Generate a Graphviz DOT graph."""
    lines = [
        'digraph SerializerGraph {',
        '    rankdir=TB;',
        '    node [shape=record, style=filled, fontname="Helvetica"];',
        '    edge [fontname="Helvetica", fontsize=10];',
        '',
        '    // Serializer classes',
    ]

    # Class nodes
    for cls in all_classes:
        fields_str = "|".join(f"{f['name']}: {f['type']}" for f in cls["fields"][:8])
        if len(cls["fields"]) > 8:
            fields_str += f"|... +{len(cls['fields']) - 8} more"
        label = f"{{{cls['name']}|{fields_str}}}" if fields_str else cls["name"]
        color = "#E8F5E9" if "Model" in cls.get("bases", [""]) else "#E3F2FD"
        lines.append(f'    "{cls["name"]}" [label="{label}", fillcolor="{color}"];')

    lines.append("")
    lines.append("    // Inheritance edges")
    for cls in all_classes:
        for base in cls["bases"]:
            if base in SERIALIZER_BASES or any(c["name"] == base for c in all_classes):
                lines.append(f'    "{cls["name"]}" -> "{base}" [style=dashed, color="#666"];')

    lines.append("")
    lines.append("    // Consumer nodes")
    consumer_files = set()
    for usage in all_usages:
        f = usage["file"]
        if f not in consumer_files:
            consumer_files.add(f)
            safe_name = f.replace("/", "_").replace(".", "_")
            lines.append(f'    "{safe_name}" [label="{f}", shape=box, fillcolor="#FFF9C4"];')

    lines.append("")
    lines.append("    // Usage edges")
    for usage in all_usages:
        safe_file = usage["file"].replace("/", "_").replace(".", "_")
        lines.append(f'    "{safe_file}" -> "{usage["name"]}" [color="#F57C00"];')

    lines.append("}")
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate serializer dependency graph")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--output-dir", default="serializer_audit", help="Output directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning {root} ...")
    files = find_python_files(root)
    print(f"Found {len(files)} Python files")

    all_classes = []
    all_usages = []

    for filepath in files:
        result = analyze_file(filepath, root)
        all_classes.extend(result["classes"])
        all_usages.extend(result["usages"])

    print(f"Found {len(all_classes)} serializer classes")
    print(f"Found {len(all_usages)} serializer usages")

    # Generate DOT
    dot = generate_dot(all_classes, all_usages)
    dot_path = output_dir / "serializer_graph.dot"
    dot_path.write_text(dot, encoding="utf-8")
    print(f"DOT graph → {dot_path}")

    # Generate JSON adjacency list
    graph_json = {
        "classes": all_classes,
        "usages": all_usages,
        "stats": {
            "total_classes": len(all_classes),
            "total_usages": len(all_usages),
            "total_files_scanned": len(files),
            "total_fields": sum(len(c["fields"]) for c in all_classes),
        },
    }
    json_path = output_dir / "serializer_graph.json"
    json_path.write_text(json.dumps(graph_json, indent=2), encoding="utf-8")
    print(f"JSON graph → {json_path}")


if __name__ == "__main__":
    main()
