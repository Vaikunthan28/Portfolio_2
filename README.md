# Vaikunthan | DevOps / Platform Engineer Portfolio

Plain HTML, CSS, and JavaScript. No framework, no build step.
Dark mode by default with a light mode toggle. Deployed to
GitHub Pages by GitHub Actions on every push.

## Structure

```
index.html                    page markup (edit bio, experience, certs here)
css/style.css                 all styling and both themes
js/script.js                  theme toggle, typewriter, project rendering
projects.json                 YOUR PROJECTS. The file you edit every 2 weeks.
assets/Vaikunthan_CV.pdf      your CV (add this file)
.github/workflows/deploy.yml  auto-deploy pipeline
```

## Add a new project (2 minutes)

Open `projects.json` and paste this at the TOP of the array:

```json
{
  "id": "my-new-project",
  "title": "My New Project",
  "status": "running",
  "date": "2026",
  "summary": "One sentence on what it does and why it matters.",
  "highlights": [
    "Key technical detail 1.",
    "Key technical detail 2."
  ],
  "tags": ["terraform", "aws"],
  "repoUrl": "https://github.com/vaikunthan28/my-new-project"
}
```

Notes:
- `status` is `"running"` (shows amber "in progress") or `"deployed"` (green check)
- `repoUrl` can be an empty string `""` to hide the repo link
- Remember the comma between objects, JSON is strict
- The pipeline validates projects.json before deploying, so a typo
  will fail the build instead of breaking the live site

Then:

```bash
git add . && git commit -m "add project: my-new-project" && git push
```

GitHub Actions deploys automatically. Live in about a minute.

## First-time setup

1. Push this to your GitHub repo (main branch)
2. Repo Settings -> Pages -> Source: select "GitHub Actions"
3. Site goes live at https://vaikunthan28.github.io/<repo-name>/
4. Add your CV as `assets/Vaikunthan_CV.pdf`
5. Replace `your-email@example.com` in index.html with your real email

## Run locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

(Opening index.html directly with file:// will not load projects.json,
browsers block fetch on local files. Use the server command above.)
