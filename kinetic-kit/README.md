# Kinetic kit: the "Owner's log in" area for client websites

A reusable owner area for sites hosted on **Cloudflare Pages**: Pages Functions + a **D1** database
(+ **R2** for product photos). The owner logs in from the site's side menu and gets these tabs:

| Tab | Shown when | What it does |
|---|---|---|
| Products & stock | `SHOP = "1"` | Lists, add/remove products, photo upload (R2), price, in/out of stock switch, show/hide, per-size stock with custom size names |
| Text | `TEXT = "1"` | Edits the text fields Kinetic set up for the site (`texts` table → `data-kit-text`) |
| Analytics | always | Visitors (last 24 h), page views, top pages, referrers, phone/computer, site events (sign-ups, quote requests…), revenue and refunds, by minute/hour/day/week/month/year |
| Transactions | always | Payments and refunds from the Stripe webhook; an empty "not connected" state until then |
| Monthly statements | always | Preview of last month's real statement, stop/start the emails |
| Account | always | Change password, statement emails on/off |

Nothing is ever made up: with no data every tab says so.

## Files

```
kinetic-kit/
  functions/                 Pages Functions (copy into the site folder)
    _lib/                    shared helpers (not routes)
    api/config.js            GET  site config for the owner page
    api/track.js             POST page view (path, referrer host; no cookies, no IP stored)
    api/event.js             POST site event (only names listed in EVENTS)
    api/public/catalog.js    GET  visible products + text for kit.js
    api/photo/[[key]].js     GET  product photo from R2
    api/auth/{login,logout,me,password}.js
    api/owner/...            everything behind the login (middleware checks session + forced change)
    api/stripe/webhook.js    POST Stripe events (signature checked with STRIPE_WEBHOOK_SECRET)
    api/statements/stop.js   GET confirm page / POST stop (one-click unsubscribe link)
  owner.html owner.js owner.css   the owner area (served at /owner)
  kit.js                     site-side snippet
  _headers                   security headers for /owner
  schema.sql                 D1 schema (safe to re-run)
  wrangler.toml              Pages config template (D1 + R2 bindings, site flags)
  tools/owner-password.mjs   create an owner / reset a password (temporary password + hash-only SQL)
  statements-worker/         cron Worker: monthly statement emails + inbound "STOP" replies
  test/run-tests.mjs         end-to-end tests (wrangler pages dev + Playwright)
```

## Security in short

- Passwords: PBKDF2-SHA256, 100,000 iterations (the most Cloudflare's WebCrypto allows), 16-byte random salt per user. Only the hash is stored.
- Sessions: 32-byte random token in a `HttpOnly; Secure; SameSite=Strict; Path=/api` cookie, 14 days. D1 stores only the SHA-256 of the token. Password change logs out every other session.
- Lockout: 5 wrong passwords in a row lock that login for 15 minutes. Unknown emails get the same answer (and take the same time) as wrong passwords.
- State-changing requests must come from the same origin (Origin / Sec-Fetch-Site check).
- Until the temporary password is replaced, every `/api/owner/*` call is refused.
- Kinetic can **reset** a password but never read one: resets go through `tools/owner-password.mjs` and `wrangler d1 execute`. There is no admin web page.
- Photos: JPG/PNG/WebP/GIF/AVIF only, checked by content type **and** the file's first bytes, 5 MB max, random R2 keys. SVG is refused. Served with `Content-Security-Policy: default-src 'none'`.
- Analytics: no cookies, nothing stored in the browser. A visitor id is `sha256(daily random salt + IP + user agent + host)`; the IP isn't stored and salts are deleted after two days.

## Setting up a new client site

Run these in the client site's folder (the one with `index.html`). The commands are the same in PowerShell and bash.

1. Copy the kit in:
   ```
   copy kit files: functions\  owner.html  owner.js  owner.css  kit.js  _headers  wrangler.toml
   ```
   Edit `wrangler.toml`: `name` (= the Pages project), `SITE_NAME`, `SITE_URL`, `SHOP`, `TEXT`, `EVENTS`, the D1/R2 names.
   Sites without a shop: delete the `[[r2_buckets]]` block (R2 must be turned on in the Cloudflare account before you can make a bucket).
2. Add to every page, before `</body>`:
   ```html
   <script src="/kit.js" defer></script>
   ```
   Put an "Owner's log in" link in the site's side menu: `<a href="/owner">Owner's log in</a>`.
   Shop sites: `<div data-kit-products></div>` where products go (or `data-kit-products="New in"` for one list), and `data-kit-text="hero"` on any text the owner may edit.
   Forms you want counted: `<form data-kit-event="quote">`, or call `KineticKit.event("quote")` after a successful send. List the names in `EVENTS`, e.g. `EVENTS = "quote:Quote requests"`.
3. Create the database (and bucket), put the id into `wrangler.toml`, load the schema:
   ```powershell
   npx wrangler d1 create client-db
   $id = (npx wrangler d1 list --json | ConvertFrom-Json | Where-Object name -eq 'client-db').uuid
   (Get-Content wrangler.toml) -replace 'REPLACE_WITH_D1_DATABASE_ID', $id | Set-Content wrangler.toml
   npx wrangler d1 execute client-db --remote --file path\to\kinetic-kit\schema.sql
   npx wrangler r2 bucket create client-photos        # shop sites only
   ```
4. Text fields (only if `TEXT = "1"`), one row per editable bit of text:
   ```
   npx wrangler d1 execute client-db --remote --command "INSERT INTO texts (key,label,value,multiline,sort) VALUES ('hero','Big heading','Made for the cold',0,1)"
   ```
5. The owner's first login:
   ```
   node path\to\kinetic-kit\tools\owner-password.mjs owner@business.co.uk --db client-db   (prints a private username + temporary password)
   ```
   It prints a temporary password **once** (send it to the owner) and the exact `wrangler d1 execute … --file …` command to run. Delete the .sql file afterwards (it only holds the hash).
   **Password reset** is the same command again: new temporary password, forced change at next login, failed-login counter and lock cleared, all sessions ended.
6. Deploy: `npx wrangler pages deploy . --project-name <project> --branch main`. The owner area is at `https://<site>/owner`.

`wrangler.toml` is uploaded with the site (Pages does that), so it must never contain secrets. It holds only names and the D1 id, which are useless without an API token.

## Card payments ("connect bank account")

The owner's bank is connected inside their own Stripe account; Stripe pays out to it. The kit only needs Stripe to tell it about payments:

1. In the owner's Stripe dashboard: Developers → Webhooks → Add endpoint
   `https://<site>/api/stripe/webhook`, events: `charge.succeeded`, `charge.pending`, `charge.failed`, `charge.refunded`, `charge.refund.updated`, `refund.created`, `refund.updated`, `refund.failed`.
2. Copy the endpoint's signing secret (`whsec_…`) into a Pages secret, then redeploy so it takes effect:
   ```
   npx wrangler pages secret put STRIPE_WEBHOOK_SECRET --project-name <project>
   npx wrangler pages deploy . --project-name <project> --branch main
   ```
   No Stripe secret key (`sk_…`) is needed or stored.

Signatures are checked (HMAC-SHA256 of `t.body`, 5-minute tolerance); events are upserted by Stripe id so retries never double count. Test-mode payments are marked "Test" in the list. Amounts are in pence; analytics and statements count the `CURRENCY` set in wrangler.toml.

## Monthly statements (statements-worker/)

A small Worker per client site, using the **same D1 database**:

- **Cron** `0 7 1 * *`: emails every owner who hasn't opted out last month's real payments and refunds (UTC month). Sites with no payments recorded yet are skipped; a sent month is logged in `statements_sent`, so a retried cron never sends twice. The email ends with **"Reply STOP to stop these emails"** and has `List-Unsubscribe` (one-click link to `/api/statements/stop?token=…` + mailto).
- **Email handler**: replies to `STATEMENT_REPLY_TO` arrive here via Cloudflare Email Routing. If the reply's own text (quoted original ignored) or subject starts with STOP/UNSUBSCRIBE, the sender's login gets `opted_out = 1`. Other replies are forwarded to `FORWARD_TO` if set.
- Sender is pluggable (`src/sender.js`); Resend is built in via `RESEND_API_KEY`.

Setup:
1. Resend: add and verify the sending domain (DNS records Resend gives you), create an API key.
2. In `statements-worker/wrangler.toml`: `name`, D1 name + id, `SITE_NAME`, `SITE_URL`, `STATEMENT_FROM`, `STATEMENT_REPLY_TO`, `FORWARD_TO`.
3. `npx wrangler secret put RESEND_API_KEY` then `npx wrangler deploy` (in `statements-worker/`).
4. Cloudflare dashboard → the domain → Email → Email Routing: enable it (this sets the domain's MX records, so only do it if the domain doesn't already receive mail elsewhere; otherwise use a subdomain), then Routing rules → custom address `statements@…` → action **Send to a Worker** → this Worker.

The owner can also stop/start statements in the owner area (Account or Monthly statements tab).

## Kinetic's own site (kinetic-live/)

`kinetic-live/` already has `functions/`, `owner.html/js/css`, `kit.js`, `_headers` and a `wrangler.toml` (`SHOP=0`, `TEXT=0`, `EVENTS = "signup:Sign-ups,quote:Quote requests"`, no R2). `index.html` got two small hooks:
- an "Owner's log in" link at the bottom of the side menu (`.menu-foot`), and
- `<script src="/kit.js" defer></script>` before `</body>`.

kit.js counts sign-ups and briefs by watching for success, so the built page's code is untouched: the sign-up pop-up `#gate` only closes after a valid sign-up, and `#v-done` only fills after a valid brief. **When index.html is rebuilt from premium/**, add the same two hooks to the source:
```html
<!-- inside <div class="menu-foot"> -->
<a class="owner-login" href="/owner">Owner's log in</a>
<!-- before </body> -->
<script src="/kit.js" defer></script>
```
(Optionally, instead of the watchers, call `window.KineticKit && KineticKit.event("signup")` after `store.set("member", member)` and `KineticKit.event("quote")` after the brief is accepted.)

When you change the kit, copy it over again: `functions\`, `owner.*`, `kit.js`, `_headers` from `kinetic-kit\` to `kinetic-live\`.

## Testing locally

```
cd kinetic-kit
npm i -D wrangler            # or set WRANGLER to an installed wrangler
node test/run-tests.mjs      # needs Playwright + Chromium (see PLAYWRIGHT / CHROME env vars)
```
It builds a throw-away site in the temp folder, runs `wrangler pages dev` (local D1 + R2 via miniflare) and `wrangler dev` for the statements Worker with a fake Resend endpoint, then checks: first login + forced password change, lockout, products/stock/sizes/hide/remove in the public API, photo upload (and refusals), page view + event tracking in analytics for every range, signed (and badly signed) Stripe webhooks into Transactions/Analytics, statement cron + email, STOP via the toggle, the link and an emailed reply, and Kinetic's live page with the kit.

Note: `wrangler pages dev` (4.x) doesn't pick up `[vars]`/D1/R2 from wrangler.toml locally, so the test passes them as flags: `--d1 DB=<id> --r2 PHOTOS -b SHOP=1 …`. Deploys do use wrangler.toml.
