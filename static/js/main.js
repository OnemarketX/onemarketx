


// ======================================
// OneMarketX FAQ Accordion + Mobile Menu
// static/js/main.js
// ======================================

// ---------- MOBILE NAVBAR ----------
const menuBtn = document.getElementById("menuBtn");
const closeBtn = document.getElementById("closeBtn");
const navMenu = document.getElementById("navMenu");

if (menuBtn && navMenu) {
    menuBtn.addEventListener("click", () => {
        navMenu.classList.add("active");
    });
}

if (closeBtn && navMenu) {
    closeBtn.addEventListener("click", () => {
        navMenu.classList.remove("active");
    });
}

document.addEventListener("click", (e) => {
    if (
        navMenu &&
        menuBtn &&
        !navMenu.contains(e.target) &&
        !menuBtn.contains(e.target)
    ) {
        navMenu.classList.remove("active");
    }
});

document.querySelectorAll(".nav-menu a").forEach(link => {
    link.addEventListener("click", () => {
        if (navMenu) {
            navMenu.classList.remove("active");
        }
    });
});


// ---------- FAQ ACCORDION ----------
const faqItems = document.querySelectorAll(".faq-item");

faqItems.forEach(item => {
    const question = item.querySelector(".faq-question");

    question.addEventListener("click", () => {

        // close others (optional premium behavior)
        faqItems.forEach(other => {
            if (other !== item) {
                other.classList.remove("active");
            }
        });

        // toggle current
        item.classList.toggle("active");
    });
});