// Scroll effect for header
document.addEventListener('scroll', function() {
    const header = document.querySelector('.head');
    if (window.scrollY > 50) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }
});

// Particle System
const particlesCanvas = document.getElementById('particles-canvas');
const ctx = particlesCanvas.getContext('2d');

function resizeCanvas() {
    particlesCanvas.width = window.innerWidth;
    particlesCanvas.height = window.innerHeight;
}

window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// Mouse repulsion effect
const mouse = {
    x: null,
    y: null,
    radius: 150
}

window.addEventListener('mousemove', function(event) {
    mouse.x = event.x;
    mouse.y = event.y;
});

class Particle {
    constructor(x, y, radius, color, opacity) {
        this.x = x;
        this.y = y;
        this.radius = radius;
        this.color = color;
        this.opacity = opacity;
        this.velocityX = Math.random() * 2 - 1;
        this.velocityY = Math.random() * 2 - 1;
        this.originalX = x;
        this.originalY = y;
    }

    draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2, false);
        ctx.fillStyle = `rgba(${this.color.r}, ${this.color.g}, ${this.color.b}, ${this.opacity})`;
        ctx.fill();
    }

    update() {
        // Move particles
        this.x += this.velocityX;
        this.y += this.velocityY;

        // Repel from mouse
        const dx = mouse.x - this.x;
        const dy = mouse.y - this.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const forceDirectionX = dx / distance;
        const forceDirectionY = dy / distance;
        const maxDistance = mouse.radius;
        const force = (maxDistance - distance) / maxDistance;
        const directionX = forceDirectionX * force * 2;
        const directionY = forceDirectionY * force * 2;

        if (distance < mouse.radius) {
            this.x -= directionX;
            this.y -= directionY;
        } else {
            // Return to original position
            if (this.x < this.originalX - 50) this.velocityX += 0.02;
            if (this.x > this.originalX + 50) this.velocityX -= 0.02;
            if (this.y < this.originalY - 50) this.velocityY += 0.02;
            if (this.y > this.originalY + 50) this.velocityY -= 0.02;
        }

        // Keep particles within bounds
        if (this.x < -50) this.x = window.innerWidth + 50;
        if (this.x > window.innerWidth + 50) this.x = -50;
        if (this.y < -50) this.y = window.innerHeight + 50;
        if (this.y > window.innerHeight + 50) this.y = -50;

        this.draw();
    }
}

// Create particles
const particlesArray = [];
const particleCount = (window.innerWidth * window.innerHeight) / 8000; // More particles for denser effect
const colors = [
    {r: 108, g: 99, b: 255}, // var(--accent-1)
    {r: 0, g: 212, b: 255},  // var(--accent-2)
    {r: 255, g: 107, b: 107} // var(--accent-3)
];

function initParticles() {
    particlesArray.length = 0;
    for (let i = 0; i < particleCount; i++) {
        const x = Math.random() * window.innerWidth;
        const y = Math.random() * window.innerHeight;
        const radius = Math.random() * 1.5 + 0.5;
        const color = colors[Math.floor(Math.random() * colors.length)];
        const opacity = Math.random() * 0.4 + 0.1;
        particlesArray.push(new Particle(x, y, radius, color, opacity));
    }
}

initParticles();
window.addEventListener('resize', initParticles);

function animateParticles() {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    for (let i = 0; i < particlesArray.length; i++) {
        particlesArray[i].update();
    }
    requestAnimationFrame(animateParticles);
}

animateParticles();

// Mouse parallax for background layers
document.addEventListener('mousemove', function(e) {
    const mouseX = e.clientX / window.innerWidth - 0.5;
    const mouseY = e.clientY / window.innerHeight - 0.5;

    document.getElementById('cosmic-gradient').style.transform = `translate(${mouseX * 15}px, ${mouseY * 15}px)`;
    document.getElementById('neon-edges').style.transform = `translate(${mouseX * 8}px, ${mouseY * 8}px)`;
});

// Scroll animations
const observerOptions = {
    threshold: 0.1
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, observerOptions);

document.querySelectorAll('.animate-in').forEach(el => {
    observer.observe(el);
});

// Ripple effect for buttons
document.querySelectorAll('.button-container button a, .hero-button button a, .booking button').forEach(button => {
    button.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');

        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);

        ripple.style.width = ripple.style.height = `${size}px`;
        ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
        ripple.style.top = `${e.clientY - rect.top - size / 2}px`;

        this.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
});

// Typewriter effect for hero subtitle
const heroSubtitle = document.querySelector('.hero-subtitle');
const text = heroSubtitle.textContent;
heroSubtitle.textContent = '';
let i = 0;

function typeWriter() {
    if (i < text.length) {
        heroSubtitle.textContent += text.charAt(i);
        i++;
        setTimeout(typeWriter, 50);
    }
}

// Start typewriter effect after a delay
setTimeout(typeWriter, 500);

// Form validation
document.getElementById('bookingForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const name = document.getElementById('name').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const date = document.getElementById('date').value;
    const time = document.getElementById('time').value;
    const computer = document.getElementById('computer').value;

    if (name && phone && date && time && computer) {
        alert('Спасибо за бронирование! Мы скоро свяжемся с вами.');
        this.reset();
    } else {
        alert('Пожалуйста, заполните все поля формы.');
    }
});