/**
 * Compte à rebours en temps réel.
 * Se met à jour toutes les secondes.
 * Cible : #countdown avec data-target (format ISO 8601).
 */

(function () {
    'use strict';

    function initCountdown() {
        const container = document.getElementById('countdown');
        if (!container) return;

        const targetDateStr = container.dataset.target;
        if (!targetDateStr) return;

        const targetDate = new Date(targetDateStr).getTime();
        if (isNaN(targetDate)) {
            console.warn('Countdown : date invalide', targetDateStr);
            return;
        }

        const daysEl = document.getElementById('cd-days');
        const hoursEl = document.getElementById('cd-hours');
        const minutesEl = document.getElementById('cd-minutes');
        const secondsEl = document.getElementById('cd-seconds');

        if (!daysEl || !hoursEl || !minutesEl || !secondsEl) return;

        let lastSeconds = -1;

        function pad(num, size) {
            let s = String(num);
            while (s.length < size) s = '0' + s;
            return s;
        }

        function tick(el, value) {
            if (!el) return;
            const formatted = pad(value, 2);
            if (el.textContent !== formatted) {
                el.textContent = formatted;
                el.classList.remove('tick');
                void el.offsetWidth;
                el.classList.add('tick');
            }
        }

        function update() {
            const now = Date.now();
            const diff = targetDate - now;

            if (diff <= 0) {
                daysEl.textContent = '00';
                hoursEl.textContent = '00';
                minutesEl.textContent = '00';
                secondsEl.textContent = '00';
                clearInterval(intervalId);
                return;
            }

            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);

            const daysFormatted = pad(days, days >= 100 ? 3 : 2);

            if (daysEl.textContent !== daysFormatted) {
                daysEl.textContent = daysFormatted;
            }

            tick(hoursEl, hours);
            tick(minutesEl, minutes);

            if (seconds !== lastSeconds) {
                tick(secondsEl, seconds);
                lastSeconds = seconds;
            }
        }

        update();
        const intervalId = setInterval(update, 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCountdown);
    } else {
        initCountdown();
    }

})();