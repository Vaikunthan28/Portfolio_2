/* fixes.js - behaviour for the generated fix and blog pages.

   Separate from script.js on purpose. script.js calls loadProjects() and the
   typewriter immediately against #projectGrid and #typed, neither of which
   exists on these pages, so loading it here would throw on every page load.

   Theme handling below mirrors script.js exactly: same "theme" localStorage
   key, same "dark" default, same sun and moon button glyphs, so the setting
   carries between the homepage and these pages in both directions.

   Do NOT load this on index.html. script.js already binds the theme button
   and the mobile menu there, and a second listener would flip the theme
   twice per click. The shared Notes dropdown lives in js/nav.js instead. */

(function () {
  "use strict";

  var root = document.documentElement;
  var toggleBtn = document.getElementById("themeToggle");

  /* ---- theme ---- */
  if (toggleBtn) {
    var stored = null;
    try {
      stored = localStorage.getItem("theme");
    } catch (err) {
      stored = null; // private browsing
    }
    var theme = stored || "dark";

    var applyTheme = function () {
      root.setAttribute("data-theme", theme);
      toggleBtn.textContent = theme === "dark" ? "\u2600\uFE0F" : "\uD83C\uDF19";
    };
    applyTheme();

    toggleBtn.addEventListener("click", function () {
      theme = theme === "dark" ? "light" : "dark";
      try {
        localStorage.setItem("theme", theme);
      } catch (err) { /* ignore */ }
      applyTheme();
    });
  }

  /* ---- mobile menu ---- */
  var nav = document.getElementById("nav");
  var menuBtn = document.getElementById("menuBtn");
  if (nav && menuBtn) {
    menuBtn.addEventListener("click", function () {
      nav.classList.toggle("open");
    });
    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        nav.classList.remove("open");
      });
    });
  }

  /* ---- contents rail: highlight the section currently in view ---- */
  var tocLinks = document.querySelectorAll(".fx-toc-nav a");
  if (tocLinks.length && "IntersectionObserver" in window) {
    var byId = {};
    tocLinks.forEach(function (link) {
      byId[link.getAttribute("href").slice(1)] = link;
    });

    var visible = new Set();
    var order = Object.keys(byId);

    var refresh = function () {
      var current = order.filter(function (id) { return visible.has(id); })[0];
      tocLinks.forEach(function (link) { link.classList.remove("active"); });
      if (current && byId[current]) byId[current].classList.add("active");
    };

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) visible.add(entry.target.id);
          else visible.delete(entry.target.id);
        });
        refresh();
      },
      { rootMargin: "-90px 0px -65% 0px" }
    );

    order.forEach(function (id) {
      var heading = document.getElementById(id);
      if (heading) observer.observe(heading);
    });
  }

  /* ---- copy buttons on code blocks ---- */
  document.querySelectorAll(".copy-btn").forEach(function (button) {
    button.addEventListener("click", function () {
      var card = button.closest(".code-card");
      var block = card && card.querySelector("pre");
      if (!block) return;
      navigator.clipboard.writeText(block.innerText).then(
        function () {
          button.textContent = "copied";
          button.classList.add("done");
          setTimeout(function () {
            button.textContent = "copy";
            button.classList.remove("done");
          }, 1600);
        },
        function () {
          button.textContent = "failed";
          setTimeout(function () {
            button.textContent = "copy";
          }, 1600);
        }
      );
    });
  });
})();
