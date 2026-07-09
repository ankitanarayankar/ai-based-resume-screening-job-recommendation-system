document.addEventListener('DOMContentLoaded', function () {
    const shell = document.getElementById('interview-shell');
    if (!shell) {
        return;
    }

    const form = document.getElementById('interview-form');
    const rulesModal = document.getElementById('rules-modal');
    const agreeRules = document.getElementById('agree-rules');
    const startButton = document.getElementById('start-interview-btn');
    const interviewPanel = document.getElementById('interview-panel');
    const timerElement = document.getElementById('timer');
    const fullscreenStatus = document.getElementById('fullscreen-status');
    const warningCount = document.getElementById('warning-count');
    const toast = document.getElementById('toast');

    let timeLeft = 900;
    let warnings = 0;
    let fullscreenViolations = 0;
    let timerStarted = false;
    let submitted = false;
    let timerInterval;

    function showToast(message, type = 'info') {
        toast.textContent = message;
        toast.className = `toast show ${type}`;
        clearTimeout(showToast.timeout);
        showToast.timeout = setTimeout(function () {
            toast.className = 'toast';
        }, 3200);
    }

    function updateFullscreenStatus() {
        fullscreenStatus.textContent = document.fullscreenElement ? 'Full Screen: On' : 'Full Screen: Off';
    }

    function updateWarningUI() {
        warningCount.textContent = `${warnings}/3`;
    }

    function autoSubmit(reason) {
        if (submitted) {
            return;
        }
        submitted = true;
        clearInterval(timerInterval);
        showToast(`Interview auto-submitted due to ${reason}.`, 'warning');
        setTimeout(function () {
            form.submit();
        }, 900);
    }

    function startTimer() {
        if (timerStarted) {
            return;
        }
        timerStarted = true;
        timerInterval = setInterval(function () {
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                autoSubmit('time expiry');
                return;
            }

            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            timerElement.textContent = minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
            timeLeft -= 1;
        }, 1000);
    }

    function requestFullscreen() {
        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen().catch(function () {
                showToast('Full-screen mode is required. Please allow it to continue.', 'warning');
            });
        } else {
            showToast('Full-screen mode is not supported in this browser.', 'warning');
        }
    }

    function handleViolation(type) {
        if (submitted) {
            return;
        }

        if (type === 'fullscreen') {
            fullscreenViolations += 1;
            showToast(`Full-screen exited. Violation ${fullscreenViolations}/3.`, 'warning');
            if (fullscreenViolations >= 3) {
                autoSubmit('multiple full-screen exits');
            }
        } else {
            warnings += 1;
            updateWarningUI();
            showToast(`Tab switch or minimize detected. Warning ${warnings}/3.`, 'warning');
            if (warnings >= 3) {
                autoSubmit('tab switching');
            }
        }
    }

    document.addEventListener('visibilitychange', function () {
        if (!timerStarted || submitted) {
            return;
        }
        if (document.hidden) {
            handleViolation('tab');
        }
    });

    document.addEventListener('blur', function () {
        if (!timerStarted || submitted) {
            return;
        }
        handleViolation('tab');
    });

    document.addEventListener('fullscreenchange', function () {
        updateFullscreenStatus();
        if (!timerStarted || submitted) {
            return;
        }
        if (!document.fullscreenElement) {
            handleViolation('fullscreen');
        }
    });

    startButton.addEventListener('click', function () {
        if (!agreeRules.checked) {
            showToast('Please accept the rules before starting the interview.', 'warning');
            return;
        }

        rulesModal.classList.remove('active');
        interviewPanel.classList.remove('is-hidden');
        fullscreenStatus.textContent = 'Full Screen: Requesting...';
        showToast('Interview started. Stay in full screen and avoid tab changes.', 'info');
        startTimer();
        requestFullscreen();
        fetch('/start_interview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    });

    form.addEventListener('submit', function () {
        submitted = true;
        clearInterval(timerInterval);
    });

    window.addEventListener('beforeunload', function (event) {
        if (timerStarted && !submitted) {
            event.preventDefault();
            event.returnValue = '';
        }
    });

    updateFullscreenStatus();
    updateWarningUI();
    timerElement.textContent = '15:00';
});