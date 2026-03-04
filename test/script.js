/* =============================================
   Portfolio Website — Main JavaScript
   =============================================
   Bao gồm:
   1. Loading Screen
   2. Custom Cursor
   3. Particles Background (Canvas)
   4. Navbar (sticky, active link, mobile menu)
   5. Typewriter Effect
   6. Theme Toggle (Dark/Light)
   7. AOS Init & GSAP Scroll Animations
   8. Skill Bar Animation
   9. Counter Animation
   10. Project Filter
   11. Tilt 3D Effect (Projects)
   12. Contact Form Validation
   13. Ripple Effect
   14. Back to Top
   15. Smooth Scroll
   ============================================= */

"use strict";

// ============================================
// 1. LOADING SCREEN
// ============================================
window.addEventListener("load", () => {
    const loader = document.getElementById("loader");
    // Ẩn loader sau khi trang đã tải xong
    setTimeout(() => {
        loader.classList.add("hidden");
        document.body.style.overflow = "auto";
        // Khởi tạo AOS sau khi loader biến mất
        initAOS();
        // Chạy GSAP hero animation
        animateHero();
    }, 1800);
});

// Chặn scroll khi đang loading
document.body.style.overflow = "hidden";

// ============================================
// 2. CUSTOM CURSOR
// ============================================
const cursorDot = document.getElementById("cursorDot");
const cursorRing = document.getElementById("cursorRing");

if (cursorDot && cursorRing) {
    let mouseX = 0, mouseY = 0;
    let ringX = 0, ringY = 0;

    // Theo dõi vị trí chuột
    document.addEventListener("mousemove", (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;

        // Dot di chuyển ngay lập tức
        cursorDot.style.left = mouseX - 4 + "px";
        cursorDot.style.top = mouseY - 4 + "px";
    });

    // Ring di chuyển mượt hơn (lerp)
    function animateCursorRing() {
        ringX += (mouseX - ringX) * 0.15;
        ringY += (mouseY - ringY) * 0.15;
        cursorRing.style.left = ringX - 18 + "px";
        cursorRing.style.top = ringY - 18 + "px";
        requestAnimationFrame(animateCursorRing);
    }
    animateCursorRing();

    // Hiệu ứng hover khi di chuột qua các phần tử tương tác
    const hoverTargets = document.querySelectorAll("a, button, .project-card, .glass-card, input, textarea");
    hoverTargets.forEach((el) => {
        el.addEventListener("mouseenter", () => {
            cursorDot.classList.add("hovered");
            cursorRing.classList.add("hovered");
        });
        el.addEventListener("mouseleave", () => {
            cursorDot.classList.remove("hovered");
            cursorRing.classList.remove("hovered");
        });
    });
}

// ============================================
// 3. PARTICLES BACKGROUND (Canvas)
// ============================================
const canvas = document.getElementById("particlesCanvas");
if (canvas) {
    const ctx = canvas.getContext("2d");
    let particles = [];
    const PARTICLE_COUNT = 80;

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // Tạo particle
    class Particle {
        constructor() {
            this.reset();
        }
        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 2 + 0.5;
            this.speedX = (Math.random() - 0.5) * 0.5;
            this.speedY = (Math.random() - 0.5) * 0.5;
            this.opacity = Math.random() * 0.5 + 0.1;
        }
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            // Quay lại khi ra ngoài màn hình
            if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
            if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(108, 99, 255, ${this.opacity})`;
            ctx.fill();
        }
    }

    // Khởi tạo particles
    for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push(new Particle());
    }

    // Vẽ đường nối giữa các particle gần nhau
    function drawConnections() {
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < 150) {
                    const opacity = (1 - distance / 150) * 0.15;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(108, 99, 255, ${opacity})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }
    }

    // Animation loop
    function animateParticles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach((p) => {
            p.update();
            p.draw();
        });
        drawConnections();
        requestAnimationFrame(animateParticles);
    }
    animateParticles();
}

// ============================================
// 4. NAVBAR
// ============================================
const navbar = document.getElementById("navbar");
const navLinks = document.getElementById("navLinks");
const hamburger = document.getElementById("hamburger");
const allNavLinks = document.querySelectorAll(".nav-link");

// Sticky navbar khi scroll
window.addEventListener("scroll", () => {
    if (window.scrollY > 50) {
        navbar.classList.add("scrolled");
    } else {
        navbar.classList.remove("scrolled");
    }
    updateActiveNavLink();
    handleBackToTop();
});

// Cập nhật nav link active dựa trên vị trí scroll
function updateActiveNavLink() {
    const sections = document.querySelectorAll("section[id]");
    const scrollPos = window.scrollY + 150;

    sections.forEach((section) => {
        const top = section.offsetTop;
        const height = section.offsetHeight;
        const id = section.getAttribute("id");

        if (scrollPos >= top && scrollPos < top + height) {
            allNavLinks.forEach((link) => link.classList.remove("active"));
            const activeLink = document.querySelector(`.nav-link[data-section="${id}"]`);
            if (activeLink) activeLink.classList.add("active");
        }
    });
}

// Mobile menu toggle
if (hamburger) {
    // Tạo overlay
    const overlay = document.createElement("div");
    overlay.className = "nav-overlay";
    document.body.appendChild(overlay);

    hamburger.addEventListener("click", () => {
        hamburger.classList.toggle("active");
        navLinks.classList.toggle("open");
        overlay.classList.toggle("show");
    });

    // Đóng menu khi click overlay
    overlay.addEventListener("click", () => {
        hamburger.classList.remove("active");
        navLinks.classList.remove("open");
        overlay.classList.remove("show");
    });

    // Đóng menu khi click nav link (mobile)
    allNavLinks.forEach((link) => {
        link.addEventListener("click", () => {
            hamburger.classList.remove("active");
            navLinks.classList.remove("open");
            overlay.classList.remove("show");
        });
    });
}

// ============================================
// 5. TYPEWRITER EFFECT
// ============================================
const typewriterEl = document.getElementById("typewriter");
if (typewriterEl) {
    const titles = [
        "Frontend Developer",
        "UI/UX Designer",
        "React Enthusiast",
        "Creative Coder",
        "Software Engineer",
    ];
    let titleIndex = 0;
    let charIndex = 0;
    let isDeleting = false;
    let typeSpeed = 80;

    function typewrite() {
        const currentTitle = titles[titleIndex];

        if (isDeleting) {
            // Xóa ký tự
            typewriterEl.textContent = currentTitle.substring(0, charIndex - 1);
            charIndex--;
            typeSpeed = 40;
        } else {
            // Gõ ký tự
            typewriterEl.textContent = currentTitle.substring(0, charIndex + 1);
            charIndex++;
            typeSpeed = 80;
        }

        // Hoàn thành gõ
        if (!isDeleting && charIndex === currentTitle.length) {
            isDeleting = true;
            typeSpeed = 2000; // Dừng trước khi xóa
        }
        // Hoàn thành xóa
        if (isDeleting && charIndex === 0) {
            isDeleting = false;
            titleIndex = (titleIndex + 1) % titles.length;
            typeSpeed = 300; // Dừng trước khi gõ title mới
        }

        setTimeout(typewrite, typeSpeed);
    }
    // Bắt đầu sau 2s (chờ loader)
    setTimeout(typewrite, 2200);
}

// ============================================
// 6. THEME TOGGLE (Dark / Light)
// ============================================
const themeToggle = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");

if (themeToggle) {
    // Lấy theme từ localStorage
    const savedTheme = localStorage.getItem("theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateThemeIcon(savedTheme);

    themeToggle.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme");
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("theme", next);
        updateThemeIcon(next);
    });

    function updateThemeIcon(theme) {
        if (themeIcon) {
            themeIcon.className = theme === "dark" ? "fas fa-moon" : "fas fa-sun";
        }
    }
}

// ============================================
// 7. AOS & GSAP ANIMATIONS
// ============================================
function initAOS() {
    AOS.init({
        duration: 800,
        easing: "ease-out-cubic",
        once: true,
        offset: 80,
        disable: "mobile", // Tắt trên mobile để tối ưu performance
    });
}

function animateHero() {
    // GSAP animation cho hero section
    if (typeof gsap === "undefined") return;

    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

    tl.from(".hero-greeting", { y: 30, opacity: 0, duration: 0.6 })
      .from(".hero-name", { y: 40, opacity: 0, duration: 0.7 }, "-=0.3")
      .from(".hero-title", { y: 30, opacity: 0, duration: 0.6 }, "-=0.3")
      .from(".hero-slogan", { y: 30, opacity: 0, duration: 0.6 }, "-=0.3")
      .from(".hero-buttons", { y: 30, opacity: 0, duration: 0.6 }, "-=0.3")
      .from(".hero-socials", { y: 20, opacity: 0, duration: 0.5 }, "-=0.2");

    // GSAP ScrollTrigger cho các section
    if (typeof ScrollTrigger !== "undefined") {
        gsap.registerPlugin(ScrollTrigger);

        // Parallax effect cho hero section
        gsap.to(".particles-canvas", {
            scrollTrigger: {
                trigger: ".hero-section",
                start: "top top",
                end: "bottom top",
                scrub: 1,
            },
            y: 100,
            opacity: 0.3,
        });

        // Animate skill bars khi scroll tới
        gsap.utils.toArray(".skill-fill").forEach((bar) => {
            const width = bar.getAttribute("data-width");
            gsap.to(bar, {
                width: width + "%",
                duration: 1.5,
                ease: "power2.out",
                scrollTrigger: {
                    trigger: bar,
                    start: "top 85%",
                    toggleActions: "play none none none",
                },
            });
        });

        // Stagger animation cho experience cards
        gsap.utils.toArray(".exp-card").forEach((card, i) => {
            gsap.from(card, {
                x: -50,
                opacity: 0,
                duration: 0.8,
                delay: i * 0.15,
                scrollTrigger: {
                    trigger: card,
                    start: "top 85%",
                    toggleActions: "play none none none",
                },
            });
        });

        // Section reveal animation
        gsap.utils.toArray(".section").forEach((section) => {
            gsap.from(section, {
                opacity: 0,
                y: 30,
                duration: 0.8,
                scrollTrigger: {
                    trigger: section,
                    start: "top 90%",
                    toggleActions: "play none none none",
                },
            });
        });
    }
}

// ============================================
// 8. SKILL BAR ANIMATION (Fallback nếu không có GSAP)
// ============================================
function animateSkillBars() {
    const skillBars = document.querySelectorAll(".skill-fill");
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const bar = entry.target;
                    const width = bar.getAttribute("data-width");
                    bar.style.width = width + "%";
                    observer.unobserve(bar);
                }
            });
        },
        { threshold: 0.5 }
    );

    skillBars.forEach((bar) => observer.observe(bar));
}
// Chạy fallback nếu GSAP ScrollTrigger không có
if (typeof ScrollTrigger === "undefined") {
    window.addEventListener("load", animateSkillBars);
}

// ============================================
// 9. COUNTER ANIMATION
// ============================================
function animateCounters() {
    const counters = document.querySelectorAll(".counter-number");
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const counter = entry.target;
                    const target = parseInt(counter.getAttribute("data-target"));
                    let current = 0;
                    const increment = target / 60; // ~60 bước
                    const duration = 2000; // 2 giây
                    const stepTime = duration / 60;

                    const timer = setInterval(() => {
                        current += increment;
                        if (current >= target) {
                            current = target;
                            clearInterval(timer);
                        }
                        counter.textContent = Math.floor(current);
                    }, stepTime);

                    observer.unobserve(counter);
                }
            });
        },
        { threshold: 0.5 }
    );

    counters.forEach((counter) => observer.observe(counter));
}
animateCounters();

// ============================================
// 10. PROJECT FILTER
// ============================================
const filterBtns = document.querySelectorAll(".filter-btn");
const projectCards = document.querySelectorAll(".project-card");

filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
        // Cập nhật active button
        filterBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        const filter = btn.getAttribute("data-filter");

        projectCards.forEach((card) => {
            const category = card.getAttribute("data-category");
            if (filter === "all" || category.includes(filter)) {
                card.classList.remove("hidden");
                card.style.animation = "fadeInUp 0.5s ease forwards";
            } else {
                card.classList.add("hidden");
            }
        });
    });
});

// ============================================
// 11. TILT 3D EFFECT (cho project cards)
// ============================================
if (window.innerWidth > 768) {
    projectCards.forEach((card) => {
        card.addEventListener("mousemove", (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = ((y - centerY) / centerY) * -8;
            const rotateY = ((x - centerX) / centerX) * 8;

            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
        });

        card.addEventListener("mouseleave", () => {
            card.style.transform = "perspective(1000px) rotateX(0) rotateY(0) translateY(0)";
            card.style.transition = "transform 0.5s ease";
        });

        card.addEventListener("mouseenter", () => {
            card.style.transition = "none";
        });
    });
}

// ============================================
// 12. CONTACT FORM VALIDATION
// ============================================
const contactForm = document.getElementById("contactForm");
if (contactForm) {
    contactForm.addEventListener("submit", (e) => {
        e.preventDefault();
        let isValid = true;

        // Lấy các field
        const name = document.getElementById("name");
        const email = document.getElementById("email");
        const subject = document.getElementById("subject");
        const message = document.getElementById("message");

        // Reset errors
        clearErrors();

        // Validate Name
        if (!name.value.trim()) {
            showError(name, "nameError", "Vui lòng nhập họ và tên");
            isValid = false;
        } else if (name.value.trim().length < 2) {
            showError(name, "nameError", "Tên phải có ít nhất 2 ký tự");
            isValid = false;
        }

        // Validate Email
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!email.value.trim()) {
            showError(email, "emailError", "Vui lòng nhập email");
            isValid = false;
        } else if (!emailRegex.test(email.value.trim())) {
            showError(email, "emailError", "Email không hợp lệ");
            isValid = false;
        }

        // Validate Subject
        if (!subject.value.trim()) {
            showError(subject, "subjectError", "Vui lòng nhập chủ đề");
            isValid = false;
        }

        // Validate Message
        if (!message.value.trim()) {
            showError(message, "messageError", "Vui lòng nhập tin nhắn");
            isValid = false;
        } else if (message.value.trim().length < 10) {
            showError(message, "messageError", "Tin nhắn phải có ít nhất 10 ký tự");
            isValid = false;
        }

        // Nếu tất cả hợp lệ
        if (isValid) {
            // Hiển thị thông báo thành công
            document.getElementById("formSuccess").classList.add("show");
            contactForm.reset();

            // Ẩn thông báo sau 5 giây
            setTimeout(() => {
                document.getElementById("formSuccess").classList.remove("show");
            }, 5000);
        }
    });

    function showError(input, errorId, message) {
        input.classList.add("error");
        document.getElementById(errorId).textContent = message;
    }

    function clearErrors() {
        document.querySelectorAll(".form-group input, .form-group textarea").forEach((el) => {
            el.classList.remove("error");
        });
        document.querySelectorAll(".form-error").forEach((el) => {
            el.textContent = "";
        });
    }

    // Xóa error khi user bắt đầu nhập
    document.querySelectorAll(".form-group input, .form-group textarea").forEach((input) => {
        input.addEventListener("input", () => {
            input.classList.remove("error");
            const errorEl = input.closest(".form-group").querySelector(".form-error");
            if (errorEl) errorEl.textContent = "";
        });
    });
}

// ============================================
// 13. RIPPLE EFFECT
// ============================================
document.querySelectorAll(".ripple-btn").forEach((btn) => {
    btn.addEventListener("click", function (e) {
        // Tạo phần tử ripple
        const ripple = document.createElement("span");
        ripple.classList.add("ripple");

        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        ripple.style.width = ripple.style.height = size + "px";
        ripple.style.left = e.clientX - rect.left - size / 2 + "px";
        ripple.style.top = e.clientY - rect.top - size / 2 + "px";

        this.appendChild(ripple);

        // Xóa ripple sau khi animation kết thúc
        setTimeout(() => ripple.remove(), 600);
    });
});

// ============================================
// 14. BACK TO TOP BUTTON
// ============================================
const backToTop = document.getElementById("backToTop");

function handleBackToTop() {
    if (!backToTop) return;
    if (window.scrollY > 400) {
        backToTop.classList.add("show");
    } else {
        backToTop.classList.remove("show");
    }
}

if (backToTop) {
    backToTop.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
}

// ============================================
// 15. SMOOTH SCROLL cho anchor links
// ============================================
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
        e.preventDefault();
        const targetId = this.getAttribute("href");
        if (targetId === "#") return;

        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
        }
    });
});

// ============================================
// 16. PARALLAX EFFECT nhẹ cho các section
// ============================================
window.addEventListener("scroll", () => {
    const scrolled = window.scrollY;

    // Parallax cho avatar
    const avatar = document.querySelector(".hero-avatar");
    if (avatar && window.innerWidth > 768) {
        avatar.style.transform = `translateY(${scrolled * 0.1}px)`;
    }
});
