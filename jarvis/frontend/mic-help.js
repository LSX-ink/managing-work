// Microphone help: browsers only let a page use the microphone on a secure address (https, or localhost on the
// PC itself), and only once it has been allowed. When either is missing this shows a small panel saying exactly
// what to do, instead of Alfred quietly not hearing anything. main.js sends 'jarvis:mic-blocked' when the
// browser refuses the microphone.
(() => {
    const LOCAL = ['localhost', '127.0.0.1', '[::1]'];
    let panel = null;
    const ios = /iPhone|iPad|iPod/.test(navigator.userAgent);

    function localLink() {
        const port = location.port ? `:${location.port}` : '';
        return `http://localhost${port}/`;
    }

    function show(kind) {
        if (panel) panel.remove();
        panel = document.createElement('section');
        panel.id = 'mic-help'; panel.setAttribute('role', 'alertdialog'); panel.setAttribute('aria-labelledby', 'mic-help-title');
        const title = document.createElement('h2'); title.id = 'mic-help-title';
        const list = document.createElement('ol');
        const add = (text) => { const li = document.createElement('li'); li.textContent = text; list.append(li); };
        const buttons = document.createElement('div'); buttons.className = 'mic-help-buttons';
        if (kind === 'insecure') {
            title.textContent = 'MICROPHONE NEEDS A SECURE ADDRESS';
            if (ios) {
                add('Your iPhone only lets Alfred hear you on the https Tailscale link, not this address.');
                add('On the PC run: tailscale serve --bg 8340');
                add('Open the https://...ts.net link it prints, here in Safari.');
            } else {
                add(`This address (${location.host}) is not secure, so the browser blocks the microphone.`);
                add('On the PC Alfred runs on, open the localhost address instead (button below). It counts as secure.');
                add('On another device, use the https Tailscale link (tailscale serve --bg 8340).');
                const go = document.createElement('a'); go.href = localLink(); go.textContent = 'OPEN ' + localLink().replace('http://', '').replace(/\/$/, '');
                go.className = 'mic-help-go'; buttons.append(go);
            }
        } else {
            title.textContent = 'MICROPHONE IS BLOCKED FOR THIS PAGE';
            if (ios) {
                add('In Safari, tap the aA (or page settings) button at the left of the address bar.');
                add('Tap Website Settings, then set Microphone to Allow.');
                add('Reload the page and tap the orb.');
            } else {
                add('Click the icon at the left of the address bar (the padlock, the (i), or the crossed-out microphone).');
                add('Set Microphone to Allow.');
                add('Reload the page (Ctrl+F5). If it is still blocked, check Windows Settings > Privacy & security > Microphone: "Let desktop apps access your microphone" must be on.');
            }
            const again = document.createElement('button'); again.type = 'button'; again.textContent = 'RELOAD';
            again.addEventListener('click', () => location.reload()); buttons.append(again);
        }
        const close = document.createElement('button'); close.type = 'button'; close.textContent = 'CLOSE';
        close.addEventListener('click', () => { panel.remove(); panel = null; });
        buttons.append(close);
        panel.append(title, list, buttons);
        document.body.append(panel);
    }

    function check() {
        if (!window.isSecureContext && !LOCAL.includes(location.hostname)) { show('insecure'); return; }
        if (navigator.permissions && navigator.permissions.query) {
            navigator.permissions.query({ name: 'microphone' }).then((p) => {
                if (p.state === 'denied') show('blocked');
                p.onchange = () => { if (p.state !== 'denied' && panel) { panel.remove(); panel = null; } };
            }).catch(() => {});
        }
    }

    document.addEventListener('jarvis:mic-blocked', () => show(window.isSecureContext ? 'blocked' : 'insecure'));
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', check, { once: true });
    else check();
    window.JarvisMicHelp = { show };
})();
