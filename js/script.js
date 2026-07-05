// ============================================================
//  You normally never need to edit this file.
//  Projects live in projects.json. Everything else is markup
//  in index.html.
// ============================================================

// ---------- Projects (loaded from projects.json) ----------
async function loadProjects() {
  const grid = document.getElementById("projectGrid");
  try {
    const res = await fetch("projects.json");
    const projects = await res.json();
    grid.innerHTML = projects
      .map(
        (p) => `
  <article class="card">
    <div class="dep-head">
      <span class="dep-name">deploy/<b>${p.id}</b></span>
      <span class="status ${p.status === "running" ? "run" : "ok"}">${
          p.status === "running" ? "&#9684; in progress" : "&#10003; deployed"
        }</span>
    </div>
    <div class="card-body">
      <h3>${p.title}</h3>
      <p>${p.summary}</p>
      <ul class="highlights">${p.highlights
        .map((h) => `<li>${h}</li>`)
        .join("")}</ul>
      <div class="tags">${p.tags
        .map((t) => `<span class="tag">${t}</span>`)
        .join("")}</div>
      ${
        p.repoUrl
          ? `<a class="repo-link" href="${p.repoUrl}" target="_blank" rel="noreferrer">View repository &rarr;</a>`
          : ""
      }
    </div>
  </article>`
      )
      .join("");
  } catch (err) {
    grid.innerHTML =
      '<p class="dim">Could not load projects.json. If you are opening this file directly, run a local server: python3 -m http.server</p>';
    console.error(err);
  }
}
loadProjects();

// ---------- Theme: dark by default, remembered per visitor ----------
const root = document.documentElement;
const toggleBtn = document.getElementById("themeToggle");
let theme = localStorage.getItem("theme") || "dark";

function applyTheme() {
  root.setAttribute("data-theme", theme);
  toggleBtn.textContent = theme === "dark" ? "\u2600\uFE0F" : "\uD83C\uDF19";
}
applyTheme();

toggleBtn.addEventListener("click", () => {
  theme = theme === "dark" ? "light" : "dark";
  localStorage.setItem("theme", theme);
  applyTheme();
});

// ---------- Typewriter ----------
const roles = [
  "DevOps Engineer",
  "MLOps Engineer",
  "Platform Engineer",
  "Site Reliability Engineer",
];
const typedEl = document.getElementById("typed");
let ri = 0,
  ci = 0,
  deleting = false;
(function type() {
  const word = roles[ri % roles.length];
  typedEl.textContent = word.slice(0, ci);
  let delay = deleting ? 40 : 90;
  if (!deleting && ci === word.length) {
    deleting = true;
    delay = 1800;
  } else if (deleting && ci === 0) {
    deleting = false;
    ri++;
    delay = 400;
  } else {
    ci += deleting ? -1 : 1;
  }
  setTimeout(type, delay);
})();

// ---------- Mobile menu ----------
const nav = document.getElementById("nav");
document
  .getElementById("menuBtn")
  .addEventListener("click", () => nav.classList.toggle("open"));
nav
  .querySelectorAll("a")
  .forEach((a) =>
    a.addEventListener("click", () => nav.classList.remove("open"))
  );
