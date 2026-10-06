/**
 * Parallaxe subtile — effet de profondeur au mouvement de souris.
 * Activé uniquement sur desktop (pointer: fine).
 */

(function () {
    'use strict';

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isDesktop = window.matchMedia('(pointer: fine)').matches;

    if (reducedMotion || !isDesktop) return;

    // Parallaxe sur le hero
    const hero = document.querySelector('.hero-section');
    const heroGrid = hero ? hero.querySelector('::after') : null;

    if (hero) {
        const heroContent = hero.querySelector('.container');
        const heroBg = hero;

        let targetX = 0;
        let targetY = 0;
        let currentX = 0;
        let currentY = 0;

        hero.addEventListener('mousemove', (e) => {
            const rect = hero.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width - 0.5;
            const y = (e.clientY - rect.top) / rect.height - 0.5;

            targetX = x * 20;
            targetY = y * 20;
        });

        hero.addEventListener('mouseleave', () => {
            targetX = 0;
            targetY = 0;
        });

        function animate() {
            currentX += (targetX - currentX) * 0.08;
            currentY += (targetY - currentY) * 0.08;

            if (heroContent) {
                heroContent.style.transform =
                    `translate3d(${currentX}px, ${currentY}px, 0)`;
            }

            requestAnimationFrame(animate);
        }

        animate();
    }

    // Parallaxe sur les images du poster
    const posters = document.querySelectorAll('.poster-frame');

    posters.forEach((poster) => {
        poster.addEventListener('mousemove', (e) => {
            const rect = poster.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width - 0.5;
            const y = (e.clientY - rect.top) / rect.height - 0.5;

            poster.style.transform =
                `perspective(1000px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) scale(1.03)`;
        });

        poster.addEventListener('mouseleave', () => {
            poster.style.transform = '';
        });
    });

})();