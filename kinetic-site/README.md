# Kinetic Web Designs website

The public site for Kinetic Web Designs: style gallery (full front-page previews in switchable colours), colour lab,
instant quote and the "your vision" brief. Everything is in `index.html`; no build step.

## Going live

GitHub Pages publishes this folder whenever it changes on `main` (workflow: `.github/workflows/kinetic-site.yml`).
Turn it on once: repository **Settings > Pages > Build and deployment > Source: GitHub Actions**.

## Sign-ups and briefs (Formspree)

1. Make a free account at formspree.io with Alfred's email, alfredw.lsx@gmail.com.
2. Create two forms: "Kinetic sign-ups" and "Kinetic briefs". Each gets an address like `https://formspree.io/f/abcdwxyz`.
3. Put them in `index.html` at the top of the script: `SIGNUP_ENDPOINT` and `BRIEF_ENDPOINT`.

Until those are set, the sign-up still opens the site and the brief shows a copy-and-email fallback to Alfred's address.

The marketing-consent tick box starts unticked (UK PECR): only people who tick it go on the email list.
