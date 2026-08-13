/* The Hiko Company — hero canvas: drifting ion particles + occasional faint
 * lightning strokes. Vanilla JS, no dependencies. Performance-minded:
 * device-pixel-capped canvas, ~40 particles, work skipped when the hero is
 * offscreen or the tab is hidden, fully disabled under prefers-reduced-motion. */

(function () {
  "use strict";

  var canvas = document.getElementById("sky");
  if (!canvas) return;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  var ctx = canvas.getContext("2d");
  var particles = [];
  var bolts = [];
  var running = false;
  var visible = true;
  var W = 0;
  var H = 0;
  var DPR = 1;

  var YELLOW = "245, 197, 24";
  var BLUE = "62, 197, 255";

  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = canvas.clientWidth;
    H = canvas.clientHeight;
    canvas.width = Math.floor(W * DPR);
    canvas.height = Math.floor(H * DPR);
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }

  function makeParticles() {
    var count = Math.max(24, Math.min(44, Math.floor(W / 32)));
    particles = [];
    for (var i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * W,
        y: Math.random() * H,
        r: 0.6 + Math.random() * 1.5,
        vx: (Math.random() - 0.5) * 0.12,
        vy: -0.04 - Math.random() * 0.1,
        blue: Math.random() < 0.6,
        tw: Math.random() * Math.PI * 2
      });
    }
  }

  /* A lightning stroke: a jittered polyline from a random top point downward,
   * with one optional short branch. Fades over ~0.5 s. */
  function spawnBolt() {
    var x = W * (0.15 + Math.random() * 0.7);
    var y = -10;
    var pts = [[x, y]];
    var segs = 7 + Math.floor(Math.random() * 5);
    var reach = H * (0.35 + Math.random() * 0.3);
    for (var i = 0; i < segs; i++) {
      x += (Math.random() - 0.5) * 46;
      y += reach / segs;
      pts.push([x, y]);
    }
    var branch = null;
    if (Math.random() < 0.6 && pts.length > 4) {
      var k = 2 + Math.floor(Math.random() * (pts.length - 3));
      var bx = pts[k][0];
      var by = pts[k][1];
      branch = [[bx, by]];
      for (var j = 0; j < 3; j++) {
        bx += (Math.random() < 0.5 ? -1 : 1) * (12 + Math.random() * 22);
        by += 18 + Math.random() * 16;
        branch.push([bx, by]);
      }
    }
    bolts.push({ pts: pts, branch: branch, life: 1 });
  }

  function drawPath(pts, alpha, width, rgb) {
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.strokeStyle = "rgba(" + rgb + ", " + alpha + ")";
    ctx.lineWidth = width;
    ctx.stroke();
  }

  var last = 0;
  function frame(t) {
    if (!running) return;
    requestAnimationFrame(frame);
    if (!visible) return;
    if (t - last < 1000 / 45) return; /* cap ~45 fps */
    last = t;

    ctx.clearRect(0, 0, W, H);

    /* particles */
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.tw += 0.02;
      if (p.y < -4) { p.y = H + 4; p.x = Math.random() * W; }
      if (p.x < -4) p.x = W + 4;
      if (p.x > W + 4) p.x = -4;
      var a = 0.12 + 0.1 * (1 + Math.sin(p.tw)) * 0.5;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(" + (p.blue ? BLUE : YELLOW) + ", " + a + ")";
      ctx.fill();
    }

    /* rare, faint lightning */
    if (Math.random() < 0.004 && bolts.length < 2) spawnBolt();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (var b = bolts.length - 1; b >= 0; b--) {
      var bolt = bolts[b];
      bolt.life -= 0.045;
      if (bolt.life <= 0) { bolts.splice(b, 1); continue; }
      var glow = 0.10 * bolt.life;
      var core = 0.32 * bolt.life;
      drawPath(bolt.pts, glow, 5, YELLOW);
      drawPath(bolt.pts, core, 1.4, YELLOW);
      if (bolt.branch) drawPath(bolt.branch, core * 0.7, 1, YELLOW);
    }
  }

  function start() {
    if (running || reduceMotion.matches) return;
    running = true;
    resize();
    makeParticles();
    requestAnimationFrame(frame);
  }

  function stop() {
    running = false;
    ctx.clearRect(0, 0, W, H);
  }

  /* Static fallback for reduced motion: a quiet, fixed starfield. */
  function drawStatic() {
    resize();
    makeParticles();
    ctx.clearRect(0, 0, W, H);
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(" + (p.blue ? BLUE : YELLOW) + ", 0.16)";
      ctx.fill();
    }
  }

  window.addEventListener("resize", function () {
    resize();
    makeParticles();
    if (reduceMotion.matches) drawStatic();
  });

  document.addEventListener("visibilitychange", function () {
    visible = document.visibilityState === "visible";
  });

  /* Skip work when the hero scrolls out of view. */
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting && document.visibilityState === "visible";
    }).observe(canvas);
  }

  var onMotionChange = function () {
    if (reduceMotion.matches) { stop(); drawStatic(); }
    else { start(); }
  };
  if (reduceMotion.addEventListener) reduceMotion.addEventListener("change", onMotionChange);

  if (reduceMotion.matches) drawStatic();
  else start();
})();
