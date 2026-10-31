// Pluggable email sender. Resend is built in (RESEND_API_KEY); add another provider by returning
// an object with the same send() from makeSender().
export function makeSender(env) {
  if (env.RESEND_API_KEY) return resend(env);
  return null;
}

function resend(env) {
  const url = env.RESEND_API_URL || "https://api.resend.com/emails";
  return {
    name: "resend",
    async send({ from, to, replyTo, subject, text, html, headers }) {
      const res = await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
        body: JSON.stringify({ from, to: [to], reply_to: replyTo, subject, text, html, headers })
      });
      if (!res.ok) throw new Error(`Resend ${res.status}: ${(await res.text()).slice(0, 300)}`);
      return res.json();
    }
  };
}
