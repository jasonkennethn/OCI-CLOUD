/* ══════════════════════════════════════════════════════
   OCI Cloud Dashboard – Live Timer & Status Polling
   ══════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── Timer ──
    const nextRunIso = document.getElementById('dashboard')?.dataset.nextRun;
    let timerTarget = nextRunIso ? new Date(nextRunIso) : null;

    function padZero(n) {
        return String(n).padStart(2, '0');
    }

    function updateTimer() {
        if (!timerTarget) return;

        const now = new Date();
        let diff = Math.max(0, Math.floor((timerTarget - now) / 1000));

        const hours = Math.floor(diff / 3600);
        diff %= 3600;
        const minutes = Math.floor(diff / 60);
        const seconds = diff % 60;

        const hEl = document.getElementById('timer-hours');
        const mEl = document.getElementById('timer-minutes');
        const sEl = document.getElementById('timer-seconds');

        if (hEl) hEl.textContent = padZero(hours);
        if (mEl) mEl.textContent = padZero(minutes);
        if (sEl) sEl.textContent = padZero(seconds);
    }

    // Update timer every second
    if (timerTarget) {
        updateTimer();
        setInterval(updateTimer, 1000);
    }

    // ── Status Polling ──
    function fetchStatus() {
        fetch('/api/status/')
            .then(r => r.json())
            .then(data => {
                // Update allocation badge
                const badge = document.getElementById('status-badge');
                const icon = document.getElementById('status-icon');
                const title = document.getElementById('status-title');
                const sub = document.getElementById('status-sub');

                if (data.is_allocated) {
                    if (badge) {
                        badge.innerHTML = '<span class="dot dot--inactive"></span> Allocated';
                    }
                    if (icon) {
                        icon.className = 'status-hero__icon status-hero__icon--success';
                        icon.textContent = '✓';
                    }
                    if (title) title.textContent = 'Cloud Allocated';
                    if (sub) sub.textContent = 'Instance provisioned on ' + (data.allocated_at ? new Date(data.allocated_at).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'}) : 'N/A');

                    // Hide timer
                    const timerSection = document.getElementById('timer-section');
                    if (timerSection) timerSection.style.display = 'none';
                }

                // Update attempts counter
                const attemptsEl = document.getElementById('total-attempts');
                if (attemptsEl) attemptsEl.textContent = data.total_attempts;

                // Update last attempt status
                const lastStatusEl = document.getElementById('last-status');
                if (lastStatusEl && data.last_attempt_status) {
                    lastStatusEl.textContent = data.last_attempt_status;
                }

                // Update scheduler status
                const schedEl = document.getElementById('scheduler-status');
                if (schedEl) {
                    if (data.scheduler_active) {
                        schedEl.innerHTML = '<span class="badge badge--active"><span class="badge__dot"></span>Active</span>';
                    } else {
                        schedEl.innerHTML = '<span class="badge badge--pending"><span class="badge__dot"></span>Stopped</span>';
                    }
                }

                // Update next run timer target
                if (data.schedule && data.schedule.next_run) {
                    timerTarget = new Date(data.schedule.next_run);
                }
            })
            .catch(() => {});
    }

    // Poll every 30 seconds
    setInterval(fetchStatus, 30000);
})();
