#!/usr/bin/env python3
"""
build.py - static site generator for the fix log and blog.

Reads Markdown from fixes/ and blog/, validates frontmatter, and writes a
complete static site into dist/. Each post gets its own directory and
index.html so URLs stay clean:

    dist/fixes/kubernetes-liveness-probe-404/index.html
    -> https://example.com/fixes/kubernetes-liveness-probe-404/

Generated pages reuse the classes already in css/style.css (topbar, brand,
nav, tag, wdot, sec-head, footer) so they inherit the site theme rather than
redefining it. Only genuinely new components live in css/fixes.css.

Exit code is non-zero on any validation failure, so a bad commit fails the
pipeline instead of deploying a broken site.

Usage:
    python3 build.py                 # build into dist/
    python3 build.py --check         # validate only, write nothing
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path

import markdown
import yaml
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

ROOT = Path(__file__).parent.resolve()

SITE_NAME = "Vaikunthan"
# Used for canonical URLs, Open Graph tags and RSS feeds, all of which need
# absolute URLs. Must match the domain in the CNAME file.
SITE_URL = "https://vaikunthan.dev"

# directory -> (url segment, hero eyebrow, index heading, singular noun)
COLLECTIONS = {
    "fixes": ("fixes", "TODAY I FIXED", "Fix log", "fix"),
    "blog": ("blog", "WRITTEN", "Blog", "post"),
}

STATIC_PATHS = [
    "index.html", "css", "js", "assets",
    "projects.json", "projects-archive.json", "robots.txt", "CNAME",
]

REQUIRED_FIELDS = ["title", "date", "tags", "summary"]

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
FENCE_RE = re.compile(r"^```([\w+-]*)[ \t]*\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)
PLACEHOLDER_RE = re.compile(r"<p>\s*XCODEBLOCK(\d+)X\s*</p>")

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

WRENCH = ('<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
          'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
          '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1'
          '-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>')

CAL = ('<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
       'stroke-linecap="round" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2"/>'
       '<path d="M16 2v4M8 2v4M3 10h18"/></svg>')

CLOCK = ('<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/>'
         '<path d="M12 7v5l3 2"/></svg>')


class BuildError(Exception):
    """Any problem that should stop the build."""


@dataclass
class Post:
    collection: str
    slug: str
    title: str
    published: date
    tags: list[str]
    summary: str
    body_html: str
    time: str = ""
    headings: list = None

    @property
    def url_path(self) -> str:
        return f"/{COLLECTIONS[self.collection][0]}/{self.slug}/"

    @property
    def absolute_url(self) -> str:
        return f"{SITE_URL.rstrip('/')}{self.url_path}"

    @property
    def pretty_date(self) -> str:
        return f"{MONTHS[self.published.month - 1][:3]} {self.published.day}, {self.published.year}"


def e(text) -> str:
    return html.escape(str(text), quote=True)


# --------------------------------------------------------------------------
# Code blocks
# --------------------------------------------------------------------------

def render_code_block(lang: str, code: str) -> str:
    """One fenced block as a window-chrome card, matching the engineer.yaml motif."""
    lang = (lang or "text").lower()
    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        lexer = get_lexer_by_name("text")
    body = highlight(code.rstrip("\n"), lexer, HtmlFormatter(nowrap=True))
    return (
        '<div class="code-card">'
        '<div class="code-bar">'
        '<span class="wdot" style="background:#ff5f57"></span>'
        '<span class="wdot" style="background:#febc2e"></span>'
        '<span class="wdot" style="background:#28c840"></span>'
        f'<span class="code-lang">{e(lang)}</span>'
        '<button class="copy-btn" type="button" aria-label="Copy code to clipboard">copy</button>'
        '</div>'
        f'<pre><code>{body}</code></pre>'
        '</div>'
    )


HEADING_RE = re.compile(r"<h2>(.*?)</h2>", re.DOTALL)
TAGSTRIP_RE = re.compile(r"<[^>]+>")


def slugify(text: str) -> str:
    plain = html.unescape(TAGSTRIP_RE.sub("", text)).lower()
    plain = re.sub(r"[^a-z0-9]+", "-", plain).strip("-")
    return plain or "section"


def render_markdown(body: str) -> tuple[str, list[tuple[str, str]]]:
    """Convert Markdown to HTML.

    Fenced code is pulled out first so Pygments handles it rather than the
    Markdown parser. Returns the HTML plus a list of (anchor, label) pairs
    for every h2, used to build the on-page table of contents.
    """
    blocks: list[str] = []

    def stash(match: re.Match) -> str:
        blocks.append(render_code_block(match.group(1), match.group(2)))
        return f"\n\nXCODEBLOCK{len(blocks) - 1}X\n\n"

    stashed = FENCE_RE.sub(stash, body)
    rendered = markdown.Markdown(extensions=["tables", "attr_list"]).convert(stashed)

    headings: list[tuple[str, str]] = []
    seen: set[str] = set()

    def anchor(match: re.Match) -> str:
        label = match.group(1).strip()
        slug = slugify(label)
        n = 2
        while slug in seen:
            slug = f"{slugify(label)}-{n}"
            n += 1
        seen.add(slug)
        headings.append((slug, TAGSTRIP_RE.sub("", html.unescape(label))))
        return f'<h2 id="{slug}">{label}</h2>'

    rendered = HEADING_RE.sub(anchor, rendered)
    rendered = PLACEHOLDER_RE.sub(lambda m: blocks[int(m.group(1))], rendered)
    return rendered, headings


# --------------------------------------------------------------------------
# Parsing and validation
# --------------------------------------------------------------------------

def parse_post(path: Path, collection: str) -> Post:
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if not match:
        raise BuildError(f"{path.name}: no YAML frontmatter. File must start with '---'.")

    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise BuildError(f"{path.name}: frontmatter is not valid YAML.\n  {exc}") from exc
    if not isinstance(meta, dict):
        raise BuildError(f"{path.name}: frontmatter must be key/value pairs.")

    if meta.get("draft") is True:
        raise BuildError(f"{path.name}: marked as draft")

    missing = [k for k in REQUIRED_FIELDS if meta.get(k) in (None, "")]
    if missing:
        raise BuildError(f"{path.name}: missing required frontmatter: {', '.join(missing)}")
    if collection == "fixes" and not meta.get("time"):
        raise BuildError(f'{path.name}: fixes require a "time" field, for example "20 minutes"')

    published = meta["date"]
    if isinstance(published, datetime):
        published = published.date()
    if not isinstance(published, date):
        raise BuildError(f"{path.name}: 'date' must be YYYY-MM-DD, got {meta['date']!r}")

    tags = meta["tags"]
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list) or not tags:
        raise BuildError(f"{path.name}: 'tags' must be a non-empty list.")
    tags = [str(t).strip().lower() for t in tags]

    slug = str(meta.get("slug") or DATE_PREFIX_RE.sub("", path.stem)).strip().lower()
    if not SLUG_RE.match(slug):
        raise BuildError(f"{path.name}: slug '{slug}' invalid. Lowercase, numbers, single hyphens.")

    body = match.group(2).strip()
    if not body:
        raise BuildError(f"{path.name}: frontmatter present but no content.")

    body_html, headings = render_markdown(body)

    return Post(
        collection=collection,
        slug=slug,
        title=str(meta["title"]).strip(),
        published=published,
        tags=tags,
        summary=str(meta["summary"]).strip(),
        body_html=body_html,
        time=str(meta.get("time", "")).strip(),
        headings=headings,
    )


def load_collection(name: str) -> list[Post]:
    directory = ROOT / name
    if not directory.exists():
        return []

    posts: list[Post] = []
    errors: list[str] = []
    seen: dict[str, Path] = {}

    for path in sorted(directory.glob("*.md")):
        if path.name.startswith("_"):
            continue
        try:
            post = parse_post(path, name)
        except BuildError as exc:
            if "marked as draft" in str(exc):
                print(f"  skipped draft: {name}/{path.name}")
                continue
            errors.append(str(exc))
            continue
        if post.slug in seen:
            errors.append(
                f"{path.name}: slug '{post.slug}' already used by {seen[post.slug].name}. "
                "Two pages cannot share a URL."
            )
            continue
        seen[post.slug] = path
        posts.append(post)

    if errors:
        raise BuildError("\n".join(errors))

    posts.sort(key=lambda p: (p.published, p.slug), reverse=True)
    return posts


def validate_json_files() -> None:
    for name in ("projects.json", "projects-archive.json"):
        path = ROOT / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BuildError(
                f"{name}: invalid JSON at line {exc.lineno}, column {exc.colno}.\n  {exc.msg}"
            ) from exc
        if not isinstance(data, list):
            raise BuildError(f"{name}: expected a JSON array at the top level.")
        print(f"  ok: {name} ({len(data)} entries)")


# --------------------------------------------------------------------------
# Page shell
# --------------------------------------------------------------------------

def page_shell(*, title: str, description: str, canonical: str, depth: int, body: str) -> str:
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{e(title)}</title>
<meta name="description" content="{e(description)}" />
<link rel="canonical" href="{e(canonical)}" />
<meta property="og:title" content="{e(title)}" />
<meta property="og:description" content="{e(description)}" />
<meta property="og:type" content="article" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="{up}css/style.css" />
<link rel="stylesheet" href="{up}css/fixes.css" />
<link rel="alternate" type="application/rss+xml" title="{e(SITE_NAME)} fix log" href="{up}fixes/rss.xml" />
</head>
<body>
<div class="site">

<header class="topbar">
  <a class="brand" href="{up}"><span class="k8s">&#9096;</span> vaikunthan</a>
  <div class="topbar-right">
    <nav class="nav" id="nav">
      <a href="{up}#projects">Projects</a>
      <div class="nav-drop">
        <button class="nav-drop-btn" id="notesBtn" aria-expanded="false" aria-controls="notesMenu">Notes <span class="chev">&#9662;</span></button>
        <div class="nav-menu" id="notesMenu">
          <a href="{up}fixes/">Fixes</a>
          <a href="{up}blog/">Blog</a>
        </div>
      </div>
      <a href="{up}#experience">Experience</a>
      <a href="{up}#skills">Skills</a>
      <a href="{up}#contact">Contact</a>
    </nav>
    <button class="icon-btn" id="themeToggle" aria-label="Toggle day and night mode">&#9728;&#65039;</button>
    <button class="icon-btn menu-btn" id="menuBtn" aria-label="Toggle menu">&#9776;</button>
  </div>
</header>

<main>
{body}
</main>

<footer class="footer">
  <span>&copy; {date.today().year} vaikunthan &middot; markdown in, static html out &middot; built and deployed by github actions</span>
  <span class="up"><span class="pulse"></span>status: operational</span>
</footer>

</div>
<script src="{up}js/fixes.js"></script>
<script src="{up}js/nav.js"></script>
</body>
</html>
"""


def tag_pills(tags: list[str], skip_first: bool = False) -> str:
    items = tags[1:] if skip_first else tags
    return "".join(f'<span class="tag">{e(t)}</span>' for t in items)


def plural(noun: str, count: int) -> str:
    if count == 1:
        return noun
    return noun + "es" if noun == "fix" else noun + "s"


# --------------------------------------------------------------------------
# Article page
# --------------------------------------------------------------------------

def render_post_page(post: Post, older: Post | None) -> str:
    seg, eyebrow, _, noun = COLLECTIONS[post.collection]

    time_item = ""
    if post.time:
        time_item = f'<span class="fx-meta-item">{CLOCK}{e(post.time)} to fix</span>'

    older_card = ""
    if older:
        older_card = (
            f'<a class="older-card" href="../{e(older.slug)}/">'
            f'<span class="older-label">&larr; OLDER {noun.upper()}</span>'
            f'<span class="older-title">{e(older.title)}</span>'
            f'<span class="tags">{tag_pills(older.tags[:1])}</span></a>'
        )

    toc = ""
    if post.headings and len(post.headings) > 1:
        links = "".join(
            f'<a href="#{e(slug)}">{e(label)}</a>' for slug, label in post.headings
        )
        toc = (
            '<aside class="fx-toc">'
            '<div class="fx-toc-label">On this page</div>'
            f'<nav class="fx-toc-nav">{links}</nav>'
            '</aside>'
        )

    body = f"""<article class="fx-article">
  <a class="fx-back" href="../">&larr; All {e(seg)}</a>

  <div class="fx-hero">
    <div class="fx-eyebrow">{WRENCH}{e(eyebrow)}</div>
    <h1>{e(post.title)}</h1>
    <div class="fx-meta">
      <span class="tag primary">{e(post.tags[0])}</span>
      <span class="fx-meta-item">{CAL}{e(post.pretty_date)}</span>
      {time_item}
      {tag_pills(post.tags, skip_first=True)}
    </div>
  </div>

  <div class="fx-layout">
    {toc}
    <div class="fx-body">
{post.body_html}
    </div>
  </div>

  <div class="fx-foot">
    {older_card}
    <a class="fx-browse" href="../">{WRENCH}Browse all {e(seg)}</a>
  </div>
</article>"""

    return page_shell(
        title=f"{post.title} | {SITE_NAME}",
        description=post.summary,
        canonical=post.absolute_url,
        depth=2,
        body=body,
    )


# --------------------------------------------------------------------------
# Index page
# --------------------------------------------------------------------------

def render_index(collection: str, posts: list[Post]) -> str:
    seg, _, heading, noun = COLLECTIONS[collection]

    if collection == "fixes":
        blurb = ("Real errors from real clusters. Symptom, root cause, fix, and why it happened. "
                 "Every one reproduced and resolved by me.")
        cmd = "kubectl get events --sort-by=.lastTimestamp"
    else:
        blurb = "Longer writing on platform engineering, Kubernetes, and CI/CD."
        cmd = "git log --oneline"

    if not posts:
        listing = (f'<p class="fx-empty">No {plural(noun, 0)} published yet. '
                   f'Add a Markdown file to <code>{e(collection)}/</code> and push.</p>')
    else:
        chunks: list[str] = []
        current: tuple[int, int] | None = None
        items: list[str] = []

        def flush() -> None:
            if current and items:
                y, m = current
                chunks.append(
                    '<section class="fx-month"><div class="fx-month-head">'
                    f'<h2>{MONTHS[m - 1]} {y}</h2>'
                    f'<span class="fx-count">{len(items)} {plural(noun, len(items))}</span>'
                    f'</div><ul class="fx-list">{"".join(items)}</ul></section>'
                )

        for post in posts:
            key = (post.published.year, post.published.month)
            if key != current:
                flush()
                current = key
                items = []
            time_span = f'<span class="fx-row-time">{e(post.time)}</span>' if post.time else ""
            items.append(
                f'<li><a class="fx-row" href="{e(post.slug)}/">'
                f'<span class="fx-row-day">{post.published.day:02d}</span>'
                f'<span class="fx-row-main"><span class="fx-row-title">{e(post.title)}</span>'
                f'<span class="tags">{tag_pills(post.tags)}</span></span>'
                f'{time_span}</a></li>'
            )
        flush()
        listing = "".join(chunks)

    total = len(posts)
    body = f"""<section class="fx-wrap fx-index-head">
  <div class="sec-head"><h1>{e(heading)}</h1><span class="sec-tag">{e(cmd)}</span></div>
  <p class="fx-blurb">{e(blurb)}</p>
  <div class="fx-stats">
    <span><b>{total}</b> {plural(noun, total)}</span>
    <span><a href="rss.xml">RSS</a></span>
  </div>
</section>
<div class="fx-wrap">{listing}</div>"""

    return page_shell(
        title=f"{heading} | {SITE_NAME}",
        description=blurb,
        canonical=f"{SITE_URL.rstrip('/')}/{seg}/",
        depth=1,
        body=body,
    )


def render_rss(collection: str, posts: list[Post]) -> str:
    seg, _, heading, _ = COLLECTIONS[collection]
    items = []
    for post in posts[:20]:
        pub = datetime.combine(post.published, datetime.min.time(), tzinfo=timezone.utc)
        items.append(
            f"<item><title>{e(post.title)}</title><link>{e(post.absolute_url)}</link>"
            f'<guid isPermaLink="true">{e(post.absolute_url)}</guid>'
            f"<pubDate>{format_datetime(pub)}</pubDate>"
            f"<description>{e(post.summary)}</description></item>"
        )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n<channel>\n'
            f"<title>{e(SITE_NAME)} {heading.lower()}</title>\n"
            f"<link>{e(SITE_URL.rstrip('/'))}/{e(seg)}/</link>\n"
            "<description>Production fixes and writing, root cause first.</description>\n"
            "<language>en-au</language>\n" + "\n".join(items) + "\n</channel>\n</rss>\n")


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def verify_cname() -> None:
    """A custom domain only survives a deploy if CNAME is in the output.

    GitHub Pages reads CNAME from the published artifact. If it goes missing,
    the custom domain is silently dropped and the site 404s until someone
    notices. Cheaper to fail the build here.
    """
    path = ROOT / "CNAME"
    if not path.exists():
        raise BuildError(
            "CNAME file is missing. GitHub Pages needs it to serve the custom "
            "domain. Create it containing a single line: vaikunthan.dev"
        )
    domain = path.read_text(encoding="utf-8").strip()
    if not domain or " " in domain or "/" in domain or domain.startswith("http"):
        raise BuildError(
            f"CNAME must contain only a bare domain, got {domain!r}. "
            "No scheme, no path, no trailing slash."
        )
    expected = SITE_URL.split("//", 1)[-1].rstrip("/")
    if domain != expected:
        raise BuildError(
            f"CNAME says '{domain}' but SITE_URL is '{SITE_URL}'. "
            "These must match or canonical tags and RSS links will point at "
            "the wrong host."
        )
    print(f"  ok: CNAME -> {domain}")


def copy_static(out_dir: Path) -> None:
    for name in STATIC_PATHS:
        src = ROOT / name
        if not src.exists():
            continue
        dest = out_dir / name
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        print(f"  copied: {name}")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the portfolio site.")
    parser.add_argument("--out", default="dist", help="output directory (default: dist)")
    parser.add_argument("--check", action="store_true", help="validate without writing")
    args = parser.parse_args()

    print("validating content")
    try:
        verify_cname()
        validate_json_files()
        content = {name: load_collection(name) for name in COLLECTIONS}
    except BuildError as exc:
        print("\nBUILD FAILED\n", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1

    for name, posts in content.items():
        print(f"  ok: {len(posts)} in {name}/")

    if args.check:
        print("\ncheck passed, nothing written")
        return 0

    out_dir = ROOT / args.out
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    print(f"\nbuilding into {args.out}/")
    copy_static(out_dir)

    pages = 0
    for name, posts in content.items():
        seg = COLLECTIONS[name][0]
        write(out_dir / seg / "index.html", render_index(name, posts))
        pages += 1
        print(f"  built: {seg}/index.html")
        for i, post in enumerate(posts):
            older = posts[i + 1] if i + 1 < len(posts) else None
            write(out_dir / seg / post.slug / "index.html", render_post_page(post, older))
            pages += 1
            print(f"  built: {seg}/{post.slug}/")
        write(out_dir / seg / "rss.xml", render_rss(name, posts))
        print(f"  built: {seg}/rss.xml")

    print(f"\ndone. {pages} pages generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
