// Screen games (arcade*.py): boards and cards Alfred plays against you, and games that run right here in the
// pop-up (sudoku, memory pairs, minesweeper, snake, 2048, maths sprint). Clicking a square sends a say line to
// Alfred. Games that run here stop their timers and key listeners once their window closes or is redrawn, only
// take keys when their window is the top one, and never while you're typing in a box.
(() => {
    const kinds = window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    const NS = 'http://www.w3.org/2000/svg';

    const svg = (tag, attrs = {}, parent) => {
        const n = document.createElementNS(NS, tag);
        for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
        if (parent) parent.append(n);
        return n;
    };

    // Timers and listeners that end by themselves once root leaves the page.
    function life(root) {
        const offs = [];
        const alive = () => root.isConnected;
        const stop = () => offs.splice(0).forEach((off) => off());
        const on = (target, type, fn, opts) => {
            const wrapped = (e) => (alive() ? fn(e) : stop());
            target.addEventListener(type, wrapped, opts);
            offs.push(() => target.removeEventListener(type, wrapped, opts));
        };
        const every = (ms, fn) => {
            const id = setInterval(() => (alive() ? fn() : stop()), ms);
            offs.push(() => clearInterval(id));
            return () => clearInterval(id);
        };
        const later = (ms, fn) => {
            const id = setTimeout(() => { if (alive()) fn(); }, ms);
            offs.push(() => clearTimeout(id));
        };
        const dog = setInterval(() => { if (!alive()) stop(); }, 1000);
        offs.push(() => clearInterval(dog));
        return { on, every, later, alive, stop };
    }

    const typing = (e) => e.target instanceof Element &&
        !!e.target.closest('input, textarea, select, [contenteditable=""], [contenteditable="true"]');

    // True when root's pop-up is showing and above every other pop-up.
    function onTop(root) {
        const win = root.closest('.popup');
        if (!win || win.classList.contains('shrunk') || !root.offsetParent) return false;
        const z = Number(win.style.zIndex) || 0;
        return [...document.querySelectorAll('.popup')].every((w) => w === win || (Number(w.style.zIndex) || 0) <= z);
    }

    const ARROWS = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right',
        w: 'up', s: 'down', a: 'left', d: 'right', W: 'up', S: 'down', A: 'left', D: 'right' };

    // Arrow keys (and WASD, space) for a game, only while its window is on top and you're not typing.
    function keys(game, root, handler) {
        game.on(window, 'keydown', (e) => {
            if (e.ctrlKey || e.altKey || e.metaKey || typing(e) || !onTop(root)) return;
            const key = ARROWS[e.key] || (e.key === ' ' ? 'space' : '');
            if (key && handler(key) !== false) e.preventDefault();
        });
    }

    const css = (root, name, fallback) => getComputedStyle(root).getPropertyValue(name).trim() || fallback;

    // ---- Boards against Alfred: noughts and crosses, Connect Four, battleships -------------------

    const SYMBOLS = { x: 'X', o: 'O', hit: '✕', sunk: '✕', miss: '•' };
    const NAMES = { x: 'your X', o: "Alfred's O", you: 'your counter', alfred: "Alfred's counter", ship: 'ship',
        hit: 'hit', sunk: 'sunk', miss: 'miss' };

    kinds['arcade-grid'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const root = el('div', `ag ag-${d.style || 'plain'}`);
        const boards = el('div', 'ag-boards');
        for (const g of d.grids || []) {
            const box = el('div', 'ag-board');
            if (g.label) box.append(el('div', 'ag-label', g.label));
            const grid = el('div', 'ag-cells');
            grid.style.gridTemplateColumns = `${g.axes ? '1.1em ' : ''}repeat(${g.cols}, 1fr)`;
            if (g.axes) {
                grid.append(el('span', 'ag-axis'));
                for (let c = 0; c < g.cols; c++) grid.append(el('span', 'ag-axis', String(c + 1)));
            }
            const marks = new Set(g.marks || []);
            for (let r = 0; r < g.rows; r++) {
                if (g.axes) grid.append(el('span', 'ag-axis', 'ABCDEFGHIJ'[r]));
                for (let c = 0; c < g.cols; c++) {
                    const i = r * g.cols + c, tok = (g.cells || [])[i] || '', say = (g.says || [])[i] || '';
                    const cell = el(say ? 'button' : 'div', `ag-cell tok-${tok || 'empty'}${marks.has(i) ? ' mark' : ''}`,
                        SYMBOLS[tok] || '');
                    const where = g.axes ? 'ABCDEFGHIJ'[r] + (c + 1) : `row ${r + 1} column ${c + 1}`;
                    cell.setAttribute('aria-label', `${where}: ${NAMES[tok] || 'empty'}`);
                    if (say) {
                        cell.type = 'button';
                        cell.title = say;
                        cell.addEventListener('click', () => { root.classList.add('waiting'); ask(say); });
                    }
                    grid.append(cell);
                }
            }
            box.append(grid);
            boards.append(box);
        }
        root.append(boards);
        if (d.status) root.append(el('div', 'ag-status', d.status));
        body.append(root);
    };

    // ---- Hangman ---------------------------------------------------------------------------------

    const GALLOWS = [
        ['line', { x1: 10, y1: 150, x2: 110, y2: 150 }], ['line', { x1: 35, y1: 150, x2: 35, y2: 12 }],
        ['line', { x1: 35, y1: 12, x2: 95, y2: 12 }], ['line', { x1: 95, y1: 12, x2: 95, y2: 30 }],
    ];
    const BODY = [
        ['circle', { cx: 95, cy: 42, r: 12 }], ['line', { x1: 95, y1: 54, x2: 95, y2: 96 }],
        ['line', { x1: 95, y1: 64, x2: 78, y2: 82 }], ['line', { x1: 95, y1: 64, x2: 112, y2: 82 }],
        ['line', { x1: 95, y1: 96, x2: 80, y2: 124 }], ['line', { x1: 95, y1: 96, x2: 110, y2: 124 }],
    ];

    kinds['arcade-hangman'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const root = el('div', 'ah');
        const top = el('div', 'ah-top');
        const pic = svg('svg', { viewBox: '0 0 130 160', class: 'ah-pic', role: 'img',
            'aria-label': `${d.misses || 0} of ${d.lives || 6} wrong guesses` });
        GALLOWS.forEach(([tag, a]) => svg(tag, { ...a, class: 'ah-frame' }, pic));
        BODY.slice(0, d.misses || 0).forEach(([tag, a]) => svg(tag, { ...a, class: 'ah-body' }, pic));
        const side = el('div', 'ah-side');
        side.append(el('div', `ah-word${d.over ? (d.won ? ' won' : ' lost') : ''}`, d.pattern || ''));
        side.append(el('div', 'ah-wrong', (d.wrong || []).length ? `Wrong: ${d.wrong.join(' ')}` : 'No wrong guesses yet'));
        top.append(pic, side);
        root.append(top);
        if (d.say) {
            const tried = new Set(d.guessed || []);
            const keysBox = el('div', 'ah-keys');
            for (const letter of 'ABCDEFGHIJKLMNOPQRSTUVWXYZ') {
                const b = el('button', 'ah-key', letter);
                b.type = 'button';
                b.disabled = tried.has(letter);
                b.addEventListener('click', () => {
                    keysBox.querySelectorAll('button').forEach((k) => { k.disabled = true; });
                    ask(d.say.replace('%s', letter));
                });
                keysBox.append(b);
            }
            root.append(keysBox);
        }
        body.append(root);
    };

    // ---- Wordle ----------------------------------------------------------------------------------

    const MARK = { g: 'right', y: 'near', '.': 'miss' };

    kinds['arcade-wordle'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const root = el('div', 'aw');
        const rows = el('div', 'aw-rows');
        for (let r = 0; r < (d.tries || 6); r++) {
            const row = el('div', 'aw-row'), guess = (d.rows || [])[r];
            for (let i = 0; i < 5; i++) {
                const tile = el('span', `aw-tile ${guess ? MARK[guess.marks[i]] : 'empty'}`, guess ? guess.word[i] : '');
                if (guess) tile.title = { g: 'right place', y: 'in the word', '.': 'not in the word' }[guess.marks[i]];
                row.append(tile);
            }
            rows.append(row);
        }
        root.append(rows);
        if (d.say) {
            const form = el('form', 'aw-form');
            const input = el('input', 'aw-input');
            Object.assign(input, { maxLength: 5, placeholder: 'Five letters', autocomplete: 'off', spellcheck: false });
            input.setAttribute('aria-label', 'Your guess');
            const go = el('button', 'pop-action', 'Guess');
            go.type = 'submit';
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const word = input.value.replace(/[^a-z]/gi, '');
                if (word.length !== 5) { input.classList.add('bad'); return; }
                input.disabled = go.disabled = true;
                ask(d.say.replace('%s', word.toUpperCase()));
            });
            input.addEventListener('input', () => input.classList.remove('bad'));
            form.append(input, go);
            root.append(form);
        } else if (d.answer) root.append(el('div', 'aw-answer', `The word was ${d.answer}`));
        const board = el('div', 'aw-keys');
        for (const line of ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM']) {
            const row = el('div', 'aw-keyrow');
            for (const ch of line) row.append(el('span', `aw-key ${MARK[(d.letters || {})[ch]] || ''}`, ch));
            board.append(row);
        }
        root.append(board);
        body.append(root);
    };

    // ---- Playing cards and bingo -----------------------------------------------------------------

    const SUIT = { S: '♠︎', H: '♥︎', D: '♦︎', C: '♣︎' };
    const SUIT_NAME = { S: 'spades', H: 'hearts', D: 'diamonds', C: 'clubs' };

    function playingCard(el, code) {
        if (code === '??') {
            const back = el('div', 'ac-card back');
            back.setAttribute('aria-label', 'face-down card');
            return back;
        }
        const rank = code.slice(0, -1), suit = code.slice(-1);
        const c = el('div', `ac-card${'HD'.includes(suit) ? ' red' : ''}`);
        c.setAttribute('aria-label', `${rank} of ${SUIT_NAME[suit]}`);
        c.append(el('span', 'ac-corner', `${rank}${SUIT[suit]}`), el('span', 'ac-pip', SUIT[suit]),
            el('span', 'ac-corner end', `${rank}${SUIT[suit]}`));
        return c;
    }

    kinds['arcade-cards'] = (card, body, { el }) => {
        const d = card.data || {};
        const root = el('div', 'ac');
        for (const hand of d.hands || []) {
            const box = el('div', 'ac-hand');
            box.append(el('div', 'ac-label', hand.total ? `${hand.label} · ${hand.total}` : hand.label));
            const row = el('div', 'ac-row');
            (hand.cards || []).forEach((code) => row.append(playingCard(el, code)));
            box.append(row);
            root.append(box);
        }
        if (d.status) root.append(el('div', 'ag-status', d.status));
        body.append(root);
    };

    kinds['arcade-bingo'] = (card, body, { el }) => {
        const d = card.data || {};
        const called = new Set(d.called || []);
        const root = el('div', 'ab');
        const head = el('div', 'ab-head');
        head.append(el('div', 'ab-last', d.last ? String(d.last) : '--'),
            el('div', 'ab-call', d.last ? (d.call || `Number ${d.last}`) : 'Eyes down'));
        root.append(head);
        const grid = el('div', 'ab-grid');
        for (let n = 1; n <= 90; n++) {
            grid.append(el('span', `ab-n${called.has(n) ? ' on' : ''}${n === d.last ? ' last' : ''}`, String(n)));
        }
        root.append(grid);
        const recent = (d.called || []).slice(-6, -1).reverse();
        root.append(el('div', 'ab-recent', `${called.size} of 90 called${recent.length ? ` · before that: ${recent.join(', ')}` : ''}`));
        body.append(root);
    };

    // ---- Sudoku (typed here; Check and Hint work here too) -----------------------------------------

    const sudokuEntries = new Map();  // puzzle id -> {cells: {index: digit}, started, solved}

    kinds['arcade-sudoku'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const givens = d.givens || [], solution = d.solution || [], fixedHints = new Set(d.hints || []);
        if (!sudokuEntries.has(d.id)) sudokuEntries.set(d.id, { cells: {}, started: Date.now(), solved: false });
        const saved = sudokuEntries.get(d.id);
        const root = el('div', 'as');
        const grid = el('div', 'as-grid');
        const inputs = [];
        for (let i = 0; i < 81; i++) {
            const r = Math.floor(i / 9), c = i % 9;
            const box = el('input', `as-cell${c % 3 === 2 && c < 8 ? ' right' : ''}${r % 3 === 2 && r < 8 ? ' bottom' : ''}`);
            Object.assign(box, { maxLength: 1, inputMode: 'numeric', autocomplete: 'off' });
            box.setAttribute('aria-label', `row ${r + 1} column ${c + 1}`);
            if (givens[i]) { box.value = givens[i]; box.readOnly = true; box.classList.add('given'); }
            else if (fixedHints.has(i)) { box.value = solution[i]; box.readOnly = true; box.classList.add('hinted'); }
            else if (saved.cells[i]) box.value = saved.cells[i];
            box.addEventListener('input', () => {
                box.value = box.value.replace(/[^1-9]/g, '').slice(-1);
                saved.cells[i] = box.value;
                box.classList.remove('wrong');
            });
            box.addEventListener('keydown', (e) => {
                const step = { ArrowUp: -9, ArrowDown: 9, ArrowLeft: -1, ArrowRight: 1 }[e.key];
                if (step && inputs[i + step]) { e.preventDefault(); inputs[i + step].focus(); }
            });
            inputs.push(box);
            grid.append(box);
        }
        const status = el('div', 'ag-status', saved.solved ? 'Solved!' : 'Fill every row, column and box with 1 to 9.');
        const check = () => {
            let empty = 0, wrong = 0;
            inputs.forEach((box, i) => {
                if (!box.value) empty++;
                else if (Number(box.value) !== solution[i]) { wrong++; box.classList.add('wrong'); }
            });
            if (!empty && !wrong) {
                status.textContent = 'Solved!';
                if (!saved.solved) {
                    saved.solved = true;
                    const minutes = Math.max(1, Math.round((Date.now() - saved.started) / 60000));
                    ask(`I finished the sudoku in ${minutes} minute${minutes === 1 ? '' : 's'}.`);
                }
            } else status.textContent = `${wrong} wrong, ${empty} still empty.`;
        };
        const hint = () => {
            const open = inputs.map((box, i) => i).filter((i) => !inputs[i].readOnly && Number(inputs[i].value) !== solution[i]);
            if (!open.length) return;
            const i = open[Math.floor(Math.random() * open.length)];
            inputs[i].value = saved.cells[i] = String(solution[i]);
            inputs[i].classList.remove('wrong');
            inputs[i].classList.add('hinted');
            status.textContent = `Row ${Math.floor(i / 9) + 1}, column ${i % 9 + 1} is ${solution[i]}.`;
        };
        const bar = el('div', 'arcade-bar');
        const checkBtn = el('button', 'pop-action', 'Check');
        const hintBtn = el('button', 'pop-action', 'Hint');
        const clearBtn = el('button', 'pop-action', 'Clear mistakes');
        checkBtn.addEventListener('click', check);
        hintBtn.addEventListener('click', hint);
        clearBtn.addEventListener('click', () => inputs.forEach((box, i) => {
            if (!box.readOnly && box.value && Number(box.value) !== solution[i]) {
                box.value = saved.cells[i] = '';
                box.classList.remove('wrong');
            }
        }));
        bar.append(checkBtn, hintBtn, clearBtn);
        root.append(grid, bar, status);
        body.append(root);
    };

    // ---- Memory pairs (simple shapes, no pictures) -----------------------------------------------

    const SHAPES = [
        ['circle', { cx: 20, cy: 20, r: 13 }], ['rect', { x: 8, y: 8, width: 24, height: 24 }],
        ['polygon', { points: '20,6 34,32 6,32' }], ['polygon', { points: '20,4 36,20 20,36 4,20' }],
        ['polygon', { points: '20,4 24,15 36,15 26,22 30,34 20,27 10,34 14,22 4,15 16,15' }],
        ['path', { d: 'M15 6h10v9h9v10h-9v9H15v-9H6V15h9z' }], ['circle', { cx: 20, cy: 20, r: 13, class: 'hollow' }],
        ['polygon', { points: '12,6 28,6 36,20 28,34 12,34 4,20' }], ['rect', { x: 8, y: 8, width: 24, height: 24, class: 'hollow' }],
        ['polygon', { points: '20,34 6,8 34,8' }],
    ];
    const SHAPE_NAMES = ['circle', 'square', 'triangle', 'diamond', 'star', 'cross', 'ring', 'hexagon', 'box', 'down triangle'];

    kinds['arcade-memory'] = (card, body, { el, ask }) => {
        const layout = (card.data || {}).layout || [];
        const root = el('div', 'am');
        const game = life(root);
        const grid = el('div', 'am-grid');
        grid.style.gridTemplateColumns = `repeat(${layout.length > 16 ? 5 : 4}, 1fr)`;
        const status = el('div', 'ag-status', 'Moves: 0');
        let open = [], moves = 0, found = 0, busy = false;
        const buttons = layout.map((shape, i) => {
            const b = el('button', 'am-card');
            b.type = 'button';
            b.setAttribute('aria-label', 'face-down card');
            const face = svg('svg', { viewBox: '0 0 40 40', class: 'am-shape' });
            const [tag, attrs] = SHAPES[shape % SHAPES.length];
            svg(tag, attrs, face);
            b.append(face);
            b.addEventListener('click', () => {
                if (busy || b.classList.contains('up') || b.classList.contains('found')) return;
                b.classList.add('up');
                b.setAttribute('aria-label', SHAPE_NAMES[shape % SHAPES.length]);
                open.push(i);
                if (open.length < 2) return;
                moves++;
                const [a, c] = open;
                open = [];
                if (layout[a] === layout[c]) {
                    [a, c].forEach((k) => buttons[k].classList.add('found'));
                    found++;
                } else {
                    busy = true;
                    game.later(800, () => {
                        [a, c].forEach((k) => {
                            buttons[k].classList.remove('up');
                            buttons[k].setAttribute('aria-label', 'face-down card');
                        });
                        busy = false;
                    });
                }
                status.textContent = `Moves: ${moves}`;
                if (found * 2 === layout.length) {
                    status.textContent = `All pairs found in ${moves} moves!`;
                    ask(`I finished the memory game in ${moves} moves.`);
                }
            });
            grid.append(b);
            return b;
        });
        root.append(grid, status);
        body.append(root);
    };

    // ---- Minesweeper -----------------------------------------------------------------------------

    kinds['arcade-mines'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const size = d.size || 9, mineCount = d.mines || 10;
        const root = el('div', 'amn');
        const game = life(root);
        const top = el('div', 'arcade-bar');
        const counter = el('span', 'amn-count');
        const clock = el('span', 'amn-count');
        const flagBtn = el('button', 'pop-action', 'Flag mode: off');
        const newBtn = el('button', 'pop-action', 'New game');
        top.append(counter, clock, flagBtn, newBtn);
        const grid = el('div', 'amn-grid');
        grid.style.gridTemplateColumns = `repeat(${size}, 1fr)`;
        const status = el('div', 'ag-status', 'Click a square to start. Right-click (or flag mode) marks a mine.');
        root.append(top, grid, status);
        body.append(root);

        let mines, shown, flags, cells, started, over, finalSecs = 0, flagMode = false;
        const near = (i) => {
            const r = Math.floor(i / size), c = i % size, out = [];
            for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) {
                const y = r + dr, x = c + dc;
                if ((dr || dc) && y >= 0 && y < size && x >= 0 && x < size) out.push(y * size + x);
            }
            return out;
        };
        const count = (i) => near(i).filter((k) => mines.has(k)).length;
        const paint = () => {
            counter.textContent = `Mines: ${mineCount - flags.size}`;
            cells.forEach((b, i) => {
                const open = shown.has(i);
                b.className = `amn-cell${open ? ' open' : ''}${flags.has(i) && !open ? ' flag' : ''}${open && mines.has(i) ? ' mine' : ''}`;
                const n = open && !mines.has(i) ? count(i) : 0;
                b.textContent = open ? (mines.has(i) ? '✹' : n || '') : flags.has(i) ? '⚑' : '';
                if (n) b.dataset.n = n; else delete b.dataset.n;
            });
        };
        const plant = (safe) => {
            const banned = new Set([safe, ...near(safe)]);
            const spots = [...Array(size * size).keys()].filter((i) => !banned.has(i));
            while (mines.size < mineCount && spots.length) mines.add(spots.splice(Math.floor(Math.random() * spots.length), 1)[0]);
            started = Date.now();
        };
        const reveal = (i) => {
            const stack = [i];
            while (stack.length) {
                const k = stack.pop();
                if (shown.has(k) || flags.has(k)) continue;
                shown.add(k);
                if (!mines.has(k) && !count(k)) stack.push(...near(k));
            }
        };
        const finish = (won) => {
            over = true;
            const secs = finalSecs = Math.round((Date.now() - started) / 1000);
            if (!won) mines.forEach((k) => shown.add(k));
            status.textContent = won ? `Cleared in ${secs} seconds!` : 'Boom. That was a mine.';
            ask(won ? `I won minesweeper in ${secs} seconds.` : 'I lost at minesweeper.');
        };
        const press = (i, flag) => {
            if (over) return;
            if (flag) {
                if (!shown.has(i)) flags.has(i) ? flags.delete(i) : flags.add(i);
            } else if (!flags.has(i)) {
                if (!started) plant(i);
                if (mines.has(i)) finish(false);
                else {
                    reveal(i);
                    if (shown.size === size * size - mineCount) finish(true);
                }
            }
            paint();
        };
        const reset = () => {
            mines = new Set(); shown = new Set(); flags = new Set(); started = 0; over = false;
            status.textContent = 'Click a square to start. Right-click (or flag mode) marks a mine.';
            paint();
        };
        cells = [...Array(size * size).keys()].map((i) => {
            const b = el('button', 'amn-cell');
            b.type = 'button';
            b.setAttribute('aria-label', `row ${Math.floor(i / size) + 1} column ${i % size + 1}`);
            b.addEventListener('click', () => press(i, flagMode));
            b.addEventListener('contextmenu', (e) => { e.preventDefault(); press(i, true); });
            grid.append(b);
            return b;
        });
        flagBtn.addEventListener('click', () => { flagMode = !flagMode; flagBtn.textContent = `Flag mode: ${flagMode ? 'on' : 'off'}`; });
        newBtn.addEventListener('click', reset);
        game.every(500, () => {
            clock.textContent = `Time: ${!started ? 0 : over ? finalSecs : Math.round((Date.now() - started) / 1000)}`;
        });
        reset();
    };

    // ---- Snake -----------------------------------------------------------------------------------

    kinds['arcade-snake'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const N = d.size || 18, baseSpeed = d.speed || 130, CELL = 20;
        const root = el('div', 'asn');
        const game = life(root);
        const canvas = el('canvas', 'asn-canvas');
        canvas.width = canvas.height = N * CELL;
        canvas.setAttribute('aria-label', 'Snake board');
        const status = el('div', 'ag-status', 'Press an arrow key to start. Space pauses.');
        const bar = el('div', 'arcade-bar');
        const scoreEl = el('span', 'amn-count', 'Score: 0');
        const again = el('button', 'pop-action', 'New game');
        bar.append(scoreEl, again);
        root.append(bar, canvas, status);
        body.append(root);
        const ctx = canvas.getContext('2d');
        const OPPOSITE = { up: 'down', down: 'up', left: 'right', right: 'left' };
        const STEP = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
        let snake, dir, queue, food, score, running, over, last;

        const placeFood = () => {
            const taken = new Set(snake.map(([x, y]) => y * N + x));
            const free = [...Array(N * N).keys()].filter((i) => !taken.has(i));
            const i = free[Math.floor(Math.random() * free.length)];
            food = [i % N, Math.floor(i / N)];
        };
        const draw = () => {
            ctx.fillStyle = css(root, '--hud-bg', '#000');
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = css(root, '--hud-faint', '#1f2b3d');
            ctx.strokeRect(0.5, 0.5, canvas.width - 1, canvas.height - 1);
            ctx.fillStyle = css(root, '--hud-warn', '#ffc24a');
            ctx.beginPath();
            ctx.arc(food[0] * CELL + CELL / 2, food[1] * CELL + CELL / 2, CELL / 2 - 3, 0, Math.PI * 2);
            ctx.fill();
            snake.forEach(([x, y], k) => {
                ctx.fillStyle = k ? css(root, '--hud', '#3fa9ff') : css(root, '--hud-bright', '#9fd8ff');
                ctx.fillRect(x * CELL + 1, y * CELL + 1, CELL - 2, CELL - 2);
            });
        };
        const reset = () => {
            const m = Math.floor(N / 2);
            snake = [[m, m], [m - 1, m], [m - 2, m]];
            dir = 'right'; queue = []; score = 0; running = false; over = false; last = 0;
            placeFood();
            scoreEl.textContent = 'Score: 0';
            status.textContent = 'Press an arrow key to start. Space pauses.';
            draw();
        };
        const pause = (why) => {
            if (!running) return;
            running = false;
            status.textContent = `Paused${why ? ` (${why})` : ''}. Press an arrow key or space to carry on.`;
        };
        const step = () => {
            if (queue.length) dir = queue.shift();
            const [dx, dy] = STEP[dir];
            const head = [snake[0][0] + dx, snake[0][1] + dy];
            const eats = head[0] === food[0] && head[1] === food[1];
            const body_ = eats ? snake : snake.slice(0, -1);
            if (head[0] < 0 || head[1] < 0 || head[0] >= N || head[1] >= N || body_.some(([x, y]) => x === head[0] && y === head[1])) {
                running = false; over = true;
                status.textContent = `Game over. You scored ${score}.`;
                ask(`I scored ${score} at snake.`);
                return;
            }
            snake = [head, ...body_];
            if (eats) {
                score++;
                scoreEl.textContent = `Score: ${score}`;
                if (snake.length === N * N) { running = false; over = true; ask(`I scored ${score} at snake.`); return; }
                placeFood();
            }
        };
        keys(game, root, (key) => {
            if (over) return false;
            if (key === 'space') { running ? pause() : (running = true, status.textContent = 'Go!'); return true; }
            const tail = queue.length ? queue[queue.length - 1] : dir;
            if (key !== tail && key !== OPPOSITE[tail] && queue.length < 3) queue.push(key);
            if (!running) { running = true; status.textContent = 'Go!'; }
            return true;
        });
        game.on(window, 'blur', () => pause('window lost focus'));
        game.on(document, 'visibilitychange', () => { if (document.hidden) pause('window hidden'); });
        game.every(30, () => {
            if (!running) return;
            if (!onTop(root)) { pause('another window is on top'); return; }
            const now = performance.now();
            if (now - last < Math.max(55, baseSpeed - score * 2)) return;
            last = now;
            step();
            draw();
        });
        again.addEventListener('click', reset);
        reset();
    };

    // ---- 2048 ------------------------------------------------------------------------------------

    kinds['arcade-2048'] = (card, body, { el, ask }) => {
        const N = (card.data || {}).size || 4;
        const root = el('div', 'a2');
        const game = life(root);
        const bar = el('div', 'arcade-bar');
        const scoreEl = el('span', 'amn-count');
        const again = el('button', 'pop-action', 'New game');
        bar.append(scoreEl, again);
        const grid = el('div', 'a2-grid');
        grid.style.gridTemplateColumns = `repeat(${N}, 1fr)`;
        const tiles = [...Array(N * N)].map(() => grid.appendChild(el('div', 'a2-tile')));
        const status = el('div', 'ag-status', 'Slide with the arrow keys. Join matching tiles to reach 2048.');
        root.append(bar, grid, status);
        body.append(root);
        let board, score, over, reached;

        const add = () => {
            const free = board.map((v, i) => (v ? -1 : i)).filter((i) => i >= 0);
            if (free.length) board[free[Math.floor(Math.random() * free.length)]] = Math.random() < 0.9 ? 2 : 4;
        };
        const paint = () => {
            scoreEl.textContent = `Score: ${score}`;
            tiles.forEach((t, i) => {
                const v = board[i];
                t.textContent = v || '';
                t.dataset.v = v ? String(Math.min(v, 4096)) : '';
                t.setAttribute('aria-label', v ? String(v) : 'empty');
            });
        };
        const line = (k, dir) => [...Array(N).keys()].map((j) => ({
            left: k * N + j, right: k * N + (N - 1 - j), up: j * N + k, down: (N - 1 - j) * N + k,
        })[dir]);
        const slide = (dir) => {
            let moved = false;
            for (let k = 0; k < N; k++) {
                const idx = line(k, dir), vals = idx.map((i) => board[i]).filter(Boolean), out = [];
                for (let j = 0; j < vals.length; j++) {
                    if (vals[j] === vals[j + 1]) { out.push(vals[j] * 2); score += vals[j] * 2; j++; } else out.push(vals[j]);
                }
                idx.forEach((i, j) => { const v = out[j] || 0; if (board[i] !== v) moved = true; board[i] = v; });
            }
            return moved;
        };
        const stuck = () => board.every((v, i) => v && (i % N === N - 1 || board[i + 1] !== v) && (i + N >= N * N || board[i + N] !== v));
        const reset = () => {
            board = Array(N * N).fill(0); score = 0; over = false; reached = false;
            add(); add(); paint();
            status.textContent = 'Slide with the arrow keys. Join matching tiles to reach 2048.';
        };
        keys(game, root, (key) => {
            if (over || key === 'space') return false;
            if (!slide(key)) return true;
            add();
            paint();
            if (!reached && board.includes(2048)) {
                reached = true;
                status.textContent = 'You made 2048! Keep going if you like.';
                ask(`I reached 2048 with a score of ${score}.`);
            } else if (stuck()) {
                over = true;
                status.textContent = `No moves left. Final score ${score}.`;
                ask(`I scored ${score} at 2048.`);
            }
            return true;
        });
        again.addEventListener('click', reset);
        reset();
    };

    // ---- Maths sprint ----------------------------------------------------------------------------

    const rand = (lo, hi) => lo + Math.floor(Math.random() * (hi - lo + 1));

    function sum(level) {
        const op = ['+', '-', '×', ...(level === 'hard' ? ['÷'] : [])][rand(0, level === 'hard' ? 3 : 2)];
        const big = level === 'hard';
        if (op === '+') { const a = rand(2, big ? 99 : 20), b = rand(2, big ? 99 : 20); return [`${a} + ${b}`, a + b]; }
        if (op === '-') { const a = rand(5, big ? 120 : 30), b = rand(1, a); return [`${a} − ${b}`, a - b]; }
        if (op === '×') { const a = rand(2, big ? 15 : 10), b = rand(2, 12); return [`${a} × ${b}`, a * b]; }
        const b = rand(2, 12), q = rand(2, 12);
        return [`${b * q} ÷ ${b}`, q];
    }

    kinds['arcade-sprint'] = (card, body, { el, ask }) => {
        const d = card.data || {};
        const seconds = d.seconds || 60, level = d.level || 'easy';
        const root = el('div', 'amx');
        const game = life(root);
        const bar = el('div', 'arcade-bar');
        const clock = el('span', 'amn-count', `Time: ${seconds}`);
        const scoreEl = el('span', 'amn-count', 'Score: 0');
        bar.append(clock, scoreEl);
        const question = el('div', 'amx-q', 'Ready?');
        const form = el('form', 'aw-form');
        const input = el('input', 'aw-input');
        Object.assign(input, { inputMode: 'numeric', autocomplete: 'off', placeholder: 'Answer', disabled: true });
        input.setAttribute('aria-label', 'Your answer');
        const start = el('button', 'pop-action', 'Start');
        start.type = 'button';
        form.append(input, start);
        const status = el('div', 'ag-status', `${seconds} seconds. Type each answer and press Enter.`);
        root.append(bar, question, form, status);
        body.append(root);
        let answer = 0, score = 0, ends = 0, stopClock = null;

        const next = () => { const [q, a] = sum(level); question.textContent = `${q} = ?`; answer = a; input.value = ''; };
        const end = () => {
            if (stopClock) stopClock();
            input.disabled = true;
            start.disabled = false;
            start.textContent = 'Play again';
            question.textContent = `Time! ${score} right.`;
            clock.textContent = 'Time: 0';
            ask(`I scored ${score} in the maths sprint.`);
        };
        start.addEventListener('click', () => {
            score = 0; scoreEl.textContent = 'Score: 0';
            ends = Date.now() + seconds * 1000;
            input.disabled = false; start.disabled = true;
            next();
            input.focus();
            stopClock = game.every(200, () => {
                const left = Math.max(0, Math.ceil((ends - Date.now()) / 1000));
                clock.textContent = `Time: ${left}`;
                if (!left) end();
            });
        });
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (input.disabled || input.value.trim() === '') return;
            if (Number(input.value) === answer) {
                score++;
                scoreEl.textContent = `Score: ${score}`;
                status.textContent = 'Right!';
            } else status.textContent = `It was ${answer}.`;
            next();
        });
    };
})();
