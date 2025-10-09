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

// Background animation
const canvas = document.getElementById("bg-animation");
const ctx = canvas.getContext("2d");
let particles = [];

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();

class Particle {
    constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.size = Math.random() * 2 + 1;
        this.speedX = Math.random() * 1 - 0.5;
        this.speedY = Math.random() * 1 - 0.5;
    }
    update() {
        this.x += this.speedX;
        this.y += this.speedY;
        if (this.x > canvas.width || this.x < 0) this.speedX *= -1;
        if (this.y > canvas.height || this.y < 0) this.speedY *= -1;
    }
    draw() {
        ctx.fillStyle = "rgba(0,123,255,0.3)";
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
    }
}

function initParticles() {
    particles = [];
    for (let i = 0; i < 60; i++) {
        particles.push(new Particle());
    }
}

function animateParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach((p) => {
        p.update();
        p.draw();
    });
    requestAnimationFrame(animateParticles);
}

initParticles();
animateParticles();