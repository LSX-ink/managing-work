// Shiftnote demo: serves the app and turns a supervisor's notes into a structured site diary.
const MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const PHOTO_MODEL = "@cf/llava-hf/llava-1.5-7b-hf";

const SYSTEM = `You turn a construction site supervisor's spoken end-of-shift notes into a structured daily site diary.
Return ONLY one JSON object, no prose, with exactly these keys:
{
 "weather": {"am": string, "pm": string},
 "labour": [{"trade": string, "count": number}],
 "plant": [{"item": string, "count": number, "status": "Working" | "Standing" | "Broken down"}],
 "works": [{"location": string, "activity": string, "status": "Complete" | "In progress" | "Stopped" | "Started", "pct": number}],
 "delays": [{"start": "HH:MM" or "", "end": "HH:MM" or "", "hours": number, "location": string, "cause": string, "affected": string, "owner": string}],
 "safety": {"toolbox": string, "incidents": [{"type": "Near miss" | "Incident" | "Observation", "text": string}]},
 "visitors": [{"who": string, "time": string, "purpose": string}],
 "actions": [string],
 "earlyWarnings": [{"title": string, "description": string, "time": boolean, "cost": boolean, "quality": boolean, "safety": boolean, "proposed": [string]}]
}
Rules: use only facts stated in the notes; never invent names, numbers or times; use "" or [] when something is not mentioned.
Keep every number the supervisor gives: temperatures (e.g. "Dry, 7°C"), headcounts, quantities with units, depths, percentages, times as HH:MM.
For each delay give start and end times when stated, and hours lost (work it out from the times if needed). Put the people and plant affected in "affected" (e.g. "4 groundworkers + 13 t excavator").
Each action should start with a verb and say what needs doing.
Write in plain British English, past tense, short factual sentences suitable for a contractual record.
Raise an early warning only for matters that could increase cost, delay completion or affect quality or safety.`;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/write") {
      if (request.method !== "POST") return json({ error: "POST only" }, 405);
      let notes = "";
      try {
        const body = await request.json();
        notes = String(body.notes || "").slice(0, 4000).trim();
      } catch (e) {
        return json({ error: "bad request" }, 400);
      }
      if (notes.length < 20) return json({ error: "notes too short" }, 400);
      if (!env.AI) return json({ error: "ai unavailable" }, 503);
      try {
        const out = await env.AI.run(MODEL, {
          messages: [
            { role: "system", content: SYSTEM },
            { role: "user", content: "Supervisor's notes:\n" + notes },
          ],
          max_tokens: 2000,
          temperature: 0.1,
        });
        let text = out && (out.response ?? out.result?.response);
        if (typeof text === "object" && text !== null) return json({ diary: text });
        text = String(text || "");
        const a = text.indexOf("{"), b = text.lastIndexOf("}");
        if (a < 0 || b <= a) return json({ error: "no json" }, 502);
        const diary = JSON.parse(text.slice(a, b + 1));
        return json({ diary });
      } catch (e) {
        return json({ error: "ai failed" }, 502);
      }
    }
    if (url.pathname === "/api/photo") {
      if (request.method !== "POST") return json({ error: "POST only" }, 405);
      if (!env.AI) return json({ error: "ai unavailable" }, 503);
      try {
        const body = await request.json();
        const b64 = String(body.image || "");
        if (!b64 || b64.length > 1500000) return json({ error: "bad image" }, 400);
        const bin = atob(b64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        const out = await env.AI.run(PHOTO_MODEL, {
          image: [...bytes],
          prompt: "This photo was taken at a construction site gate as something arrived or left. Say what the main item is in under 12 words, like a site log entry, e.g. '13 t tracked excavator on a low loader' or 'Concrete mixer truck'. Ignore the text banner at the bottom.",
          max_tokens: 40,
        });
        let d = String((out && (out.description || out.response)) || "").trim().replace(/^["']|["']$/g, "");
        d = d.split(/\n/)[0].replace(/\.$/, "");
        if (!d) return json({ error: "empty" }, 502);
        return json({ description: d.charAt(0).toUpperCase() + d.slice(1) });
      } catch (e) {
        return json({ error: "ai failed" }, 502);
      }
    }
    return env.ASSETS.fetch(request);
  },
};
