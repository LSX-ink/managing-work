// GET /api/config -> what this site's owner area should show
import { json, siteConfig } from "../_lib/util.js";

export function onRequestGet({ env }) {
  const c = siteConfig(env);
  return json({ siteName: c.siteName, siteUrl: c.siteUrl, shop: c.shop, text: c.text, events: c.events,
    currency: c.currency, stripe: c.stripe, photos: c.photos });
}
