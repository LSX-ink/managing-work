// POST /api/client/website  { website }  -> a signed-in client saves (or changes) their own website address
import { handle, json, err, readJson, sameOrigin } from "../../_lib/util.js";
import { getClient, cleanSite } from "../../_lib/client.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const c = await getClient(env, request);
  if (!c) return err("Please sign in first.", 401);
  const body = await readJson(request, 2048);
  const website = cleanSite(body.website);
  if (body.website && !website) return err("That doesn't look like a web address, for example yourbusiness.co.uk.");
  await env.DB.prepare("UPDATE clients SET website = ? WHERE id = ?").bind(website, c.id).run();
  return json({ ok: true, website });
});
