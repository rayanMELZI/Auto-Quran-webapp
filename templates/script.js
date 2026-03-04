// Smooth scrolling for navigation links
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        const targetId = this.getAttribute('href');
        if (targetId === '#home') {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
            const targetSection = document.querySelector(targetId);
            if (targetSection) {
                targetSection.scrollIntoView({ behavior: 'smooth' });
            }
        }
    });
});

// Language toggle functionality
const langButton = document.querySelector('.lang-button');
let isArabic = true;

langButton.addEventListener('click', function() {
    if (isArabic) {
        this.textContent = 'English';
        isArabic = false;
    } else {
        this.textContent = 'العربية';
        isArabic = true;
    }
});

// Button click effects
const followButtons = document.querySelectorAll('.follow-btn');
const visitButtons = document.querySelectorAll('.visit-btn');

followButtons.forEach(btn => {
    btn.addEventListener('click', function() {
        alert('Follow functionality would be implemented here');
    });
});

visitButtons.forEach(btn => {
    btn.addEventListener('click', function() {
        alert('Visit functionality would be implemented here');
    });
});

// Show All button
const showAllBtn = document.querySelector('.show-all-btn');
showAllBtn.addEventListener('click', function() {
    alert('Show all posts functionality would be implemented here');
});

// Service cards click
const serviceCards = document.querySelectorAll('.service-card');
serviceCards.forEach(card => {
    card.addEventListener('click', function() {
        const serviceName = this.querySelector('.service-title').textContent;
        alert(`Learn more about ${serviceName}`);
    });
});

// Add parallax effect to background
window.addEventListener('scroll', function() {
    const scrolled = window.pageYOffset;
    const bgImage = document.querySelector('.bg-image');
    if (bgImage) {
        bgImage.style.transform = `translateY(${scrolled * 0.5}px)`;
    }
});

// Add card hover effects
const cards = document.querySelectorAll('.card');
cards.forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-10px)';
        this.style.transition = 'transform 0.3s ease';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});

// Intersection Observer for fade-in animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe elements for animation
document.querySelectorAll('.channel, .card, .service-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
});

// Active navigation link highlighting
const sections = document.querySelectorAll('section');
const navLinks = document.querySelectorAll('.nav-link');

window.addEventListener('scroll', function() {
    let current = '';
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;
        if (pageYOffset >= sectionTop - 200) {
            current = section.getAttribute('id');
        }
    });
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${current}`) {
            link.classList.add('active');
        }
    });
});

// Add active link style
const style = document.createElement('style');
style.textContent = `
    .nav-link.active {
        text-decoration: underline;
        opacity: 1;
    }
`;
document.head.appendChild(style);
