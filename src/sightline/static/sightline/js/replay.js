/*
 * Sightline replay player.
 *
 * What it replays, said plainly: the visitor's pointer, scrolling, clicks
 * and typing markers, drawn over the page as it exists now. It is not a
 * DOM recording. Nothing about the visitor's screen contents is stored, so
 * nothing about it can be shown, and a page redesigned since the visit
 * replays against the new design.
 *
 * Two things about the frame are worth knowing.
 *
 * The page is fetched and written into the frame, not loaded by URL.
 * Django sends X-Frame-Options: DENY on every response by default, and
 * plenty of sites add it again at the proxy, so pointing an iframe at your
 * own page shows a broken document icon and nothing else. Fetching the
 * HTML and writing it in sidesteps that entirely: there is no navigation,
 * so there is no header to refuse it. Scripts are stripped on the way in,
 * which also stops the recorded page from recording the replay.
 *
 * The frame is sized to the viewport the visitor had and then scaled down
 * to fit the stage. Replaying a 390 pixel phone visit in a 900 pixel box
 * would show the desktop layout with a cursor wandering over the wrong
 * elements.
 */
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

  // ---------------------------------------------------------------- frame
  function fit() {
    if (!view) { return; }
    var width = view.viewport[0] || 1280;
    var height = view.viewport[1] || 800;
    var room = stage.clientWidth || width;
    scale = Math.min(room / width, 1);

    frame.style.width = width + "px";
    frame.style.height = height + "px";
    scaler.style.transform = "scale(" + scale + ")";
    // The stage keeps the shape of the screen the visitor actually had.
    stage.style.height = Math.round(height * scale) + "px";
  }

  function dress(html, path) {
    // A base tag so the page's own relative URLs still resolve, and no
    // scripts: the replay only needs the page to look right, and running
    // the site's JavaScript inside it would start a second recording.
    var cleaned = html
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
      .replace(/<script\b[^>]*\/>/gi, "");
    var base = '<base href="' + path + '">';
    if (/<head[^>]*>/i.test(cleaned)) {
      return cleaned.replace(/<head([^>]*)>/i, "<head$1>" + base);
    }
    return base + cleaned;
  }

  function loadPage(path) {
    say("");
    frame.srcdoc = "";
    fetch(path, { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) { throw new Error(String(r.status)); }
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
    loadPage(view.path);
    markStep(index);
  }

  function markStep(index) {
    var rows = stepList.querySelectorAll("[data-step]");
    for (var i = 0; i < rows.length; i++) {
      rows[i].toggleAttribute("data-on", i === index);
    }
  }

  // ---------------------------------------------------------------- drawing
  function place(x, y, scroll) {
    // The frame is scrolled to where the visitor was, and the cursor is
    // drawn at the point they were on. Both are in the recorded page's own
    // pixels, so they only need the stage scale applied.
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

  function apply(row) {
    var kind = row[0], x = row[2], y = row[3], scroll = row[4];
    if (kind === "move" || kind === "scroll") { place(x, y, scroll); return; }
    if (kind === "click" || kind === "rage" || kind === "dead" || kind === "input") {
      place(x, y, scroll);
      pop(x, y, scroll, kind);
    }
  }

  // ---------------------------------------------------------------- playback
  function seek(to) {
    // Replayed from the start of the page so the scroll offset and cursor
    // land where they belong. Stepping backwards otherwise leaves the
    // frame scrolled wherever it happened to be.
    elapsed = to;
    cursorAt = 0;
    var lastRow = null;
    while (cursorAt < events.length && events[cursorAt][1] <= elapsed) {
      lastRow = events[cursorAt];
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
      stepList.innerHTML = payload.views.map(function (row, i) {
        return '<button type="button" class="sl-step" data-step="' + i + '">'
          + '<b>' + (i + 1) + '</b><span>' + row.path + '</span>'
          + '<em>' + fmt(row.durationMs) + '</em></button>';
      }).join("");
      loadView(0);
    })
    .catch(function () {
      say("This visit could not be loaded.");
    });
})(window, document);
