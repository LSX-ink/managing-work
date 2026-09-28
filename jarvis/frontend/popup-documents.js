// Pop-up kinds for documents and spreadsheets (docs_tools_sheets.py).
// documents-summary: {data: {columns, rows, chart}} draws a bar chart with the totals table under it.
(() => {
    window.jarvisPopupKinds = window.jarvisPopupKinds || {};
    window.jarvisPopupKinds['documents-summary'] = (card, body, { el, table, chart }) => {
        const data = card.data || {};
        const wrap = el('div', 'pop-docsum');
        if (data.chart && (data.chart.values || []).length) wrap.append(chart(data.chart));
        wrap.append(table((data.columns || []).map(String), (data.rows || []).map((r) => r.map(String))));
        body.append(wrap);
    };
})();
