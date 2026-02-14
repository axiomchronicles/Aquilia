"""Artifact freezing command.

Compiles the workspace and then generates a deterministic fingerprint
so that production deployments can verify artifact integrity.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from ..utils.workspace import get_workspace_file


def freeze_artifacts(
    output_dir: Optional[str] = None,
    sign: bool = False,
    verbose: bool = False,
) -> str:
    """
    Generate immutable artifacts for production.

    1. Runs the standard compiler to produce .crous artifacts.
    2. Computes a combined SHA-256 fingerprint over all artifacts.
    3. Writes a frozen manifest (frozen.json) containing the fingerprint.

    Args:
        output_dir: Output directory for frozen artifacts
        sign: Sign artifacts with cryptographic signature (reserved)
        verbose: Enable verbose output

    Returns:
        Fingerprint of frozen artifacts
    """
    workspace_root = Path.cwd()
    ws_file = get_workspace_file(workspace_root)

    if not ws_file:
        raise ValueError(
            "Not in an Aquilia workspace (workspace.py not found)"
        )

    # Step 1 — compile
    from .compile import compile_workspace

    output = output_dir or str(workspace_root / 'artifacts')
    artifacts = compile_workspace(output_dir=output, verbose=verbose)

    if verbose:
        print(f"  Compiled {len(artifacts)} artifact(s)")

    # Step 2 — fingerprint
    hasher = hashlib.sha256()
    artifacts_dir = Path(output) if output_dir else workspace_root / 'artifacts'

    for artifact_path in sorted(artifacts_dir.glob('*.crous')):
        data = artifact_path.read_bytes()
        hasher.update(data)

    fingerprint = hasher.hexdigest()

    # Step 3 — write frozen manifest
    frozen_meta = {
        'fingerprint': fingerprint,
        'artifacts': [str(a) for a in sorted(artifacts_dir.glob('*.crous'))],
        'signed': sign,
    }

    frozen_path = artifacts_dir / 'frozen.json'
    frozen_path.write_text(json.dumps(frozen_meta, indent=2))

    if verbose:
        print(f"  Frozen manifest: {frozen_path}")

    return fingerprint
