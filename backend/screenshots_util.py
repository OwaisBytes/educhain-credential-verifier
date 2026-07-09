"""Scan screenshots folder for demo images."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT / "screenshots"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def list_screenshots() -> list[dict[str, str]]:
    if not SCREENSHOTS_DIR.exists():
        return []
    items: list[dict[str, str]] = []
    for path in sorted(SCREENSHOTS_DIR.iterdir()):
        if path.suffix.lower() in IMAGE_EXTS and path.is_file():
            name = path.stem.replace("-", " ").replace("_", " ").title()
            items.append({
                "filename": path.name,
                "title": name,
                "url": f"/screenshots/{path.name}",
            })
    return items
