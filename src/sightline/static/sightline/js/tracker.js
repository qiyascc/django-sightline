/*
 * Sightline collector.
 *
 * Runs on the visitor's page. Three rules keep it out of the way:
 *
 *   1. It never blocks. Everything happens on passive listeners and the
 *      network only sees a request every few seconds, or once on unload.
 *   2. It never reads content. Typing is recorded as "somebody typed
 *      here", never as what was typed.
 *   3. It never throws into the page. Every entry point is wrapped, so a
 *      bug here cannot break the site it is watching.
 */
(function (window, document) {
  "use strict";

  var config = window.__sightline || {};
  if (!config.collect) { return; }

  // Only the top window records. A page that embeds part of itself in an
  // iframe (a chat panel, a preview, a widget) would otherwise record the
  // frame as a separate visit, and the path it reports is whatever the
  // frame's own URL happens to be: "srcdoc", "about:blank", a fragment.
  // None of those are pages anybody can open, and they crowd out the real
  // ones in every report.
  try {
    if (window.top !== window.self) { return; }
  } catch (e) {
    // Cross origin parent. Same conclusion: not the top window.
    return;
  }

  var STORE_SESSION = "sightline.session";
  var STORE_SAMPLE = "sightline.sampled";
  var FLUSH_MS = 5000;
  var MAX_QUEUE = 400;

  // ---------------------------------------------------------------- sampling
  // The decision is made once and remembered, so a visitor is either
  // recorded for the whole visit or not at all. Sampling per page would
  // give half a session, which is worse than none.
  function sampled() {
    try {
      var stored = sessionStorage.getItem(STORE_SAMPLE);
      if (stored !== null) { return stored === "1"; }
      var pick = Math.random() < (config.sampleRate === undefined ? 1 : config.sampleRate);
      sessionStorage.setItem(STORE_SAMPLE, pick ? "1" : "0");
      return pick;
    } catch (e) {
      return true;
    }
  }
  if (!sampled()) { return; }

  // ---------------------------------------------------------------- state
  var started = Date.now();
  var queue = [];
  var sessionId = null;
  var pageviewId = null;
  var maxScroll = 0;
  var firstBatch = true;
  var lastMove = 0;
  var recentClicks = [];
  var timer = null;

  try { sessionId = sessionStorage.getItem(STORE_SESSION); } catch (e) {}

  function now() { return Date.now() - started; }

  function docHeight() {
    var b = document.body, e = document.documentElement;
    return Math.max(b ? b.scrollHeight : 0, e ? e.scrollHeight : 0,
                    b ? b.offsetHeight : 0, e ? e.offsetHeight : 0);
  }

  function docWidth() {
    var e = document.documentElement;
    return Math.max(e ? e.clientWidth : 0, window.innerWidth || 0, 1);
  }

  // ---------------------------------------------------------------- selectors
  // A short, stable path to an element. Ids win, then data-sightline, then
  // a class, then the tag with its position. Long CSS paths are avoided on
  // purpose: they change with every redesign and stop matching.
  function selectorFor(node) {
    if (!node || node === document || node === document.body) { return "body"; }
    if (node.id) { return "#" + node.id; }
    var marker = node.getAttribute && node.getAttribute("data-sightline");
    if (marker) { return "[data-sightline=\"" + marker + "\"]"; }

    var name = (node.tagName || "div").toLowerCase();
    var cls = (node.className && typeof node.className === "string")
      ? node.className.trim().split(/\s+/).slice(0, 2).join(".")
      : "";
    var base = cls ? name + "." + cls : name;

    var parent = node.parentElement;
    if (!parent) { return base; }
    var same = 0, index = 0, i;
    for (i = 0; i < parent.children.length; i++) {
      if (parent.children[i].tagName === node.tagName) {
        same++;
        if (parent.children[i] === node) { index = same; }
      }
    }
    if (same > 1) { base += ":nth-of-type(" + index + ")"; }
    var up = parent.id ? "#" + parent.id + " > " : "";
    return (up + base).slice(0, 300);
  }

  function masked(node) {
    var list = config.maskSelectors || [];
    for (var i = 0; i < list.length; i++) {
      try { if (node.closest && node.closest(list[i])) { return true; } } catch (e) {}
    }
    return false;
  }

  function labelFor(node) {
    if (!node || masked(node)) { return ""; }
    var tag = (node.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") { return ""; }
    var text = (node.innerText || node.textContent || "").trim();
    return text.replace(/\s+/g, " ").slice(0, 160);
  }

  // ---------------------------------------------------------------- queue
  function push(kind, extra) {
    if (queue.length >= MAX_QUEUE) { return; }
    var row = { k: kind, t: now() };
    if (extra) {
      for (var key in extra) {
        if (Object.prototype.hasOwnProperty.call(extra, key)) { row[key] = extra[key]; }
      }
    }
    queue.push(row);
  }

  function point(event) {
    var scroll = window.pageYOffset || document.documentElement.scrollTop || 0;
    var width = docWidth();
    var height = docHeight() || 1;
    var absX = event.pageX !== undefined ? event.pageX : (event.clientX || 0);
    var absY = event.pageY !== undefined ? event.pageY : (event.clientY || 0) + scroll;
    return {
      x: Math.round(absX),
      y: Math.round(absY),
      xp: Math.min(Math.max(absX / width, 0), 1),
      yp: Math.min(Math.max(absY / height, 0), 1),
      s: Math.round(scroll)
    };
  }

  // ---------------------------------------------------------------- sending
  function body(final) {
    return JSON.stringify({
      session: sessionId,
      pageview: pageviewId,
      url: location.pathname + location.search,
      title: (document.title || "").slice(0, 300),
      referrer: document.referrer || "",
      viewportWidth: window.innerWidth || 0,
      viewportHeight: window.innerHeight || 0,
      documentHeight: docHeight(),
      maxScrollPct: maxScroll,
      durationMs: now(),
      first: firstBatch,
      final: !!final,
      events: queue.splice(0, queue.length)
    });
  }

  function flush(final) {
    if (!queue.length && !final) { return; }
    var payload = body(final);
    firstBatch = false;

    // On unload only sendBeacon survives. Everywhere else fetch is used so
    // the answer can be read: it carries the ids the next batch needs.
    if (final && navigator.sendBeacon) {
      try {
        navigator.sendBeacon(config.collect, new Blob([payload], { type: "text/plain" }));
        return;
      } catch (e) {}
    }
    try {
      fetch(config.collect, {
        method: "POST",
        body: payload,
        headers: { "Content-Type": "application/json" },
        keepalive: true,
        credentials: "same-origin"
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (data && data.session) {
          sessionId = data.session;
          pageviewId = data.pageview;
          try { sessionStorage.setItem(STORE_SESSION, sessionId); } catch (e) {}
        }
      }).catch(function () {});
    } catch (e) {}
  }

  // ---------------------------------------------------------------- listeners
  function guard(fn) {
    return function (event) {
      try { fn(event); } catch (e) {}
    };
  }

  document.addEventListener("click", guard(function (event) {
    var node = event.target;
    var spot = point(event);
    var kind = "click";

    // Several clicks in the same place within a short window is somebody
    // hitting a thing that is not responding.
    var when = Date.now();
    recentClicks.push({ x: spot.x, y: spot.y, at: when });
    recentClicks = recentClicks.filter(function (c) {
      return when - c.at < (config.rageWindowMs || 1000);
    });
    var radius = config.rageRadius || 32;
    var near = recentClicks.filter(function (c) {
      return Math.abs(c.x - spot.x) < radius && Math.abs(c.y - spot.y) < radius;
    });
    if (near.length >= (config.rageCount || 3)) {
      kind = "rage";
      recentClicks = [];
    }

    // A click on nothing interactive, on a page that then does not change,
    // is worth knowing about. The cheap test is whether the target sits
    // inside anything clickable at all.
    if (kind === "click" && node.closest) {
      var live = node.closest("a,button,input,select,textarea,label,summary,[role=button],[onclick]");
      if (!live) { kind = "dead"; }
    }

    spot.sel = selectorFor(node);
    spot.lbl = labelFor(node);
    push(kind, spot);
    if (kind !== "click") { flush(false); }
  }), true);

  document.addEventListener("mousemove", guard(function (event) {
    var when = Date.now();
    if (when - lastMove < (config.moveSampleMs || 120)) { return; }
    lastMove = when;
    push("move", point(event));
  }), { passive: true });

  window.addEventListener("scroll", guard(function () {
    var scroll = window.pageYOffset || document.documentElement.scrollTop || 0;
    var height = docHeight();
    var seen = scroll + (window.innerHeight || 0);
    var pct = height ? Math.round(Math.min(seen / height, 1) * 100) : 0;
    if (pct > maxScroll) { maxScroll = pct; }
    push("scroll", { s: Math.round(scroll), y: Math.round(scroll), yp: pct / 100 });
  }), { passive: true });

  document.addEventListener("input", guard(function (event) {
    // The fact of typing, never the text.
    push("input", { sel: selectorFor(event.target) });
  }), true);

  window.addEventListener("resize", guard(function () {
    push("resize", { x: window.innerWidth || 0, y: window.innerHeight || 0 });
  }), { passive: true });

  window.addEventListener("error", guard(function (event) {
    push("error", { lbl: String(event.message || "").slice(0, 160) });
  }));

  // ---------------------------------------------------------------- overlays
  // A popup is a page in the only way that matters: the visitor is looking
  // at it. It has no URL, so nothing else in the recorder notices it, and
  // a replay without it shows somebody clicking on a page that was covered
  // at the time.
  //
  // Checked on a timer rather than through a mutation filter. An overlay
  // can be opened by a native dialog call, an attribute, a class or a
  // style, and one cheap loop catches all four where a filter would miss
  // three.
  var overlayState = {};

  function visible(node) {
    if (!node) { return false; }
    if (node.tagName === "DIALOG") { return node.hasAttribute("open"); }
    if (node.hasAttribute("hidden")) { return false; }
    if (!node.getClientRects().length) { return false; }
    var style = window.getComputedStyle(node);
    if (style.visibility === "hidden" || style.display === "none") { return false; }
    return parseFloat(style.opacity || "1") > 0.05;
  }

  function overlayName(node) {
    // A popup whose content arrives later, a chat panel for instance, has
    // no text at the moment it opens. Its own label is a better name than
    // an empty string, and far better than a CSS selector.
    var named = node.getAttribute("aria-label")
      || node.getAttribute("data-title")
      || node.getAttribute("title")
      || "";
    if (named) { return named.slice(0, 60); }
    var text = labelFor(node);
    if (text) { return text.slice(0, 60); }
    return (node.id || node.className || node.tagName || "").toString().slice(0, 60);
  }

  function scanOverlays() {
    var list = config.overlaySelectors || [];
    if (!list.length) { return; }
    var nodes;
    try {
      nodes = document.querySelectorAll(list.join(","));
    } catch (e) {
      return;
    }
    var seen = {};
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      var key = selectorFor(node);
      seen[key] = true;
      var now = visible(node);

      // First sighting. A closed overlay is the normal state of the page
      // and saying so would put a "closed" row at the top of every visit;
      // one that is already open when the page loads is worth recording.
      if (overlayState[key] === undefined) {
        overlayState[key] = now;
        if (!now) { continue; }
      } else if (overlayState[key] === now) {
        continue;
      }
      overlayState[key] = now;
      push("overlay", {
        sel: key,
        lbl: overlayName(node),
        m: { state: now ? "open" : "close" }
      });
      if (now) { flush(false); }
    }
    // An overlay removed from the page counts as closed.
    for (var known in overlayState) {
      if (overlayState[known] && !seen[known]) {
        overlayState[known] = false;
        push("overlay", { sel: known, m: { state: "close" } });
      }
    }
  }

  setInterval(guard(scanOverlays), config.overlayPollMs || 400);

  // ---------------------------------------------------------------- lifecycle
  timer = setInterval(function () { flush(false); }, FLUSH_MS);

  document.addEventListener("visibilitychange", guard(function () {
    if (document.visibilityState === "hidden") { flush(true); }
  }));
  window.addEventListener("pagehide", guard(function () { flush(true); }));
  window.addEventListener("beforeunload", guard(function () { flush(true); }));

  // First batch goes out early so the session exists before the visitor
  // leaves. A visit that lasted four seconds is still a visit.
  setTimeout(function () { flush(false); }, 1200);

  // A small door for the host project: sightline.mark("checkout-started").
  window.sightline = {
    mark: function (name, meta) {
      push("custom", { lbl: String(name || "").slice(0, 160), m: meta || {} });
    },
    flush: function () { flush(false); }
  };
})(window, document);
