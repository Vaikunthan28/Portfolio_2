#!/usr/bin/env python3
"""
linkcheck.py - fail the build if any internal link points at a file that is
not in the build output.

This is the check that catches a "Download CV" button pointing at a PDF nobody
ever committed. External links are not fetched, only local paths are resolved.

Usage:
    python3 linkcheck.py            # check dist/
    python3 linkcheck.py --dir out  # check a different directory
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

# href="..." or src="..." with either quote style
LINK_RE = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:", "//", "#", "javascript:")


def local_targets(html: str) -> list[str]:
    targets = []
    for raw in LINK_RE.findall(html):
        value = raw.strip()
        if not value or value.lower().startswith(SKIP_PREFIXES):
            continue
        path = urlsplit(value).path  # drops #fragment and ?query
        if path:
            targets.append(unquote(path))
    return targets


def resolve(root: Path, page: Path, target: str) -> Path:
    base = root if target.startswith("/") else page.parent
    candidate = (base / target.lstrip("/")).resolve()
    # A URL ending in "/" means the directory's index.html
    if target.endswith("/") or candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description="Check internal links in built HTML.")
    parser.add_argument("--dir", default="dist", help="directory to check (default: dist)")
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="PATH",
        help="link target to skip, repeatable. Use only for files you know are "
             "coming, and remove the flag once they land.",
    )
    args = parser.parse_args()

    ignored = {item.strip().lstrip("/") for item in args.ignore}

    root = Path(args.dir).resolve()
    if not root.exists():
        print(f"link check: '{args.dir}' does not exist. Run build.py first.", file=sys.stderr)
        return 1

    pages = sorted(root.rglob("*.html"))
    if not pages:
        print(f"link check: no HTML files found in {args.dir}/", file=sys.stderr)
        return 1

    broken: list[str] = []
    checked = 0
    waived = 0

    for page in pages:
        html = page.read_text(encoding="utf-8", errors="ignore")
        for target in local_targets(html):
            if target.lstrip("./").lstrip("/") in ignored or target.lstrip("/") in ignored:
                waived += 1
                continue
            checked += 1
            if not resolve(root, page, target).exists():
                broken.append(f"{page.relative_to(root)} -> {target}")

    if broken:
        print(f"\nLINK CHECK FAILED: {len(broken)} broken internal link(s)\n", file=sys.stderr)
        for item in broken:
            print(f"  {item}", file=sys.stderr)
        print("", file=sys.stderr)
        return 1

    summary = f"link check: {checked} internal links across {len(pages)} pages, all resolve"
    if waived:
        summary += f" ({waived} waived via --ignore)"
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
