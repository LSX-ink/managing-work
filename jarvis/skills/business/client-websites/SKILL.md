---
name: client-websites
description: "Build creative Kinetic Web Designs client sites and mock-ups that make the owner want to buy: 21st.dev components through the MCP bridge, sales-focused page structure, and a quality check before showing it."
risk: none
source: kinetic-web-designs
date_added: "2026-10-12"
---

# Creative client websites that sell

Use this when you make a concept home page (web_design_sales mockup) or a full site for a Kinetic Web Designs client.
The goal is a page the business owner looks at and thinks "I want that", and that their customers act on.

## 1. Get creative parts from 21st.dev

21st.dev is a library of polished website components (heroes, feature grids, testimonials, pricing, call-to-action
banners, animated buttons, logo clouds). The user added its Magic MCP to the Claude app, so use it through mcp_bridge:

1. `mcp_bridge` action `servers`: find the 21st.dev server (often named `@21st-dev/magic` or `magic`). If it isn't
   listed, tell the user it isn't in the Claude app yet and carry on with the built-in mock-up.
2. `mcp_bridge` action `tools` on it, then `call` its inspiration or builder tool with a short brief, for example:
   "hero section for a family bakery in Stockport, warm, big photo area, two buttons". Ask for 2 or 3 parts at most:
   a hero, one proof section (reviews or "why choose us") and a closing call to action.
3. `logo_search` (if the server has it) only finds logos of well-known brands. Never use another company's logo for
   a client.

21st.dev returns React and Tailwind code. The mock-up page is plain HTML, so convert each part:
- Turn JSX into HTML (`className` to `class`, `{...}` expressions to real text, remove imports and `export`).
- Replace Tailwind classes with a few lines of plain CSS, using the page's variables: `var(--bg)`, `var(--ink)`,
  `var(--brand)`, `var(--accent)`, `var(--head)`, `var(--body)`. That keeps the client's colours and fonts.
- No scripts. Animations must be CSS only (`transition`, `@keyframes`) and respect `prefers-reduced-motion`.
- Pass the results to web_design_sales `mockup` as `sections` (HTML) and `section_css` (CSS). Alfred strips any
  script, iframe or event handler, so anything that relies on JavaScript will not work.

## 2. Structure that makes people buy

Every page, in this order:
1. **Hero:** what they do, for whom, where, in under 10 words. One main button (call, book, order) and one softer one.
2. **Proof straight away:** star rating, years in business, "trusted by 300 locals", or a short review. Only real facts;
   use clear placeholders like "[your Google rating]" when you don't know them.
3. **What you get:** 3 to 6 services as cards, each with the benefit to the customer, not just the name.
4. **Why choose us:** 3 short reasons that competitors can't copy (local, family-run, same-day, fixed prices).
5. **Reviews:** 2 or 3, with first name and area. Placeholders until the client sends real ones.
6. **Clear next step:** big button, phone number you can tap, opening hours, map or address.

## 3. Make it feel premium

- One strong idea per page: a bold headline font, a confident colour, or one striking image area. Not all three.
- Plenty of space. Big headline, short lines (under 70 characters), 16px or larger body text.
- A small, tasteful motion: buttons lift on hover, sections fade in. Nothing that spins or flashes.
- Show it on a phone first: most of their customers will see it there. Buttons at least 44px tall.
- Use the client's own words and town. Generic copy ("quality service") is what makes owners shrug.

## 4. Check before showing the owner

- Read it on a phone-width screen and a laptop-width screen.
- Text contrast is readable (dark on light or light on dark, never grey on grey).
- Every button goes somewhere real: `tel:`, `#contact`, or the booking link.
- No made-up reviews, ratings, awards or prices presented as real. Placeholders are fine and clearly marked.
- The footer says it's a concept by Kinetic Web Designs and not the live site.

Then offer: "Write outreach" with the mock-up, or "Quote them".
