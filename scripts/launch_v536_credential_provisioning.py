"""Load the V5.36 credential provisioner from this exact deployment."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from typing import Sequence


_MODULE_NAME = "algotrader.execution.v536_credential_provisioning"
_MODULE_RELATIVE_PATH = Path(
    "src/algotrader/execution/v536_credential_provisioning.py"
)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        sys.dont_write_bytecode = True
        launcher_path = Path(__file__).resolve(strict=True)
        repo_root = launcher_path.parents[1]
        expected_launcher = (
            repo_root / "scripts" / "launch_v536_credential_provisioning.py"
        ).resolve(strict=True)
        if launcher_path != expected_launcher:
            raise RuntimeError("runtime_source_mismatch")
        src_root = (repo_root / "src").resolve(strict=True)
        sys.path.insert(0, str(src_root))
        module = importlib.import_module(_MODULE_NAME)
        expected_module = (repo_root / _MODULE_RELATIVE_PATH).resolve(strict=True)
        actual_module = Path(module.__file__).resolve(strict=True)
        if actual_module != expected_module:
            raise RuntimeError("runtime_source_mismatch")
        return int(module.main(argv, expected_repo_root=repo_root))
    except Exception:
        print(
            json.dumps(
                {"classification": "provisioning_runtime_source_unavailable"},
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
