/* ============================================================
   BANTONDO'S GÉNÉRATION — PREMIUM ANIMATIONS
   Vanilla JS : comportement proche des interfaces React modernes
   ============================================================ */

(() => {
    "use strict";

    const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    /* ------------------------------
       Reveal on scroll
    ------------------------------ */

    const revealElements = document.querySelectorAll(
        ".fade-in-up, .fade-in, .slide-in-left, .slide-in-right"
    );

    if (reducedMotion || !("IntersectionObserver" in window)) {
        revealElements.forEach((element) => {
            element.classList.add("is-visible");
        });
    } else {
        const revealObserver = new IntersectionObserver(
            (entries, observer) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) return;

                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                });
            },
            {
                threshold: 0.12,
                rootMargin: "0px 0px -50px 0px"
            }
        );

        revealElements.forEach((element) => {
            revealObserver.observe(element);
        });
    }

    /* ------------------------------
       Navbar scroll effect
    ------------------------------ */

    const header = document.querySelector(".site-header");

    if (header) {
        const updateHeader = () => {
            if (window.scrollY > 20) {
                header.classList.add("is-scrolled");
            } else {
                header.classList.remove("is-scrolled");
            }
        };

        updateHeader();
        window.addEventListener("scroll", updateHeader, { passive: true });
    }

    /* ------------------------------
       Animated counters
    ------------------------------ */

    const counters = document.querySelectorAll("[data-counter]");

    const animateCounter = (element) => {
        const target = Number(element.dataset.counter);

        if (!Number.isFinite(target)) return;

        const duration = 1000;
        const start = performance.now();

        const tick = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const value = Math.round(target * eased);

            element.textContent = value.toLocaleString("fr-FR");

            if (progress < 1) {
                requestAnimationFrame(tick);
            }
        };

        requestAnimationFrame(tick);
    };

    if (counters.length) {
        if (reducedMotion || !("IntersectionObserver" in window)) {
            counters.forEach((counter) => {
                const value = Number(counter.dataset.counter);
                if (Number.isFinite(value)) {
                    counter.textContent = value.toLocaleString("fr-FR");
                }
            });
        } else {
            const counterObserver = new IntersectionObserver(
                (entries, observer) => {
                    entries.forEach((entry) => {
                        if (!entry.isIntersecting) return;

                        animateCounter(entry.target);
                        observer.unobserve(entry.target);
                    });
                },
                { threshold: 0.5 }
            );

            counters.forEach((counter) => {
                counterObserver.observe(counter);
            });
        }
    }

    /* ------------------------------
       Magnetic-like buttons
       ------------------------------ */

    if (!reducedMotion && window.matchMedia("(pointer:fine)").matches) {
        document.querySelectorAll(".btn-magnetic").forEach((button) => {
            button.addEventListener("pointermove", (event) => {
                const rect = button.getBoundingClientRect();
                const x = event.clientX - rect.left - rect.width / 2;
                const y = event.clientY - rect.top - rect.height / 2;

                button.style.transform =
                    `translate(${x * 0.06}px, ${y * 0.06}px)`;
            });

            button.addEventListener("pointerleave", () => {
                button.style.transform = "";
            });
        });
    }
})();
