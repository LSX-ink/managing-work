// Head only: by default the screen shows nothing but Alfred's floating head (the dotted wolf on the HUD themes,
// the orb on the plain one) on a plain dark background. Everything else still runs underneath: listening, spoken
// replies and notifications, the mic, pop-ups, approvals.
//   H        show or hide all the panels (remembered in this browser)
//   Esc      hide the panels again
//   any key  while hidden, typing a letter (or /) opens a small typing box; it hides again once the message is sent
// Loaded in <head> so the page never flashes the panels before hiding them, and so its keys are seen before hudplus.js.
(() => {
    const KEY = 'alfred-head-only';
    const root = document.documentElement;
    let on = true;
    try { on = localStorage.getItem(KEY) !== '0'; } catch (e) { /* private window: head only */ }
    root.classList.toggle('head-only', on);

    const $ = (id) => document.getElementById(id);
    const isOn = () => root.classList.contains('head-only');
    const typing = (target) => !!(target && target.closest && target.closest('input, textarea, select, [contenteditable]'));
    const popupsOpen = () => !!document.querySelector('#popups .popup:not(.shrunk), .hudplus-overlay, .hudplus-saver')
        || ($('memory-panel') && !$('memory-panel').hidden);

    function set(next) {
        root.classList.toggle('head-only', next);
        if (next) peek(false);
        try { localStorage.setItem(KEY, next ? '1' : '0'); } catch (e) { /* private window */ }
        dispatchEvent(new Event('resize'));   // canvases and folder stars measure again
    }
    const toggle = () => set(!isOn());

    // The typing box, shown on its own at the bottom while the panels are hidden.
    function peek(open, firstKey = '') {
        const input = $('type-input');
        if (!open) {
            root.classList.remove('head-peek');
            if (input && document.activeElement === input && isOn()) input.blur();
            return;
        }
        if (!input) return;
        root.classList.add('head-peek');
        if (firstKey) input.value += firstKey;
        input.focus();
        const end = input.value.length;
        try { input.setSelectionRange(end, end); } catch (e) { /* not a text box */ }
    }

    // Runs before hudplus.js and the pop-ups (capture, registered first), so while hidden a letter goes to the box.
    addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey || e.altKey || e.isComposing || e.defaultPrevented) return;
        const key = e.key || '';
        if (typing(e.target)) {
            if (key === 'Escape' && e.target === $('type-input') && root.classList.contains('head-peek')) {
                e.target.value = '';
                peek(false);
            }
            return;
        }
        if (key === 'h' || key === 'H') {
            if (document.querySelector('.hudplus-overlay, .hudplus-saver')) return;
            e.preventDefault();
            e.stopImmediatePropagation();
            toggle();
            return;
        }
        if (key === 'Escape') {
            if (!isOn() && !popupsOpen()) set(true);   // pop-ups and the memory folder close first
            return;
        }
        if (!isOn() || key.length !== 1) return;
        if (key === '/') {
            e.preventDefault();
            e.stopImmediatePropagation();
            peek(true);
            return;
        }
        // An open pop-up (a game, a slideshow) may want its keys; a space on a focused button presses it.
        if (popupsOpen()) return;
        if (key === ' ' && e.target && e.target.closest && e.target.closest('button')) return;
        if (key.trim() === '') return;
        e.preventDefault();
        e.stopImmediatePropagation();
        peek(true, key);
    }, true);

    // Alt+T (access.js) or any other way into the box shows it too; leaving it empty hides it.
    document.addEventListener('focusin', (e) => {
        if (isOn() && e.target && e.target.id === 'type-input') root.classList.add('head-peek');
    });
    document.addEventListener('focusout', (e) => {
        if (!e.target || e.target.id !== 'type-input') return;
        setTimeout(() => {
            const input = $('type-input');
            if (input && document.activeElement !== input && !input.value.trim()) peek(false);
        }, 0);
    });
    // Sent: hide again. main.js clears the box in its own submit handler, which runs after this one.
    document.addEventListener('submit', (e) => {
        if (e.target && e.target.id === 'type-form' && isOn()) setTimeout(() => peek(false), 0);
    });

    window.AlfredHead = { toggle, show: () => set(false), hide: () => set(true), isOn };
})();
