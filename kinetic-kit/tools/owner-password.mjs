#!/usr/bin/env node
// Create an owner login, or reset an owner's password, with a new TEMPORARY password.
// The owner must choose their own password the next time they log in.
//
//   node tools/owner-password.mjs owner@business.co.uk [--username <name>] [--db kinetic-db] [--out <file.sql>]
//
// The email is only where statements go. The login is a private username, made up for you
// unless you pass --username; keep it off the website.
//
// Prints the temporary password ONCE (send it to the owner) and writes a small .sql file that
// holds only the PBKDF2 hash. Apply it with the wrangler command printed at the end, then
// delete the .sql file. Nobody, including Kinetic, can read a password back out of the database.
import { pbkdf2Sync, randomBytes, randomInt } from "node:crypto";
import { writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const ITERATIONS = 100000; // must match functions/_lib/util.js (Cloudflare's WebCrypto maximum)

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args.splice(i, 2)[1] : dflt; };
const db = opt("--db", "kinetic-db");
// Default: the system temp folder, so the file can never be deployed with the site by mistake.
const out = opt("--out", join(tmpdir(), "owner-reset.sql"));
const wantUser = opt("--username", "");
const email = (args[0] || "").trim().toLowerCase();
if (!/^[^\s@'"]+@[^\s@'"]+\.[^\s@'"]+$/.test(email)) {
  console.error("Usage: node tools/owner-password.mjs owner@business.co.uk [--username <name>] [--db <d1 name>] [--out <file.sql>]");
  process.exit(1);
}

// Easy to read out over the phone: no 0/O, 1/l/I.
const ALPHA = "abcdefghjkmnpqrstuvwxyz", DIGITS = "23456789";
const pick = (s, n) => Array.from({ length: n }, () => s[randomInt(s.length)]).join("");
const temp = `${pick(ALPHA, 4)}-${pick(ALPHA, 4)}-${pick(DIGITS, 4)}`;
const temp2 = temp[0].toUpperCase() + temp.slice(1);
const username = (wantUser || `${pick(ALPHA, 5)}${pick(DIGITS, 4)}`).trim().toLowerCase();
if (!/^[a-z0-9._-]{6,40}$/.test(username)) {
  console.error("Usernames are 6-40 letters, numbers, dots, dashes or underscores (not an email).");
  process.exit(1);
}

const salt = randomBytes(16);
const hash = pbkdf2Sync(temp2, salt, ITERATIONS, 32, "sha256");
const stored = `pbkdf2-sha256$${ITERATIONS}$${salt.toString("base64")}$${hash.toString("base64")}`;
const q = s => "'" + s.replace(/'/g, "''") + "'";

const sql = `-- Owner login for ${email}: temporary password (hash only), must be changed at next login.
INSERT INTO users (email, username, pw_hash, must_change, failed, locked_until)
  VALUES (${q(email)}, ${q(username)}, ${q(stored)}, 1, 0, 0)
  ON CONFLICT(email) DO UPDATE SET username = excluded.username, pw_hash = excluded.pw_hash, must_change = 1, failed = 0, locked_until = 0;
DELETE FROM sessions WHERE user_id = (SELECT id FROM users WHERE email = ${q(email)});
`;
writeFileSync(out, sql);

console.log(`
Login for ${email}:

Username:
    ${username}
Temporary password:
    ${temp2}

Send it to the owner (it is not saved anywhere). They will choose their own at first login.

Apply it to the live database:
    npx wrangler d1 execute ${db} --remote --file "${out}"

Then delete ${out}.
`);
