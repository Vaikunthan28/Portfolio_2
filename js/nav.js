/* nav.js - the Notes dropdown, and nothing else.

   Loaded on BOTH index.html (alongside script.js) and the generated fix and
   blog pages (alongside fixes.js). It is deliberately the only shared file:
   script.js and fixes.js each own theme and menu handling for their own
   pages, and loading both on one page would attach two click listeners to
   the theme button, flipping the theme twice per click. */

(function () {
  "use strict";

  var button = document.getElementById("notesBtn");
  var menu = document.getElementById("notesMenu");
  if (!button || !menu) return;

  function setOpen(open) {
    menu.classList.toggle("open", open);
    button.setAttribute("aria-expanded", open ? "true" : "false");
  }

  button.addEventListener("click", function (event) {
    event.stopPropagation();
    setOpen(!menu.classList.contains("open"));
  });

  document.addEventListener("click", function (event) {
    if (!menu.contains(event.target) && event.target !== button) setOpen(false);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") setOpen(false);
  });
})();
