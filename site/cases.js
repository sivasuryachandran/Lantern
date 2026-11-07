/* All cases view: filter by state, search, expand a case to see its timeline. Reads cases-data.js (fictional sample data). */
(function () {
  var data = window.LANTERN_CASES || [], list = document.getElementById("caseList");
  if (!list) return;
  var LABEL = { said: "SAID", draft: "DRAFT (unverified)", nurse: "NURSE CONFIRMED", chart: "SIMULATED CHART", decision: "CLINICIAN CONFIRMED",
                given: "GIVEN", task: "OWNER", handoff: "HANDOFF", agent: "AGENT CLAIM CHECK", fetch: "LOOKUP" };
  var CHIP = { POSSIBLE_DISCREPANCY: "amber", CONFIRMED_CONFLICT: "cyan", RESOLVED: "green", HANDED_OFF: "violet", REJECTED: "red" };
  var state = "ALL", q = "";
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var name = function (s) { return s.replace(/_/g, " "); };

  var states = ["ALL"].concat(Object.keys(CHIP).filter(function (s) { return data.some(function (c) { return c.state === s; }); }));
  var bar = document.getElementById("filters");
  bar.innerHTML = states.map(function (s) {
    var n = s === "ALL" ? data.length : data.filter(function (c) { return c.state === s; }).length;
    return '<button type="button" class="fbtn" data-s="' + s + '" aria-pressed="' + (s === state) + '">' + (s === "ALL" ? "All cases" : name(s)) + ' <span>' + n + "</span></button>";
  }).join("");
  bar.addEventListener("click", function (e) {
    var b = e.target.closest(".fbtn"); if (!b) return;
    state = b.getAttribute("data-s");
    bar.querySelectorAll(".fbtn").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    draw();
  });
  document.getElementById("search").addEventListener("input", function (e) { q = e.target.value.toLowerCase(); draw(); });
  document.getElementById("expandAll").addEventListener("click", function (e) {
    var open = e.target.getAttribute("data-open") !== "1";
    e.target.setAttribute("data-open", open ? "1" : "0"); e.target.textContent = open ? "Collapse all" : "Expand all";
    list.querySelectorAll("details").forEach(function (d) { d.open = open; });
  });

  function draw() {
    var rows = data.filter(function (c) {
      if (state !== "ALL" && c.state !== state) return false;
      var hay = (c.quote + " " + c.topic + " " + c.owner + " " + c.patient + " case " + c.id + " " + c.state).toLowerCase();
      return !q || hay.indexOf(q) >= 0;
    }).slice().reverse();
    document.getElementById("count").textContent = rows.length + " of " + data.length + " cases";
    if (!rows.length) { list.innerHTML = '<p class="muted">No cases match.</p>'; return; }
    list.innerHTML = rows.map(function (c) {
      var ev = c.events.map(function (e) {
        return "<tr><td><span class='kind k-" + e.kind + "'>" + (LABEL[e.kind] || e.kind) + "</span></td><td class='mono'>" + esc(e.actor) + "</td><td>" + esc(e.text) + "</td></tr>";
      }).join("");
      var d = c.decision[0];
      return '<details class="case"><summary><span class="cn">Case ' + c.id + '</span><span class="chip ' + (CHIP[c.state] || "") + '">' + name(c.state) + '</span>' +
        '<span class="cq">“' + esc(c.quote) + '”</span><span class="cm mono">patient ' + esc(c.patient) + ' · ' + esc(c.topic) + ' · owner ' + esc(c.owner || "none") + "</span></summary>" +
        '<div class="cbody"><dl class="facts"><dt>Conflicts with</dt><dd class="mono">' + esc(c.order) + ' at chart v' + esc(c.version) + "</dd>" +
        "<dt>Patient says</dt><dd>" + esc(c.says) + "</dd>" +
        (d ? "<dt>Decision</dt><dd>" + esc(d.doctor) + ": " + esc(d.change) + " (chart v" + d.frm + " → v" + d.to + ")</dd>" : "") + "</dl>" +
        '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Kind</th><th>By</th><th>What</th></tr></thead><tbody>' + ev + "</tbody></table></div></div></details>";
    }).join("");
  }
  draw();
})();
