// Product helpers shared by the owner and public endpoints. Not a route.
import { HttpError } from "./util.js";

export const photoUrl = key => key ? "/api/photo/" + key.split("/").map(encodeURIComponent).join("/") : null;

export function parseSizes(raw) {
  let s; try { s = JSON.parse(raw || "[]"); } catch { s = []; }
  return Array.isArray(s) ? s : [];
}
export function cleanSizes(input) {
  if (!Array.isArray(input)) throw new HttpError("sizes must be a list");
  return input.slice(0, 40).map((z, i) => ({
    id: String(z && z.id || "z" + Date.now().toString(36) + i).replace(/[^\w-]/g, "").slice(0, 24) || "z" + i,
    label: String(z && z.label || "").trim().slice(0, 40),
    qty: Math.max(0, Math.min(1e6, Math.floor(Number(z && z.qty) || 0))),
    show: z && z.show !== false
  }));
}
export function isOut(p, sizes) {
  return !p.in_stock || (sizes.length > 0 && sizes.reduce((a, z) => a + z.qty, 0) === 0);
}
export function ownerProduct(p) {
  const sizes = parseSizes(p.sizes);
  return { id: p.id, listId: p.list_id, name: p.name, price: p.price_pence, img: photoUrl(p.img_key),
    inStock: !!p.in_stock, visible: !!p.visible, sizes, out: isOut(p, sizes), sort: p.sort, updatedAt: p.updated_at };
}
export function publicProduct(p) {
  const sizes = parseSizes(p.sizes);
  return { id: p.id, name: p.name, price: p.price_pence, img: photoUrl(p.img_key), outOfStock: isOut(p, sizes),
    sizes: sizes.filter(z => z.show).map(z => ({ label: z.label, available: z.qty > 0 })) };
}
export async function loadCatalog(DB, { publicOnly = false } = {}) {
  const lists = (await DB.prepare("SELECT id, title, sort FROM lists ORDER BY sort, id").all()).results;
  const prods = (await DB.prepare(`SELECT * FROM products ${publicOnly ? "WHERE visible = 1" : ""} ORDER BY sort, id DESC`).all()).results;
  return lists.map(l => ({ id: l.id, title: l.title,
    items: prods.filter(p => p.list_id === l.id).map(publicOnly ? publicProduct : ownerProduct) }));
}
