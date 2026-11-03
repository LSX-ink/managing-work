// POST /api/owner/products/:id/photo  (body: the image file itself, Content-Type image/...)
// Stored in R2. Pictures only (checked by content type AND the file's first bytes), 5 MB max.
import { handle, json, err, siteConfig, b64url, randomBytes } from "../../../../_lib/util.js";
import { ownerProduct } from "../../../../_lib/catalog.js";

const MAX_BYTES = 5 * 1024 * 1024;
const TYPES = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "image/avif": "avif" };

function sniff(b) {
  const h = (...xs) => xs.every((x, i) => b[i] === x);
  if (h(0xff, 0xd8, 0xff)) return "image/jpeg";
  if (h(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a)) return "image/png";
  if (h(0x47, 0x49, 0x46, 0x38)) return "image/gif";
  if (h(0x52, 0x49, 0x46, 0x46) && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50) return "image/webp";
  if (String.fromCharCode(...b.slice(4, 12)).match(/^ftyp(avif|avis)/)) return "image/avif";
  return null;
}

export const onRequestPost = handle(async ({ request, env, params }) => {
  if (!siteConfig(env).shop) return err("This website has no shop", 404);
  if (!env.PHOTOS) return err("Photo storage isn't set up for this website yet", 503);
  const p = await env.DB.prepare("SELECT * FROM products WHERE id = ?").bind(+params.id || 0).first();
  if (!p) return err("Product not found", 404);
  const type = (request.headers.get("Content-Type") || "").split(";")[0].trim().toLowerCase();
  if (!TYPES[type]) return err("That file isn't a picture. Choose a JPG, PNG or WebP.", 415);
  if (+(request.headers.get("Content-Length") || 0) > MAX_BYTES) return err("That picture is too big. The limit is 5 MB.", 413);
  const buf = new Uint8Array(await request.arrayBuffer());
  if (buf.length > MAX_BYTES) return err("That picture is too big. The limit is 5 MB.", 413);
  if (buf.length < 12 || sniff(buf) !== type) return err("That file isn't a picture. Choose a JPG, PNG or WebP.", 415);
  const key = `products/${p.id}/${b64url(randomBytes(9))}.${TYPES[type]}`;
  await env.PHOTOS.put(key, buf, { httpMetadata: { contentType: type, cacheControl: "public, max-age=31536000, immutable" } });
  await env.DB.prepare("UPDATE products SET img_key = ?, updated_at = ? WHERE id = ?").bind(key, Date.now(), p.id).run();
  if (p.img_key) await env.PHOTOS.delete(p.img_key);
  return json({ product: ownerProduct(await env.DB.prepare("SELECT * FROM products WHERE id = ?").bind(p.id).first()) });
});
