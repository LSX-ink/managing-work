// Microphone help: when Alfred can't hear, this finds out why and shows a small panel with the exact fix.
// Browsers only allow the microphone on a secure address (https, or localhost on the PC itself), only once the
// page is allowed, only when Windows lets the browser use the microphone, and speech listening only works in
// browsers that offer it (Chrome and Edge). main.js sends 'jarvis:mic-blocked' with the browser's error code
// when listening is refused; this then tries the microphone directly to tell those cases apart.
(() => {
    const LOCAL = ['localhost', '127.0.0.1', '[::1]'];
    const ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
    let panel = null;

    function browserName() {
        const ua = navigator.userAgent;
        if (navigator.brave) return 'Brave';
        if (/OPR\/|Opera|OPX\//.test(ua)) return 'Opera';
        if (/Vivaldi/.test(ua)) return 'Vivaldi';
        if (/Edg\//.test(ua)) return 'Edge';
        if (/Firefox\//.test(ua)) return 'Firefox';
        if (/Chrome\//.test(ua)) return 'Chrome';
        if (/Safari\//.test(ua)) return 'Safari';
        return 'this browser';
    }
    const SPEECH_OK = ['Chrome', 'Edge', 'Safari'];   // browsers whose speech listening actually works

    function localLink() {
        return `http://localhost${location.port ? `:${location.port}` : ''}/`;
    }

    function close() { if (panel) { panel.remove(); panel = null; } }

    function button(text, onClick) {
        const b = document.createElement('button'); b.type = 'button'; b.textContent = text;
        b.addEventListener('click', onClick); return b;
    }

    function link(text, href) {
        const a = document.createElement('a'); a.href = href; a.textContent = text; a.className = 'mic-help-go'; return a;
    }

    function copyButton(text, value) {
        const b = button(text, () => {
            (navigator.clipboard ? navigator.clipboard.writeText(value) : Promise.reject()).then(
                () => { b.textContent = 'COPIED'; }, () => { b.textContent = value; });
        });
        return b;
    }

    const retry = () => button('TRY AGAIN', () => { close(); document.dispatchEvent(new Event('jarvis:mic-retry')); });

    // Each problem: a title, the steps, and the buttons that help.
    function problem(kind) {
        const browser = browserName();
        switch (kind) {
        case 'insecure':
            return ios ? {
                title: 'MICROPHONE NEEDS A SECURE ADDRESS',
                steps: ['Your iPhone only lets Alfred hear you on the https Tailscale link, not this address.',
                    'On the PC run: tailscale serve --bg 8340',
                    'Open the https://...ts.net link it prints, here in Safari.'],
                buttons: [],
            } : {
                title: 'MICROPHONE NEEDS A SECURE ADDRESS',
                steps: [`This address (${location.host}) is not secure, so the browser blocks the microphone.`,
                    'On the PC Alfred runs on, open the localhost address instead (button below). It counts as secure.',
                    'On another device, use the https Tailscale link (tailscale serve --bg 8340).'],
                buttons: [link('OPEN ' + localLink().replace('http://', '').replace(/\/$/, ''), localLink())],
            };
        case 'site':
            return {
                title: 'MICROPHONE IS BLOCKED FOR THIS PAGE',
                steps: ios ? ['In Safari, tap the aA button at the left of the address bar.',
                    'Tap Website Settings, then set Microphone to Allow.', 'Reload the page and tap the orb.']
                    : ['Click the icon at the left of the address bar.', 'Set Microphone to Allow.',
                        'Press TRY AGAIN (or reload with Ctrl+F5).'],
                buttons: [retry(), button('RELOAD', () => location.reload())],
            };
        case 'windows':
            return {
                title: 'WINDOWS IS BLOCKING THE MICROPHONE',
                steps: ['The page is allowed, but Windows is not letting ' + browser + ' use the microphone.',
                    'Open Windows mic settings (button below, or Start > Settings > Privacy & security > Microphone).',
                    'Turn ON "Microphone access", "Let apps access your microphone" and "Let desktop apps access your microphone".',
                    'Close ' + browser + ' completely, open it again, then press TRY AGAIN.'],
                buttons: [link('OPEN WINDOWS MIC SETTINGS', 'ms-settings:privacy-microphone'), retry()],
            };
        case 'nomic':
            return {
                title: 'NO MICROPHONE FOUND',
                steps: ['Windows can\'t find a microphone. Plug in your headset or mic.',
                    'Right-click the speaker icon on the taskbar > Sound settings > Input, and pick your microphone.',
                    'Then press TRY AGAIN.'],
                buttons: [link('OPEN SOUND SETTINGS', 'ms-settings:sound'), retry()],
            };
        case 'busy':
            return {
                title: 'THE MICROPHONE IS BUSY',
                steps: ['Another app is holding the microphone (Discord, Teams, Zoom, OBS or a game).',
                    'Close it, or turn off its mic, then press TRY AGAIN.',
                    'Still stuck: restart the PC, which frees the microphone.'],
                buttons: [retry()],
            };
        case 'service':
        default:
            return {
                title: 'THIS BROWSER CAN\'T LISTEN FOR ALFRED',
                steps: SPEECH_OK.includes(browser) ? [
                    'Your microphone works, but ' + browser + '\'s speech listening service refused.',
                    'Check you are online (the listening service is online), then press TRY AGAIN.',
                    'If it still fails, open Alfred in ' + (browser === 'Edge' ? 'Chrome' : 'Microsoft Edge') + ' instead.',
                ] : [
                    'Your microphone works, but ' + browser + ' does not include the speech listening Alfred uses.',
                    'Open Alfred in Google Chrome or Microsoft Edge instead (copy the address below).',
                    'You can still type to Alfred here.'],
                buttons: [copyButton('COPY ADDRESS', location.href.split('#')[0]), retry()],
            };
        }
    }

    function show(kind, detail) {
        close();
        const p = problem(kind);
        panel = document.createElement('section');
        panel.id = 'mic-help'; panel.setAttribute('role', 'alertdialog'); panel.setAttribute('aria-labelledby', 'mic-help-title');
        const title = document.createElement('h2'); title.id = 'mic-help-title'; title.textContent = p.title;
        const list = document.createElement('ol');
        p.steps.forEach((s) => { const li = document.createElement('li'); li.textContent = s; list.append(li); });
        const buttons = document.createElement('div'); buttons.className = 'mic-help-buttons';
        buttons.append(...p.buttons, button('CLOSE', close));
        const small = document.createElement('p'); small.className = 'mic-help-detail';
        small.textContent = `${browserName()} · ${location.host}${detail ? ' · ' + detail : ''}`;
        panel.append(title, list, buttons, small);
        document.body.append(panel);
    }

    async function sitePermission() {
        try { return (await navigator.permissions.query({ name: 'microphone' })).state; } catch { return 'unknown'; }
    }

    // Try the microphone directly: its error says whether the page, Windows, or the hardware is the problem.
    async function diagnose(speechError) {
        if (!window.isSecureContext) return show('insecure', speechError);
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return show('service', speechError);
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach((t) => t.stop());
            return show('service', speechError);   // the mic works: the speech service is what refused
        } catch (e) {
            const name = (e && e.name) || 'Error';
            const detail = `${speechError || 'mic'} · ${name}${e && e.message ? ': ' + e.message : ''}`;
            if (name === 'NotFoundError' || name === 'OverconstrainedError') return show('nomic', detail);
            if (name === 'NotReadableError' || name === 'AbortError') return show('busy', detail);
            if (name === 'NotAllowedError' || name === 'SecurityError') {
                const state = await sitePermission();
                // The page is allowed (or the message names the system), so Windows is the one saying no.
                if (state === 'granted' || /system/i.test(e.message || '')) return show('windows', detail);
                return show('site', detail);
            }
            return show('service', detail);
        }
    }

    function check() {
        if (!window.isSecureContext && !LOCAL.includes(location.hostname)) { show('insecure'); return; }
        if (navigator.permissions && navigator.permissions.query) {
            navigator.permissions.query({ name: 'microphone' }).then((p) => {
                if (p.state === 'denied') show('site');
                p.onchange = () => { if (p.state === 'granted') close(); };
            }).catch(() => {});
        }
    }

    document.addEventListener('jarvis:mic-blocked', (e) => diagnose(e.detail && e.detail.error));
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', check, { once: true });
    else check();
    window.JarvisMicHelp = { show, diagnose };
})();
