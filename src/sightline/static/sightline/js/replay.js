(function (window, document) {
  "use strict";

  var config = window.__sightlineReplay || {};
  if (!config.dataUrl) { return; }

  var stage = document.getElementById("sl-stage");
  var scaler = document.getElementById("sl-scaler");
  var frame = document.getElementById("sl-frame");
  var cursor = document.getElementById("sl-cursor");
  var ripple = document.getElementById("sl-ripple");
  var timeline = document.getElementById("sl-timeline");
  var playBtn = document.getElementById("sl-play");
  var speedSel = document.getElementById("sl-speed");
  var clock = document.getElementById("sl-clock");
  var pageLabel = document.getElementById("sl-page");
  var stepList = document.getElementById("sl-steps");
  var notice = document.getElementById("sl-notice");

  var data = null;
  var view = null;
  var viewIndex = 0;
  var events = [];
  var cursorAt = 0;
  var elapsed = 0;
  var playing = false;
  var speed = 1;
  var last = 0;
  var raf = null;
  var scale = 1;

  function fmt(ms) {
    var total = Math.round(ms / 1000);
    var m = Math.floor(total / 60);
    var s = total % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
  }

  function say(text) {
    if (notice) { notice.textContent = text || ""; notice.hidden = !text; }
  }

  function fit() {
    if (!view) { return; }
    var width = view.viewport[0] || 1280;
    var height = view.viewport[1] || 800;
    var room = stage.clientWidth || width;
    scale = Math.min(room / width, 1);

    frame.style.width = width + "px";
    frame.style.height = height + "px";
    scaler.style.transform = "scale(" + scale + ")";
    stage.style.height = Math.round(height * scale) + "px";
  }

  function attr(text) {
    return String(text)
      .replace(/&/g, "&amp;").replace(/"/g, "&quot;")
      .replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function sameSite(path) {
    if (typeof path !== "string" || path.charAt(0) !== "/") { return null; }
    if (path.charAt(1) === "/" || path.indexOf("\\") !== -1) { return null; }
    try {
      var url = new URL(path, window.location.origin);
      if (url.origin !== window.location.origin) { return null; }
      return url.pathname + url.search;
    } catch (e) {
      return null;
    }
  }

  function dress(html, path) {
    var cleaned = html
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
      .replace(/<script\b[^>]*\/>/gi, "");
    var base = '<base href="' + attr(path) + '">';
    if (/<head[^>]*>/i.test(cleaned)) {
      return cleaned.replace(/<head([^>]*)>/i, "<head$1>" + base);
    }
    return base + cleaned;
  }

  function loadPage(given) {
    say("");
    frame.srcdoc = "";
    var path = sameSite(given);
    if (!path) {
      say("This page is not on this site, so it is not loaded. "
          + "The pointer track below still plays.");
      return;
    }
    fetch(path, { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) { throw new Error(String(r.status)); }
        if (r.url && new URL(r.url).origin !== window.location.origin) {
          throw new Error("left the site");
        }
        return r.text();
      })
      .then(function (html) {
        frame.srcdoc = dress(html, path);
      })
      .catch(function () {
        say("This page could not be loaded. It may have been removed since "
            + "the visit. The pointer track below still plays.");
      });
  }

  function loadView(index) {
    view = data.views[index];
    if (!view) { return; }
    viewIndex = index;
    events = view.events;
    cursorAt = 0;
    elapsed = 0;
    timeline.max = Math.max(view.durationMs, 1000);
    timeline.value = 0;
    pageLabel.textContent = view.path;
    clock.textContent = "0:00 / " + fmt(view.durationMs);
    fit();
    flag("");
    forced = [];
    loadPage(view.path);
    markStep(index);
  }

  function markStep(index) {
    var rows = stepList.querySelectorAll("[data-step]");
    for (var i = 0; i < rows.length; i++) {
      rows[i].toggleAttribute("data-on", i === index);
    }
  }

  function place(x, y, scroll) {
    try {
      var win = frame.contentWindow;
      if (win) { win.scrollTo(0, scroll); }
    } catch (e) {}
    cursor.style.transform =
      "translate(" + (x * scale) + "px," + ((y - scroll) * scale) + "px)";
  }

  function pop(x, y, scroll, kind) {
    var dot = document.createElement("span");
    dot.className = "sl-pop" + (kind === "rage" ? " sl-pop--rage" : "")
                             + (kind === "dead" ? " sl-pop--dead" : "");
    dot.style.left = (x * scale) + "px";
    dot.style.top = ((y - scroll) * scale) + "px";
    ripple.appendChild(dot);
    setTimeout(function () { dot.remove(); }, 900);
  }

  function overlay(row) {
    var selector = row[5], label = row[6];
    var state = (row[7] && row[7].state) || "open";
    var doc = null;
    try { doc = frame.contentDocument; } catch (e) {}
    if (!doc) { return; }

    var node = null;
    try { node = doc.querySelector(selector); } catch (e) {}

    if (!node) {
      if (state === "open") {
        flag("Popup opened: " + (label || selector)
             + ". Not in this copy of the page, because it is only rendered "
             + "for signed out visitors.");
      } else {
        flag("");
      }
      return;
    }

    if (state === "open") {
      show(node, doc);
      flag("Popup open: " + (label || selector), true);
    } else {
      hide(node);
      flag("");
    }
  }

  var forced = [];

  function show(node, doc) {
    var win = doc.defaultView || window;
    var chain = [];
    var walk = node;
    while (walk && walk !== doc.body && walk !== doc.documentElement) {
      chain.push(walk);
      walk = walk.parentElement;
    }

    chain.forEach(function (el) {
      var before = {
        node: el,
        hidden: el.hasAttribute("hidden"),
        open: el.hasAttribute("data-open"),
        style: el.getAttribute("style")
      };
      forced.push(before);

      el.removeAttribute("hidden");
      el.setAttribute("data-open", "");

      var computed = win.getComputedStyle(el);
      if (computed.display === "none") { el.style.display = "block"; }
      if (computed.visibility === "hidden") { el.style.visibility = "visible"; }
      if (parseFloat(computed.opacity || "1") < 0.99) { el.style.opacity = "1"; }
      if (computed.transform && computed.transform !== "none") {
        el.style.transform = "none";
      }
    });

    if (node.tagName === "DIALOG" && !node.hasAttribute("open")) {
      try { node.showModal(); } catch (e) {
        try { node.show(); } catch (err) { node.setAttribute("open", ""); }
      }
    }
  }

  function hide(node) {
    restore();
    if (node && node.tagName === "DIALOG") {
      try { node.close(); } catch (e) { node.removeAttribute("open"); }
    }
  }

  function restore() {
    forced.forEach(function (before) {
      var el = before.node;
      if (before.hidden) { el.setAttribute("hidden", ""); }
      if (!before.open) { el.removeAttribute("data-open"); }
      if (before.style === null) { el.removeAttribute("style"); }
      else { el.setAttribute("style", before.style); }
    });
    forced = [];
  }

  function flag(text, quiet) {
    var box = document.getElementById("sl-flag");
    if (!box) { return; }
    box.textContent = text || "";
    box.hidden = !text;
    box.toggleAttribute("data-quiet", !!quiet);
  }

  function apply(row) {
    var kind = row[0], x = row[2], y = row[3], scroll = row[4];
    if (kind === "overlay") { overlay(row); return; }
    if (kind === "move" || kind === "scroll") { place(x, y, scroll); return; }
    if (kind === "click" || kind === "rage" || kind === "dead" || kind === "input") {
      place(x, y, scroll);
      pop(x, y, scroll, kind);
    }
  }

  function seek(to) {
    elapsed = to;
    cursorAt = 0;
    restore();
    flag("");
    var lastRow = null;
    while (cursorAt < events.length && events[cursorAt][1] <= elapsed) {
      if (events[cursorAt][0] === "overlay") { overlay(events[cursorAt]); }
      else { lastRow = events[cursorAt]; }
      cursorAt++;
    }
    if (lastRow) { place(lastRow[2], lastRow[3], lastRow[4]); }
    timeline.value = Math.min(elapsed, timeline.max);
    clock.textContent = fmt(elapsed) + " / " + fmt(view.durationMs);
  }

  function tick(stamp) {
    if (!playing) { return; }
    if (!last) { last = stamp; }
    elapsed += (stamp - last) * speed;
    last = stamp;

    while (cursorAt < events.length && events[cursorAt][1] <= elapsed) {
      apply(events[cursorAt]);
      cursorAt++;
    }
    timeline.value = Math.min(elapsed, timeline.max);
    clock.textContent = fmt(elapsed) + " / " + fmt(view.durationMs);

    if (cursorAt >= events.length && elapsed >= timeline.max) {
      if (viewIndex + 1 < data.views.length) {
        loadView(viewIndex + 1);
        last = 0;
        raf = requestAnimationFrame(tick);
        return;
      }
      stop();
      return;
    }
    raf = requestAnimationFrame(tick);
  }

  function play() {
    playing = true;
    last = 0;
    playBtn.textContent = "Pause";
    raf = requestAnimationFrame(tick);
  }

  function stop() {
    playing = false;
    playBtn.textContent = "Play";
    cancelAnimationFrame(raf);
  }

  playBtn.addEventListener("click", function () {
    playing ? stop() : play();
  });

  speedSel.addEventListener("change", function (e) {
    speed = parseFloat(e.target.value) || 1;
  });

  timeline.addEventListener("input", function (e) {
    seek(parseInt(e.target.value, 10) || 0);
  });

  stepList.addEventListener("click", function (e) {
    var row = e.target.closest("[data-step]");
    if (!row) { return; }
    stop();
    loadView(parseInt(row.dataset.step, 10) || 0);
  });

  var resizeTimer = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(fit, 200);
  });

  fetch(config.dataUrl, { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (payload) {
      data = payload;
      if (!payload.views || !payload.views.length) {
        say("This visit has no recorded pages.");
        return;
      }
      stepList.textContent = "";
      payload.views.forEach(function (row, i) {
        var button = document.createElement("button");
        button.type = "button";
        button.className = "sl-step";
        button.setAttribute("data-step", String(i));
        var num = document.createElement("b");
        num.textContent = String(i + 1);
        var label = document.createElement("span");
        label.textContent = String(row.path);
        var time = document.createElement("em");
        time.textContent = fmt(row.durationMs);
        button.appendChild(num);
        button.appendChild(label);
        button.appendChild(time);
        stepList.appendChild(button);
      });
      loadView(0);
    })
    .catch(function () {
      say("This visit could not be loaded.");
    });
})(window, document);
