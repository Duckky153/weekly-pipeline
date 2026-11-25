(function () {
  "use strict";

  var ROWS_SHOWN = 4;
  var page = document.getElementById("page");
  var root = document.getElementById("drawer-root");
  var live = document.getElementById("live");
  var lastFocus = null;
  var opener = null;
  var W = null;

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "text") n.textContent = attrs[k];
        else if (k === "cls") n.className = attrs[k];
        else n.setAttribute(k, attrs[k]);
      });
    }
    (kids || []).forEach(function (c) {
      if (c === null || c === undefined) return;
      n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return n;
  }

  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }

  // tags from the notes check are moss green, so they never look like the rules' tags
  var NOTE = { "STEP DONE": 1, "NOT A STEP": 1, "CHECK STAGE": 1 };
  // up to two tags on a row: the rule tags first, then the AI's tag if there is room (every tag is in the drawer)
  function rowTags(r) { return r.push_tags.concat(r.note_tags || []).slice(0, 2); }
  function tagEl(t) { return el("span", { cls: "tag" + (t === "OVER LIMIT" ? " over" : NOTE[t] ? " note" : ""), text: t }); }

  // ------------------------------------------------------------ drawer

  function closeDrawer() {
    root.textContent = "";
    document.removeEventListener("keydown", onKey);
    var back = opener || lastFocus;
    opener = null;
    if (back) back.focus();
  }

  function onKey(e) {
    if (e.key === "Escape") closeDrawer();
    if (e.key === "Tab") {
      var f = root.querySelectorAll("button, a[href], [tabindex='0']");
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }

  function openDrawer(title, body, label) {
    lastFocus = document.activeElement;
    root.textContent = "";
    var close = el("button", { cls: "close", type: "button", text: "Close" });
    close.addEventListener("click", closeDrawer);
    var scrim = el("div", { cls: "scrim" });
    scrim.addEventListener("click", closeDrawer);
    var d = el("aside", { cls: "drawer", role: "dialog", "aria-modal": "true", "aria-labelledby": "drawer-h" }, [
      el("div", { cls: "drawer-head" }, [el("div", { cls: "titles" }, [label ? el("span", { cls: "label", text: label }) : null,
        el("h2", { id: "drawer-h", text: title })]), close]),
      el("div", { cls: "drawer-body", tabindex: "0" }, body)
    ]);
    root.appendChild(scrim);
    root.appendChild(d);
    document.addEventListener("keydown", onKey);
    close.focus();
  }

  function recountLine(key) {
    var r = W.recount && W.recount[key];
    if (!r) return null;
    return el("p", { cls: "foot", text: r.same ? "A separately written recount also got " + r.theirs + "." :
      "A separately written recount got " + r.theirs + "." });
  }

  // one deal per row, two lines: firm and city with the right-hand fact; then the owner and the detail
  function dealList(rows, right, detail, extra, open) {
    if (!rows.length) return null;
    return el("ul", { cls: "dlist" + (extra ? " three" : "") + (open ? " opens" : "") }, rows.map(function (r) {
      var name = r.firm ? [r.firm, r.city ? el("span", { cls: "city", text: " · " + r.city }) : null] : ["Deal " + r.id];
      var kids = [
        el("span", { cls: "firm" }, name),
        el("span", { cls: "right" }, right(r)),
        el("span", { cls: "detail", text: [r.owner].concat(detail(r) || []).filter(Boolean).join(" · ") }),
        extra ? el("span", { cls: "detail extra", text: extra(r) }) : null
      ];
      if (!open) return el("li", null, kids);
      var b = el("button", { type: "button" }, kids);
      b.addEventListener("click", function () { open(r); });
      return el("li", null, [b]);
    }));
  }

  function amount(r) { return [r.amount ? r.amount_text : "no amount"]; }

  function numberDrawer(n) {
    var detail = {
      new_qualified: function (r) { return ["Qualified " + r.date]; },
      moved_forward: function (r) { return [r.from + " \u2192 " + r.stage]; },
      won: function (r) { return ["Won " + r.date]; },
      lost: function (r) { return ["Lost " + r.date, r.why]; },
      open: function (r) { return [r.stage]; }
    }[n.key];
    var body = [el("p", { cls: "rule", text: "Rule: " + n.rule })];
    body.push(dealList(n.rows, amount, detail) || el("p", { cls: "empty", text: n.empty }));
    if (n.key === "lost" && n.before_qualified) {
      body.push(el("p", { cls: "foot", text: plural(n.before_qualified, "deal was", "deals were") + " lost before Qualified; not counted here." }));
    }
    if (n.value_text) body.push(el("p", { cls: "foot", text: "Total " + n.value_text + " a year." }));
    body.push(recountLine(n.key));
    openDrawer(n.label + " · " + n.count, body, "Last week");
  }

  function heldDrawer() {
    var h = W.held_out;
    var body = [el("p", { cls: "rule", text: h.rule })];
    if (!h.rows.length) body.push(el("p", { cls: "empty", text: "Every deal is counted." }));
    var groups = [];
    h.rows.forEach(function (r) {
      var g = groups[groups.length - 1];
      if (!g || g.reason !== r.reason) groups.push(g = { reason: r.reason, fixes: r.fixes, rows: [] });
      g.rows.push(r);
    });
    groups.forEach(function (g) {
      body.push(el("p", { cls: "group" }, [g.reason, el("span", { cls: "who", text: " · " + g.fixes + " to fix" })]));
      body.push(dealList(g.rows, amount, function (r) { return [r.stage]; }));
    });
    if (h.value_text) body.push(el("p", { cls: "foot", text: "Their amounts add up to " + h.value_text + " a year, across open, won and lost deals." }));
    body.push(recountLine("held_out"));
    openDrawer(plural(h.count, "deal", "deals") + " not counted", body, "Data problems");
  }

  function pushDrawer(r) {
    var facts = el("dl", { cls: "facts" }, [
      el("dt", { text: "Owner" }), el("dd", { text: r.owner }),
      el("dt", { text: "Stage" }), el("dd", { text: r.stage + " · " + plural(r.days_in_stage, "day", "days") }),
      el("dt", { text: "Last contact" }), el("dd", { text: r.contact.replace(/^last contact /, "").replace(/^no contact logged$/, "none logged") }),
      el("dt", { text: "Close date" }), el("dd", { text: r.close_date }),
      el("dt", { text: "Amount" }), el("dd", { text: r.amount_text + " a year" }),
      el("dt", { text: "Next" }), el("dd", { text: (r.next || "").replace(/^Next: (.)/, function (m, c) { return c.toUpperCase(); }) +
        ({ deal: " (the rep's own)", notes: " (suggested from the notes)", stage: " (suggested for the stage)" }[r.next_source] || "") })
    ]);
    var why = [];
    r.push_tags.forEach(function (t) { why.push(el("p", { cls: "why" }, [tagEl(t), " " + r.tag_text[t]])); });
    (r.note_tags || []).forEach(function (t) { why.push(el("p", { cls: "why" }, [tagEl(t), " " + r.note_tag_text[t]])); });
    openDrawer(r.firm + " · " + r.city, [facts, el("div", { cls: "whys" }, why)], "Needs a push");
  }

  function allPushDrawer() {
    var list = dealList(W.push, function (r) { return rowTags(r).map(tagEl); }, function (r) { return [r.status]; }, function (r) { return r.next; },
      function (r) { pushDrawer(r); });
    var lim = el("p", { cls: "foot", text: "Stage limits: " + W.limits_text + "." });
    openDrawer("Needs a push · " + W.push.length, [el("p", { cls: "rule", text: W.push_rule }), list, lim], "Monday review");
  }

  function barDrawer(b) {
    var body = [el("p", { cls: "rule", text: W.chart_rule + " " + b.week + " to " + b.week_end + "." })];
    body.push(dealList(b.rows, amount, function (r) { return ["Qualified " + r.date]; }) ||
      el("p", { cls: "empty", text: "No deal entered Qualified that week." }));
    openDrawer("Week of " + b.week + " · " + b.count, body, "New qualified deals");
  }

  // ------------------------------------------------------------ copy

  function copyText() {
    var lines = ["Needs a push (" + W.push.length + "), as of " + W.week.export_day];
    W.push.forEach(function (r) {
      var close = r.last_close_date && r.last_close_date !== r.close_date ? r.last_close_date + " to " + r.close_date : r.close_date;
      lines.push("- " + r.firm + " (" + r.city + "), " + r.owner + ": " + r.stage + ", " + plural(r.days_in_stage, "day", "days") +
        " [" + r.push_tags.join(", ") + "]. " + r.amount_text + " a year, close date " + close + ". " + r.next + ".");
    });
    return lines.join("\n");
  }

  function copy() {
    var text = copyText();
    var btn = document.getElementById("copy");
    function done(msg) { live.textContent = msg; btn.textContent = msg; setTimeout(function () { btn.textContent = "Copy for the sales meeting"; }, 1800); }
    function fallback() {
      var ta = el("textarea", { readonly: "" });
      ta.value = text;
      ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      done(ok ? "Copied" : "Copy failed");
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { done("Copied"); }, fallback);
    } else fallback();
  }

  // ------------------------------------------------------------ render

  function render() {
    var defs = document.getElementById("defs");
    W.definitions.forEach(function (d, i) {
      var dd = el("dd", { text: " " + d.text });
      defs.appendChild(el("div", { cls: "def" }, [el("dt", { text: d.term }), dd]));
    });

    document.getElementById("card-line").textContent = W.card.line;
    var detail = document.getElementById("card-detail");
    if (W.card.detail) detail.textContent = W.card.detail; else detail.hidden = true;
    var copyBtn = document.getElementById("copy");
    copyBtn.addEventListener("click", copy);
    copyBtn.style.minWidth = copyBtn.getBoundingClientRect().width + "px";
    if (!W.push.length) document.getElementById("copy").hidden = true;

    document.getElementById("week-when").textContent = W.week.start + " to " + W.week.end + " · as of " + W.week.export_day;
    var nums = document.getElementById("numbers");
    W.numbers.forEach(function (n) {
      var b = el("button", { cls: "num", type: "button" }, [
        el("span", { cls: "n", text: String(n.count) }),
        el("span", { cls: "what", text: n.label + (n.value_text ? " · " + n.value_text : "") })
      ]);
      b.addEventListener("click", function () { opener = b; numberDrawer(n); });
      nums.appendChild(b);
    });
    var held = document.getElementById("held");
    held.appendChild(document.createTextNode("Not counted: "));
    held.appendChild(el("b", { text: plural(W.held_out.count, "deal", "deals") + " with data problems" }));
    held.addEventListener("click", function () { opener = held; heldDrawer(); });

    document.getElementById("push-count").textContent = String(W.push.length);
    var rows = document.getElementById("rows");
    if (!W.push.length) rows.appendChild(el("li", { cls: "row" }, [el("p", { text: "No deal needs a push." })]));
    W.push.slice(0, ROWS_SHOWN).forEach(function (r) {
      var b = el("button", { type: "button" }, [
        el("span", { cls: "firm" }, [r.firm, el("span", { cls: "city", text: " · " + r.city })]),
        el("span", { cls: "status", text: r.status }),
        el("span", { cls: "tags" }, rowTags(r).map(tagEl)),
        el("span", { cls: "who", text: r.owner + " · " + r.contact }),
        el("span", { cls: "next", text: r.next })
      ]);
      b.addEventListener("click", function () { opener = b; pushDrawer(r); });
      rows.appendChild(el("li", { cls: "row" }, [b]));
    });
    var more = document.getElementById("more");
    if (W.push.length > ROWS_SHOWN) {
      more.hidden = false;
      more.textContent = "See all " + W.push.length;
      more.addEventListener("click", function () { opener = more; allPushDrawer(); });
    }

    var bars = document.getElementById("bars");
    var top = Math.max.apply(null, W.chart.map(function (b) { return b.count; }).concat([1]));
    W.chart.forEach(function (b) {
      var fill = el("span", { cls: "fill" });
      fill.style.height = Math.round((b.count / top) * 100) + "%";
      var bar = el("button", { cls: "bar" + (b.last ? " last" : ""), type: "button", "aria-label": "Week of " + b.week + ": " + b.count },
        [b.last ? el("span", { cls: "count", text: String(b.count) }) : null, fill]);
      bar.addEventListener("click", function () { opener = bar; barDrawer(b); });
      bars.appendChild(bar);
    });
    document.getElementById("axis-first").textContent = W.chart[0].week;
    document.getElementById("axis-last").textContent = W.chart[W.chart.length - 1].week;
    var tested = document.getElementById("tested");
    if (W.test_sentence) {
      tested.hidden = false;
      tested.appendChild(document.createTextNode(W.test_sentence + " "));
      tested.appendChild(el("a", { href: W.tested_link, text: "How it was tested" }));
    }
    page.setAttribute("aria-busy", "false");
  }

  fetch("data/week.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (w) { W = w; render(); })
    .catch(function () { page.textContent = "The week's data could not be loaded."; });
})();
