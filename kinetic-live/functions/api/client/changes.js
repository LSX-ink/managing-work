// GET  /api/client/changes  -> this client's change requests, newest first
// POST /api/client/changes  (multipart form: website, kind, details, links, files[])  -> a new change request.
//   Screenshots, photos and PDFs go to the owner as email attachments (owner, 16 Nov 2026: "allow them to add images
//   ... pdfs as well"); only their names are kept here. A JSON body (no files) is still accepted.
// (owner, 16 Nov 2026: "once signed in there's change requests")
import { handle, json, err, readJson, sameOrigin } from "../../_lib/util.js";
import { sendMail, escHtml } from "../../_lib/mail.js";
import { getClient } from "../../_lib/client.js";

const KINDS = ["Wording", "Pictures", "Design", "New page", "Other", "Cancel subscription"];
const PER_DAY = 10;
const MAX_FILES = 6;
const MAX_FILE = 8 * 1024 * 1024;     // 8 MB each
const MAX_TOTAL = 20 * 1024 * 1024;   // 20 MB together (email attachments, once encoded, must stay under 40 MB)
const TYPES = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "image/heic": "heic",
  "image/heif": "heif", "application/pdf": "pdf" };

function toBase64(buf) {
  const bytes = new Uint8Array(buf); let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}
const cleanName = (n, ext) => {
  const base = String(n || "file").replace(/[^\w.\- ]+/g, "_").replace(/\s+/g, " ").trim().slice(0, 80) || "file";
  return /\.[a-z0-9]{2,5}$/i.test(base) ? base : base + "." + ext;
};

export const onRequestGet = handle(async ({ request, env }) => {
  const c = await getClient(env, request);
  if (!c) return err("Please sign in first.", 401);
  const r = await env.DB.prepare(
    "SELECT id, website, kind, details, links, files, status, created_at, updated_at FROM change_requests WHERE client_id = ? ORDER BY created_at DESC LIMIT 50")
    .bind(c.id).all();
  return json({ requests: r.results || [] }, 200, { "Cache-Control": "no-store" });
});

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const c = await getClient(env, request);
  if (!c) return err("Please sign in first.", 401);

  let f = {}, uploads = [];
  if ((request.headers.get("Content-Type") || "").includes("multipart/form-data")) {
    if (Number(request.headers.get("Content-Length") || 0) > MAX_TOTAL + 64 * 1024) {
      return err("Those files are too big together. Keep them under 20 MB in total, or email the rest to us.", 413);
    }
    const form = await request.formData();
    for (const k of ["website", "kind", "details", "links"]) f[k] = form.get(k);
    uploads = form.getAll("files").filter(x => x && typeof x === "object" && x.size > 0);
  } else {
    f = await readJson(request, 16 * 1024);
  }
  const website = String(f.website || "").trim().slice(0, 300);
  const kind = KINDS.includes(f.kind) ? f.kind : "Other";
  const details = String(f.details || "").trim().slice(0, 4000);
  const links = String(f.links || "").trim().slice(0, 1500);
  if (details.length < 5) return err("Tell us what you'd like changed, and where on your website.");

  if (uploads.length > MAX_FILES) return err(`You can attach up to ${MAX_FILES} files at once. Send the rest in another request.`);
  let total = 0; const attachments = [], names = [];
  for (const file of uploads) {
    const ext = TYPES[file.type];
    if (!ext) return err(`"${String(file.name).slice(0, 60)}" isn't a picture or PDF. Attach screenshots, photos (JPG, PNG, HEIC) or PDFs.`);
    if (file.size > MAX_FILE) return err(`"${String(file.name).slice(0, 60)}" is over 8 MB. Make it smaller, or email it to us.`);
    total += file.size;
    if (total > MAX_TOTAL) return err("Those files are too big together. Keep them under 20 MB in total, or email the rest to us.", 413);
    const name = cleanName(file.name, ext);
    names.push(name);
    attachments.push({ filename: name, content: toBase64(await file.arrayBuffer()) });
  }

  const now = Date.now();
  const today = await env.DB.prepare("SELECT COUNT(*) AS n FROM change_requests WHERE client_id = ? AND created_at > ?")
    .bind(c.id, now - 864e5).first();
  if ((today?.n || 0) >= PER_DAY) return err("That's a lot of requests for one day. Put the rest in one message, or email us.", 429);

  const res = await env.DB.prepare(
    "INSERT INTO change_requests (client_id, email, website, kind, details, links, files, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'received', ?, ?)")
    .bind(c.id, c.email, website, kind, details, links, names.join(", "), now, now).run();
  const id = res.meta && res.meta.last_row_id;
  let mailed = true;
  if (env.NOTIFY_TO) {
    const cancel = kind === "Cancel subscription";
    mailed = await sendMail(env, {
      to: env.NOTIFY_TO, replyTo: c.email, attachments,
      subject: cancel ? `CANCEL request #${id}: ${website || c.email} wants to cancel their plan`
        : `Change request #${id}: ${kind} for ${website || c.email}`,
      text: `${cancel ? "Cancellation" : "Change"} request #${id}\n\nFrom: ${c.email}\nWebsite: ${website || "(not given)"}\nType: ${kind}\n\n${details}\n\n${links ? "Links: " + links + "\n" : ""}${names.length ? "Attached: " + names.join(", ") + "\n" : ""}`,
      html: `<p><b>${cancel ? "Cancellation" : "Change"} request #${id}</b></p><p>From: ${escHtml(c.email)}<br>Website: ${escHtml(website || "(not given)")}<br>Type: ${escHtml(kind)}</p>
<p style="white-space:pre-wrap">${escHtml(details)}</p>${links ? `<p>Links: ${escHtml(links)}</p>` : ""}${names.length ? `<p>Attached: ${escHtml(names.join(", "))}</p>` : ""}
${cancel ? "<p><b>Cancel their subscription in Stripe (Customers, then the subscription, then Cancel) and reply to confirm.</b></p>" : "<p>Reply to this email to answer the client.</p>"}`
    });
  }
  if (!mailed && attachments.length) {
    // the request is saved, but the files didn't reach the owner: say so, so the client can email them
    return json({ ok: true, id, filesNotSent: true });
  }
  return json({ ok: true, id });
});
