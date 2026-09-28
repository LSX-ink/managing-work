# Alfred on your phone

Your iPhone opens the same Alfred that runs on your PC, through a private link that only your own devices can
use (Tailscale). So there is one Alfred: everything you tell him on the phone is saved on the PC (memory
folders, notes, reminders, lists, habits, money, facts), and every update you install on the PC is on the phone
straight away. Your PC has to be on with Alfred running for the phone to reach him.

- **Open Alfred on the phone**: open the private link (below) in Safari and log in with your Alfred password.
- **Make it an app**: in Safari press Share, then **Add to Home Screen**. Alfred gets his own icon and opens
  full screen like an app.
- **Talk to him**: tap the orb, or type in the box. If the microphone doesn't work from the home-screen icon,
  open the link in Safari instead.
- **Everything else**: the same abilities as on the PC. Things that happen on the PC itself (opening folders in
  File Explorer, mouse and keyboard control, media playing on the PC) still happen on the PC.

## Setting up the private link (once)

1. Give Alfred a password: in the jarvis folder's `.env` file, add `JARVIS_PASSWORD=` followed by a password
   you choose. Alfred refuses the phone link without one.
2. Install Tailscale (free) on the PC from tailscale.com/download and sign in.
3. Install the Tailscale app on the iPhone from the App Store and sign in with the same account.
4. On the PC, in PowerShell, run `tailscale serve --bg 8340`. The first time, it may print a link to switch
   on HTTPS for your account: open it, switch it on, and run the command again. It then prints your private
   link, which looks like `https://your-pc-name.something.ts.net`.
5. On the iPhone, with the Tailscale app switched on, open that link in Safari.

The link only works on devices signed in to your Tailscale account, the connection is encrypted, and Alfred
still asks for his password. To switch the link off, run `tailscale serve reset` on the PC.
