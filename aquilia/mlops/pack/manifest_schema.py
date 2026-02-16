"""
JSON Schema for modelpack ``manifest.json``.

Used for validation at pack-time, publish-time and CI.
"""

MANIFEST_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Aquilia Modelpack Manifest",
    "type": "object",
    "required": ["name", "version", "framework", "entrypoint"],
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9][a-zA-Z0-9._/-]*$",
            "description": "Model name (registry path).",
        },
        "version": {
            "type": "string",
            "pattern": "^v?\\d+\\.\\d+\\.\\d+",
            "description": "Semantic version.",
        },
        "framework": {
            "type": "string",
            "enum": [
                "pytorch", "tensorflow", "onnx",
                "sklearn", "xgboost", "lightgbm", "custom",
            ],
        },
        "entrypoint": {
            "type": "string",
            "description": "Primary model file name inside model/.",
        },
        "inference_signature": {
            "type": "object",
            "properties": {
                "inputs": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/tensor_spec"},
                },
                "outputs": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/tensor_spec"},
                },
            },
        },
        "env_lock": {"type": "string"},
        "provenance": {
            "type": "object",
            "properties": {
                "git_sha": {"type": "string"},
                "dataset_snapshot": {"type": "string"},
                "dockerfile": {"type": "string"},
                "build_timestamp": {"type": "string"},
            },
        },
        "blobs": {
            "type": "array",
            "items": {"$ref": "#/$defs/blob_ref"},
        },
        "created_at": {"type": "string", "format": "date-time"},
        "signed_by": {"type": "string"},
        "metadata": {"type": "object"},
    },
    "$defs": {
        "tensor_spec": {
            "type": "object",
            "required": ["name", "dtype", "shape"],
            "properties": {
                "name": {"type": "string"},
                "dtype": {
                    "type": "string",
                    "enum": [
                        "float16", "float32", "float64",
                        "int8", "int16", "int32", "int64",
                        "uint8", "uint16", "bool", "string",
                    ],
                },
                "shape": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "integer", "minimum": 0},
                            {"type": "null"},
                        ]
                    },
                },
            },
        },
        "blob_ref": {
            "type": "object",
            "required": ["path", "digest", "size"],
            "properties": {
                "path": {"type": "string"},
                "digest": {
                    "type": "string",
                    "pattern": "^sha256:[a-f0-9]{64}$",
                },
                "size": {"type": "integer", "minimum": 0},
            },
        },
    },
}


def validate_manifest(data: dict) -> list[str]:
    """
    Validate manifest dict against schema.

    Returns a list of error messages (empty if valid).
    Uses a lightweight built-in validator so ``jsonschema``
    is optional.
    """
    errors: list[str] = []

    for req in MANIFEST_SCHEMA["required"]:
        if req not in data:
            errors.append(f"Missing required field: {req}")

    name = data.get("name", "")
    if name and not isinstance(name, str):
        errors.append("'name' must be a string")

    version = data.get("version", "")
    if version and not isinstance(version, str):
        errors.append("'version' must be a string")

    framework = data.get("framework", "")
    allowed = MANIFEST_SCHEMA["properties"]["framework"]["enum"]
    if framework and framework not in allowed:
        errors.append(f"'framework' must be one of {allowed}")

    sig = data.get("inference_signature", {})
    if sig:
        for key in ("inputs", "outputs"):
            tensors = sig.get(key, [])
            for i, t in enumerate(tensors):
                for f in ("name", "dtype", "shape"):
                    if f not in t:
                        errors.append(f"inference_signature.{key}[{i}] missing '{f}'")

    blobs = data.get("blobs", [])
    for i, b in enumerate(blobs):
        for f in ("path", "digest", "size"):
            if f not in b:
                errors.append(f"blobs[{i}] missing '{f}'")

    return errors
