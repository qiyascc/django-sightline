(function (window, document) {
  "use strict";

  var config = window.__sightlineOverlay || {};
  if (!config.dataUrl) { return; }

  var state = {
    kinds: "click,rage,dead",
    days: 30,
    device: "",
    mode: "heat",
    opacity: 0.75,
    radius: 26,
    data: null
  };

  var root = document.createElement("div");
  root.className = "sl-overlay";
  root.innerHTML = [
    '<canvas class="sl-canvas"></canvas>',
    '<div class="sl-scroll"></div>',
    '<div class="sl-bar">',
    '  <span class="sl-brand">Sightline</span>',
    '  <span class="sl-path"></span>',
    '  <select class="sl-mode">',
    '    <option value="heat">Clicks</option>',
    '    <option value="move">Attention</option>',
    '    <option value="scroll">Scroll depth</option>',
    '  </select>',
    '  <select class="sl-days">',
    '    <option value="1">Today</option>',
    '    <option value="7">7 days</option>',
    '    <option value="30" selected>30 days</option>',
    '    <option value="90">90 days</option>',
    '  </select>',
    '  <select class="sl-device">',
    '    <option value="">All devices</option>',
    '    <option value="desktop">Desktop</option>',
    '    <option value="tablet">Tablet</option>',
    '    <option value="mobile">Mobile</option>',
    '  </select>',
    '  <input class="sl-opacity" type="range" min="10" max="100" value="75">',
    '  <span class="sl-stats"></span>',
    '  <a class="sl-panel" href="' + (config.panelUrl || "#") + '">Panel</a>',
    '  <button class="sl-close" type="button">Close</button>',
    '</div>'
  ].join("");
  document.body.appendChild(root);

  var canvas = root.querySelector(".sl-canvas");
  var scrollBox = root.querySelector(".sl-scroll");
  var ctx = canvas.getContext("2d");

  function docSize() {
    var b = document.body, e = document.documentElement;
    return {
      w: Math.max(e.clientWidth, window.innerWidth || 0, 1),
      h: Math.max(b.scrollHeight, e.scrollHeight, b.offsetHeight, e.offsetHeight, 1)
    };
  }

  var ramp = (function () {
    var c = document.createElement("canvas");
    c.width = 256; c.height = 1;
    var g = c.getContext("2d");
    var grad = g.createLinearGradient(0, 0, 256, 0);
    grad.addColorStop(0.00, "rgba(0,0,255,0)");
    grad.addColorStop(0.25, "rgba(0,140,255,1)");
    grad.addColorStop(0.45, "rgba(0,220,160,1)");
    grad.addColorStop(0.65, "rgba(230,220,0,1)");
    grad.addColorStop(0.85, "rgba(255,130,0,1)");
    grad.addColorStop(1.00, "rgba(220,20,20,1)");
    g.fillStyle = grad;
    g.fillRect(0, 0, 256, 1);
    return g.getImageData(0, 0, 256, 1).data;
  })();

  function paintHeat(points, peak) {
    var size = docSize();
    canvas.width = size.w;
    canvas.height = size.h;
    ctx.clearRect(0, 0, size.w, size.h);
    if (!points.length || !peak) { return; }

    var radius = state.radius;
    for (var i = 0; i < points.length; i++) {
      var p = points[i];
      var weight = Math.min(p[2] / peak, 1);
      var grad = ctx.createRadialGradient(p[0], p[1], 0, p[0], p[1], radius);
      grad.addColorStop(0, "rgba(0,0,0," + weight + ")");
      grad.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p[0], p[1], radius, 0, Math.PI * 2);
      ctx.fill();
    }

    var image = ctx.getImageData(0, 0, size.w, size.h);
    var data = image.data;
    for (var j = 0; j < data.length; j += 4) {
      var value = data[j + 3];
      if (!value) { continue; }
      var offset = value * 4;
      data[j] = ramp[offset];
      data[j + 1] = ramp[offset + 1];
      data[j + 2] = ramp[offset + 2];
      data[j + 3] = Math.min(value + 40, 255);
    }
    ctx.putImageData(image, 0, 0);
  }

  function paintScroll(bands) {
    var size = docSize();
    canvas.width = size.w;
    canvas.height = size.h;
    ctx.clearRect(0, 0, size.w, size.h);
    scrollBox.innerHTML = "";
    if (!bands || !bands.length) { return; }

    var step = size.h / bands.length;
    for (var i = 0; i < bands.length; i++) {
      var pct = bands[i];
      ctx.fillStyle = "rgba(20,120,255," + (0.10 + (pct / 100) * 0.45) + ")";
      ctx.fillRect(0, i * step, size.w, step + 1);

      var tag = document.createElement("span");
      tag.className = "sl-band";
      tag.style.top = (i * step) + "px";
      tag.textContent = pct + "%";
      scrollBox.appendChild(tag);
    }
  }

  function draw() {
    if (!state.data) { return; }
    root.setAttribute("data-mode", state.mode);
    canvas.style.opacity = state.opacity;

    if (state.mode === "scroll") {
      paintScroll(state.data.scroll);
      return;
    }
    scrollBox.innerHTML = "";

    var size = docSize();
    var cols = state.data.columns || 60;
    var rows = state.data.rows || 200;
    var points = state.data.cells.map(function (cell) {
      return [
        ((cell[0] + 0.5) / cols) * size.w,
        ((cell[1] + 0.5) / rows) * size.h,
        cell[2]
      ];
    });
    paintHeat(points, state.data.peak);
  }

  function load() {
    state.kinds = state.mode === "move" ? "move" : "click,rage,dead";
    var which = config.pageId
      ? "?page=" + encodeURIComponent(config.pageId)
      : "?path=" + encodeURIComponent(config.path || location.pathname);
    var url = config.dataUrl
      + which
      + "&days=" + state.days
      + "&device=" + encodeURIComponent(state.device)
      + "&kinds=" + encodeURIComponent(state.kinds);

    root.querySelector(".sl-stats").textContent = "loading";
    fetch(url, { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.data = data;
        root.querySelector(".sl-path").textContent = data.page.path;
        root.querySelector(".sl-stats").textContent = data.views
          ? data.views + " views, " + data.clicks + " clicks"
          : "nothing recorded for this page yet";
        draw();
      })
      .catch(function () {
        root.querySelector(".sl-stats").textContent = "no data";
      });
  }

  root.querySelector(".sl-mode").addEventListener("change", function (e) {
    state.mode = e.target.value;
    load();
  });
  root.querySelector(".sl-days").addEventListener("change", function (e) {
    state.days = parseInt(e.target.value, 10) || 30;
    load();
  });
  root.querySelector(".sl-device").addEventListener("change", function (e) {
    state.device = e.target.value;
    load();
  });
  root.querySelector(".sl-opacity").addEventListener("input", function (e) {
    state.opacity = (parseInt(e.target.value, 10) || 75) / 100;
    canvas.style.opacity = state.opacity;
  });
  root.querySelector(".sl-close").addEventListener("click", function () {
    root.remove();
    var url = new URL(location.href);
    url.searchParams.delete("sightline");
    history.replaceState(null, "", url.toString());
  });

  var resizeTimer = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(draw, 200);
  });

  load();
})(window, document);
