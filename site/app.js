/* Lantern marketing site: lantern drawing, hero ignition, scroll story, nav. No dependencies. */
(function () {
  var root = document.documentElement;
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) root.classList.add("static");

  var LANTERN =
    '<svg viewBox="0 0 30 48" aria-hidden="true" focusable="false">' +
    '<path class="frame" d="M15 1v5"/>' +
    '<path class="frame" d="M8 12 15 6l7 6z"/>' +
    '<path class="frame glass" d="M8 12h14l2 22H6z"/>' +
    '<path class="flame" d="M15 17c3 4 4 6 4 9a4 4 0 0 1-8 0c0-3 1-5 4-9z"/>' +
    '<rect class="frame" x="5" y="34" width="20" height="4" rx="1.5"/>' +
    '<g class="tick"><circle cx="24" cy="41" r="6" fill="#0A101C" stroke="#3DD68C" stroke-width="1.6"/>' +
    '<path d="m21 41 2 2 4-4" fill="none" stroke="#3DD68C" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></g>' +
    "</svg>";
  window.LANTERN_SVG = LANTERN;

  document.querySelectorAll("[data-lantern]").forEach(function (el) { el.innerHTML = LANTERN; });
  document.querySelectorAll("[data-wire]").forEach(function (w) {
    var labels = (w.getAttribute("data-wire") || "").split("|");
    w.insertAdjacentHTML("beforeend",
      '<div class="wire-line"></div><div class="wire-light"></div><div class="lanterns">' +
      labels.map(function (t) { return '<div class="lan">' + LANTERN + "<span>" + t + "</span></div>"; }).join("") + "</div>");
  });

  /* nav */
  var nav = document.querySelector(".nav"), mb = document.querySelector(".menu-btn");
  if (nav && mb) {
    mb.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      mb.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.querySelectorAll(".nav-links a").forEach(function (a) {
      a.addEventListener("click", function () { nav.classList.remove("open"); mb.setAttribute("aria-expanded", "false"); });
    });
  }

  /* reveal on scroll */
  var rev = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    rev.forEach(function (r) { io.observe(r); });
  } else rev.forEach(function (r) { r.classList.add("in"); });

  /* hero: lanterns ignite left to right, the card fills in step, then a soft bloom (once, about 3 s) */
  var hero = document.getElementById("hero");
  if (hero) {
    var wire = hero.querySelector(".wire"), lans = wire.querySelectorAll(".lan"), cols = hero.querySelectorAll(".col");
    var finish = function () {
      wire.style.setProperty("--lit", "92%"); wire.classList.add("on");
      lans.forEach(function (l) { l.classList.add("lit", "done"); });
      cols.forEach(function (c) { c.classList.add("show"); });
      hero.classList.add("bloom");
    };
    if (reduce) finish();
    else {
      setTimeout(function () { wire.style.setProperty("--lit", "92%"); wire.classList.add("on"); }, 250);
      lans.forEach(function (l, i) { setTimeout(function () { l.classList.add("lit"); }, 300 + i * 380); });
      cols.forEach(function (c, i) { setTimeout(function () { c.classList.add("show"); }, 800 + i * 700); });
      setTimeout(function () { hero.classList.add("bloom"); }, 2600);
      setTimeout(function () { lans.forEach(function (l) { l.classList.add("done"); }); }, 3200);
    }
  }

  /* how it works: each step lights its lantern as it enters the viewport */
  var steps = document.querySelectorAll(".step");
  var bar = document.getElementById("storyWire");
  if (steps.length && bar) {
    var bl = bar.querySelectorAll(".lan");
    var setStep = function (n) {
      bl.forEach(function (l, i) {
        l.classList.toggle("done", i < n);
        l.classList.toggle("lit", i <= n);
      });
      bar.classList.add("on");
      bar.style.setProperty("--lit", (n / (bl.length - 1)) * 92 + "%");
      steps.forEach(function (s, i) { s.classList.toggle("active", i === n); });
    };
    setStep(0);
    if ("IntersectionObserver" in window) {
      var so = new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) setStep(+e.target.getAttribute("data-i")); });
      }, { rootMargin: "-45% 0px -45% 0px" });
      steps.forEach(function (s) { so.observe(s); });
    } else { bl.forEach(function (l) { l.classList.add("lit", "done"); }); steps.forEach(function (s) { s.classList.add("active"); }); }
  }
})();
