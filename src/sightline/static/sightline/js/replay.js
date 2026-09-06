/*
 * Sightline replay player.
 *
 * What it replays, said plainly: the visitor's pointer, scrolling, clicks
 * and typing markers, drawn over the page as it exists now. It is not a
 * DOM recording. Nothing about the visitor's screen contents is stored, so
 * nothing about it can be shown, and a page that has been redesigned since
 * the visit will replay against the new design.
 *
 * That trade is the reason the recorder stays small and the database stays
 * cheap. It answers "where did they go and what did they hit", which is
 * the question a heatmap raises and cannot answer on its own.
 */
(function (window, document) {
  "use strict";

  var config = window.__sightlineReplay || {};
  if (!config.dataUrl) { return; }

  var frame = document.getElementById("sl-frame");
  var cursor = document.getElementById("sl-cursor");
  var ripple = document.getElementById("sl-ripple");
  var timeline = document.getElementById("sl-timeline");
  var playBtn = document.getElementById("sl-play");
  var speedSel = document.getElementById("sl-speed");
  var clock = document.getElementById("sl-clock");
  var pageLabel = document.getElementById("sl-page");
  var stepList = document.getElementById("sl-steps");

  var data = null;
  var viewIndex = 0;
  var events = [];
  var cursorAt = 0;
  var elapsed = 0;
  var playing = false;
  var speed = 1;
  var last = 0;
  var raf = null;

  function fmt(ms) {
    var total = Math.round(ms / 1000);
    var m = Math.floor(total / 60);
    var s = total % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
  }

  function loadView(index) {
    var view = data.views[index];
    if (!view) { return; }
    viewIndex = index;
    events = view.events;
    cursorAt = 0;
    elapsed = 0;
    timeline.max = Math.max(view.durationMs, 1000);
    timeline.value = 0;
    pageLabel.textContent = view.path;
    clock.textContent = "0:00 / " + fmt(view.durationMs);

    // The frame is loaded with the page the visitor was on. Same origin,
    // so scrolling it from here is allowed.
    frame.src = view.path;
    markStep(index);
  }

  function markStep(index) {
    var rows = stepList.querySelectorAll("[data-step]");
    for (var i = 0; i < rows.length; i++) {
      rows[i].toggleAttribute("data-on", i === index);
    }
  }

  function place(x, y, scroll) {
    // Event coordinates are absolute inside the document. The frame is
    // scrolled to the visitor's position and the cursor is drawn at the
    // point they were hovering, converted to frame coordinates.
    try {
      var win = frame.contentWindow;
      if (win) { win.scrollTo(0, scroll); }
    } catch (e) {}
    var rect = frame.getBoundingClientRect();
    var scale = rect.width / Math.max(data.views[viewIndex].viewport[0] || rect.width, 1);
    cursor.style.transform =
      "translate(" + (x * scale) + "px," + ((y - scroll) * scale) + "px)";
  }

  function pop(x, y, scroll, kind) {
    var rect = frame.getBoundingClientRect();
    var scale = rect.width / Math.max(data.views[viewIndex].viewport[0] || rect.width, 1);
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
    if (kind === "move") { place(x, y, scroll); return; }
    if (kind === "scroll") { place(x || 0, y, scroll); return; }
    if (kind === "click" || kind === "rage" || kind === "dead") {
      place(x, y, scroll);
      pop(x, y, scroll, kind);
      return;
    }
    if (kind === "input") { pop(x, y, scroll, "input"); }
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
    clock.textContent = fmt(elapsed) + " / " + fmt(data.views[viewIndex].durationMs);

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
    elapsed = parseInt(e.target.value, 10) || 0;
    cursorAt = 0;
    // Replay from the start of the page up to the new position so the
    // scroll offset and cursor land where they belong.
    while (cursorAt < events.length && events[cursorAt][1] <= elapsed) {
      apply(events[cursorAt]);
      cursorAt++;
    }
    clock.textContent = fmt(elapsed) + " / " + fmt(data.views[viewIndex].durationMs);
  });

  stepList.addEventListener("click", function (e) {
    var row = e.target.closest("[data-step]");
    if (!row) { return; }
    stop();
    loadView(parseInt(row.dataset.step, 10) || 0);
  });

  fetch(config.dataUrl, { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (payload) {
      data = payload;
      stepList.innerHTML = payload.views.map(function (view, i) {
        return '<button type="button" class="sl-step" data-step="' + i + '">'
          + '<b>' + (i + 1) + '</b><span>' + view.path + '</span>'
          + '<em>' + fmt(view.durationMs) + '</em></button>';
      }).join("");
      loadView(0);
    })
    .catch(function () {
      pageLabel.textContent = "This visit could not be loaded";
    });
})(window, document);
