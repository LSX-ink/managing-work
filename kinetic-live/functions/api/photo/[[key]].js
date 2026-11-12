// GET /api/photo/<key> -> a product photo from R2
export async function onRequestGet({ env, params }) {
  const key = (Array.isArray(params.key) ? params.key : [params.key]).join("/");
  if (!env.PHOTOS || !/^products\/\d+\/[\w-]+\.(jpg|png|webp|gif|avif)$/.test(key)) return new Response("Not found", { status: 404 });
  const obj = await env.PHOTOS.get(key);
  if (!obj) return new Response("Not found", { status: 404 });
  const h = new Headers();
  obj.writeHttpMetadata(h);
  h.set("ETag", obj.httpEtag);
  h.set("Cache-Control", "public, max-age=31536000, immutable");
  h.set("X-Content-Type-Options", "nosniff");
  h.set("Content-Security-Policy", "default-src 'none'");
  return new Response(obj.body, { headers: h });
}
