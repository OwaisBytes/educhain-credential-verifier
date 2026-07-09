"""
Scan screenshots/ folder and update README.md Demo Preview section for GitHub.

Usage:
    python scripts/sync_readme_screenshots.py
    git add README.md
    git commit -m "Update README with screenshots"
    git push
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS = ROOT / "screenshots"
README = ROOT / "README.md"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
START = "<!-- SCREENSHOTS:START -->"
END = "<!-- SCREENSHOTS:END -->"


def _sort_key(path: Path) -> tuple[int, str]:
    nums = re.findall(r"\d+", path.stem)
    return (int(nums[0]) if nums else 999, path.name.lower())


def _img_url(path: Path) -> str:
    """GitHub-safe path — encode spaces in filenames."""
    return f"screenshots/{quote(path.name)}"


def _title(path: Path) -> str:
    return path.stem.strip().replace("-", " ").replace("_", " ")


def collect_images() -> list[Path]:
    if not SCREENSHOTS.exists():
        return []
    images = [
        p for p in SCREENSHOTS.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]
    return sorted(images, key=_sort_key)


def build_section(images: list[Path]) -> str:
    if not images:
        return f"""{START}
## Demo Preview

> **No screenshots yet.** Add `.png` or `.jpg` files to the [`screenshots/`](screenshots/) folder, then run:
>
> ```bash
> python scripts/sync_readme_screenshots.py
> git add README.md screenshots/
> git commit -m "Add demo screenshots"
> git push
> ```

_See [screenshots/README.md](screenshots/README.md) for the full checklist._

{END}"""

    lines = [
        START,
        "## Demo Screenshots",
        "",
        "Full lab exam & live demo output from the **EduChain Nexus** credential verification platform.",
        "",
    ]

    for img in images:
        title = _title(img)
        lines += [
            f"### {title}",
            f"![{title}]({_img_url(img)})",
            "",
        ]

    lines.append(f"**Total: {len(images)} screenshots**")
    lines.append(END)
    return "\n".join(lines)


def main() -> None:
    images = collect_images()
    section = build_section(images)
    text = README.read_text(encoding="utf-8")

    if START in text and END in text:
        text = re.sub(
            re.escape(START) + r".*?" + re.escape(END),
            section,
            text,
            flags=re.DOTALL,
        )
    else:
        marker = "**Repository:**"
        if marker in text:
            idx = text.find("---", text.find(marker))
            text = text[:idx] + section + "\n\n---\n\n" + text[idx + 5:]
        else:
            text = section + "\n\n" + text

    README.write_text(text, encoding="utf-8")
    print(f"Updated README.md with {len(images)} screenshot(s).")
    for img in images:
        print(f"  + {img.name}")


if __name__ == "__main__":
    main()
