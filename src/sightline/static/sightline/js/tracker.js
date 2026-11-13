(function (window, document) {
  "use strict";

  var config = window.__sightline || {};
  if (!config.collect) { return; }

  try {
    if (window.top !== window.self) { return; }
  } catch (e) {
    return;
  }

  var STORE_SESSION = "sightline.session";
  var STORE_SAMPLE = "sightline.sampled";
  var FLUSH_MS = 5000;
  var MAX_QUEUE = 400;

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

  function guard(fn) {
    return function (event) {
      try { fn(event); } catch (e) {}
    };
  }

  document.addEventListener("click", guard(function (event) {
    var node = event.target;
    var spot = point(event);
    var kind = "click";

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
    push("input", { sel: selectorFor(event.target) });
  }), true);

  window.addEventListener("resize", guard(function () {
    push("resize", { x: window.innerWidth || 0, y: window.innerHeight || 0 });
  }), { passive: true });

  window.addEventListener("error", guard(function (event) {
    push("error", { lbl: String(event.message || "").slice(0, 160) });
  }));

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
    for (var known in overlayState) {
      if (overlayState[known] && !seen[known]) {
        overlayState[known] = false;
        push("overlay", { sel: known, m: { state: "close" } });
      }
    }
  }

  setInterval(guard(scanOverlays), config.overlayPollMs || 400);

  timer = setInterval(function () { flush(false); }, FLUSH_MS);

  document.addEventListener("visibilitychange", guard(function () {
    if (document.visibilityState === "hidden") { flush(true); }
  }));
  window.addEventListener("pagehide", guard(function () { flush(true); }));
  window.addEventListener("beforeunload", guard(function () { flush(true); }));

  setTimeout(function () { flush(false); }, 1200);

  window.sightline = {
    mark: function (name, meta) {
      push("custom", { lbl: String(name || "").slice(0, 160), m: meta || {} });
    },
    flush: function () { flush(false); }
  };
})(window, document);
