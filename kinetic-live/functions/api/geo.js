// GET /api/geo -> {"country":"GB"}  The visitor's country from Cloudflare, so the page can show prices in
// pounds, dollars or euros. Nothing is stored.
export const onRequestGet = ({ request }) =>
  new Response(JSON.stringify({ country: (request.cf && request.cf.country) || "" }), {
    headers: { "Content-Type": "application/json", "Cache-Control": "private, no-store" }
  });
