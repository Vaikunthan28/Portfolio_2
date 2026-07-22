# Vaikunthan | DevOps / Platform Engineer Portfolio

Plain HTML, CSS and JavaScript for the homepage. Fix log and blog pages are
generated from Markdown by `build.py` at deploy time. No framework.
Dark mode by default with a light mode toggle.

## Structure

```
index.html                    homepage markup (bio, experience, certs)
css/style.css                 theme tokens and homepage styling
css/fixes.css                 fix log and blog pages, uses style.css tokens
js/script.js                  homepage: theme, typewriter, project rendering
js/fixes.js                   generated pages: theme, menu, copy buttons
js/nav.js                     Notes dropdown, shared by both
projects.json                 YOUR PROJECTS. Edit this to add one.
fixes/*.md                    one Markdown file per fix
blog/*.md                     one Markdown file per post
build.py                      generates dist/ from the above
linkcheck.py                  fails the build on broken internal links
.github/workflows/deploy.yml  validate -> build -> link check -> deploy
```

`dist/` is generated and gitignored. Never edit it by hand.

## Add a fix (5 minutes)

Copy `fixes/_template.md` to `fixes/YYYY-MM-DD-short-slug.md`, remove the
`draft: true` line, and fill it in. The filename date prefix is stripped, so
that file publishes at `/fixes/short-slug/`.

Required frontmatter: `title`, `date`, `tags`, `summary`, and `time` for
fixes. A missing field fails the build rather than publishing a broken page.

```bash
git add . && git commit -m "fix: short slug" && git push
```

## Add a project

Open `projects.json` and paste at the TOP of the array:

```json
{
  "id": "my-new-project",
  "title": "My New Project",
  "status": "running",
  "date": "2026",
  "summary": "One sentence on what it does and why it matters.",
  "highlights": ["Key technical detail 1.", "Key technical detail 2."],
  "tags": ["terraform", "aws"],
  "repoUrl": "https://github.com/vaikunthan28/my-new-project"
}
```

`status` is `"running"` (amber, in progress) or `"deployed"` (green check).
`repoUrl` can be `""` to hide the link. JSON is strict about commas, and the
pipeline validates the file before deploying, so a typo fails the build
instead of silently blanking the projects section.

## Run locally

```bash
pip install -r requirements.txt
python3 build.py
python3 linkcheck.py --dir dist --ignore assets/Vaikunthan_CV.pdf
python3 -m http.server 8000 --directory dist
# open http://localhost:8000
```

`python3 build.py --check` validates content without writing anything.

## Known gap

The hero "Download CV" button points at `assets/Vaikunthan_CV.pdf`, which is
not in the repo yet, so the link currently 404s. The link check waives it via
the `--ignore` flag in `deploy.yml`. Add the PDF, then delete that flag.
