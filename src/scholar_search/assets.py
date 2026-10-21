"""Browser-side assets shipped inside the distribution.

The wheel and sdist carry the native host sources, the extension and the JSON
schemas so a user who only installed the package can still complete the
documented setup. ``scholar-search assets --target DIR`` copies them out.
"""

from __future__ import annotations

import shutil
from importlib.resources import files
from pathlib import Path

ASSET_DIRS = ("native-host", "extension", "schemas")


def assets_root() -> Path:
    return Path(str(files("scholar_search"))) / "assets"


def copy_assets(target: Path) -> list[Path]:
    """Copy the bundled browser assets into ``target`` and return the paths."""

    root = assets_root()
    if not root.is_dir():
        raise FileNotFoundError(
            "this installation has no bundled assets; use a release wheel or the source tree"
        )
    target.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for name in ASSET_DIRS:
        source = root / name
        if not source.is_dir():
            continue
        destination = target / name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        copied.append(destination)
    return copied
