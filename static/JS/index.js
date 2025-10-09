// Loader effect
document.getElementById("url-shortener-form").addEventListener("submit", function () {
    const btn = document.getElementById("submitBtn");
    btn.classList.add("loading");
});

// Copy animation
function copyToClipboard() {
    const input = document.getElementById("short-url");
    const copyBtn = document.getElementById("copy-btn");

    navigator.clipboard.writeText(input.value);
    copyBtn.innerHTML = '<i class="bi bi-check2"></i>';
    copyBtn.classList.add("btn-success");

    setTimeout(() => {
        copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
        copyBtn.classList.remove("btn-success");
    }, 1500);
}

// Floating shapes animation
const canvas = document.getElementById("floating-bg");
const ctx = canvas.getContext("2d");
let width, height;
let particles = [];

function resize() {
  width = canvas.width = window.innerWidth;
  height = canvas.height = window.innerHeight;
  initParticles();
}

function initParticles() {
  particles = [];
  for (let i = 0; i < 25; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      r: Math.random() * 4 + 1,
      dx: (Math.random() - 0.5) * 1,
      dy: (Math.random() - 0.5) * 1,
    });
  }
}

function draw() {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "rgba(255,255,255,0.6)";
  particles.forEach((p) => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fill();
    p.x += p.dx;
    p.y += p.dy;
    if (p.x < 0 || p.x > width) p.dx *= -1;
    if (p.y < 0 || p.y > height) p.dy *= -1;
  });
  requestAnimationFrame(draw);
}

window.addEventListener("resize", resize);
resize();
draw();