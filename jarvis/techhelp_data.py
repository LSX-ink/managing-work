"""Built-in step-by-step tech guides and safety checklists for the tech helper (plain text, nothing online).

Each step is (short title, what to do). Windows 11 and iPhone wording, UK English.
"""

GUIDES = {
    "wifi": ("Wi-Fi not working", [
        ("Check other devices", "See whether your phone gets online on the same Wi-Fi. If it doesn't either, the problem is the router or the broadband, not this PC."),
        ("Toggle Wi-Fi", "Turn Wi-Fi off and on again: Settings, Network and internet, Wi-Fi. Also check Airplane mode is off and the laptop's Wi-Fi key hasn't been pressed."),
        ("Restart the PC", "A restart clears many network glitches. Choose Restart, not Shut down, because Windows keeps some state after a normal shut down."),
        ("Restart the router", "Unplug the router, wait 30 seconds, plug it back in and give it 2 minutes to start up fully."),
        ("Forget and rejoin", "Settings, Network and internet, Wi-Fi, Manage known networks, Forget your network, then join it again with the Wi-Fi password on the router sticker."),
        ("Run the network fixer", "Settings, System, Troubleshoot, Other troubleshooters, Network and Internet, Run. It fixes many small faults on its own."),
        ("Try a cable or call your provider", "Plug the PC into the router with an Ethernet cable. If that works too, it's the Wi-Fi; if not, check your provider's outage page on your phone's mobile data."),
    ]),
    "printer": ("Printer offline", [
        ("Power and paper", "Check the printer is on, has paper and ink or toner, and shows no error light or message."),
        ("Same network", "The printer's screen should show it's connected to the same Wi-Fi as your PC. If not, rejoin it from the printer's menu."),
        ("Restart both", "Turn the printer off, restart the PC, then turn the printer back on and wait for it to be ready."),
        ("Use online mode", "Settings, Bluetooth and devices, Printers and scanners, pick the printer, Open print queue. In the Printer menu, untick Use Printer Offline."),
        ("Clear the queue", "In the print queue, cancel every stuck job. One broken job can block all the others."),
        ("Remove and add again", "Remove the printer in Printers and scanners, then Add device. Windows finds it and reinstalls the driver."),
        ("Try the maker's app", "Install the printer maker's own app from the Microsoft Store, which can repair the connection and update firmware."),
    ]),
    "slowpc": ("Slow PC", [
        ("Restart it", "If it's been on for days, restart it. It genuinely helps."),
        ("See what's busy", "Press Ctrl+Shift+Esc for Task Manager, click the CPU, Memory and Disk headings and look for one app hogging things. Close it if you don't need it."),
        ("Trim start-up apps", "In Task Manager, Startup apps: turn off things you don't need at once, such as chat and game launchers."),
        ("Check free space", "Settings, System, Storage. Keep at least 15% of the drive free. Turn on Storage Sense to clear temporary files."),
        ("Install updates", "Settings, Windows Update, Check for updates. Restart when it asks."),
        ("Scan for nasties", "Windows Security, Virus and threat protection, Quick scan."),
        ("Look at the browser", "Too many tabs and extensions slow everything. Close spare tabs and remove extensions you don't use."),
    ]),
    "nosound": ("No sound", [
        ("Check the volume", "Click the speaker in the taskbar. Make sure it isn't muted and the slider is up, and that the app's own volume isn't down in the Volume mixer."),
        ("Pick the right output", "Click the small arrow beside the volume slider and choose the speakers or headphones you actually want."),
        ("Check the cables", "Check the plug is fully in, or that Bluetooth speakers and headphones are on, charged and connected."),
        ("Run the sound fixer", "Settings, System, Sound, Troubleshoot common sound problems."),
        ("Restart and try another app", "Restart the PC, which restarts Windows Audio. Try another app or website to see if it's just one program."),
        ("Update or reinstall the driver", "Device Manager, Sound, video and game controllers, right-click your audio device, Update driver, or Uninstall device then restart."),
    ]),
    "bluetooth": ("Bluetooth won't pair", [
        ("Charge and switch on", "Make sure the gadget is charged and switched on, and close to the PC or phone."),
        ("Put it in pairing mode", "Hold the device's Bluetooth button until the light flashes. Most stay in pairing mode for only a minute or two."),
        ("Turn Bluetooth off and on", "On Windows: Settings, Bluetooth and devices. On iPhone: Settings, Bluetooth. Switch it off, wait 10 seconds, and on again."),
        ("Forget and pair again", "Remove the device from the list on the PC or phone, then add it again from scratch."),
        ("Disconnect it elsewhere", "Many gadgets remember another device, such as your phone, and connect to that instead. Turn Bluetooth off on the other device or forget it there."),
        ("Restart everything", "Restart the PC or phone and turn the gadget off and on."),
        ("Update or reset the gadget", "Check the maker's app for a firmware update, or factory reset the gadget using the button combination in its manual."),
    ]),
    "phonestorage": ("Phone storage full", [
        ("See what's using space", "iPhone: Settings, General, iPhone Storage. It lists the biggest apps and gives suggestions."),
        ("Check photos and videos", "Videos take the most room. Look at Photos, Albums, Videos, and delete or move big ones once they're backed up."),
        ("Empty Recently Deleted", "In Photos, Albums, Recently Deleted, tap Select, Delete All. Deleted photos still use space until you do this."),
        ("Offload unused apps", "In iPhone Storage, choose an app and tap Offload App. It keeps your data and frees the app's space."),
        ("Clear Messages attachments", "In iPhone Storage, tap Messages, then Review Large Attachments and delete what you don't need."),
        ("Clear Safari and downloads", "Settings, Apps, Safari, Clear History and Website Data. Also check the Files app for old downloads."),
        ("Back up the rest", "Turn on iCloud Photos, or copy photos to your PC, before deleting them from the phone."),
    ]),
    "iphonebackup": ("iPhone backup", [
        ("Connect to Wi-Fi and power", "iCloud backups need Wi-Fi and, ideally, the phone plugged in and locked."),
        ("Check iCloud space", "Settings, your name, iCloud. The bar shows how much of your storage is used. The free 5 GB is often too little."),
        ("Turn on iCloud Backup", "Settings, your name, iCloud, iCloud Backup, switch on Back Up This iPhone."),
        ("Back up now", "On the same screen, tap Back Up Now and wait until the last backup time updates."),
        ("Choose what's included", "In Settings, your name, iCloud, Manage Account Storage, Backups, pick your phone and switch off what you don't need."),
        ("Make a second copy on the PC", "Plug the iPhone into the PC with the Apple Devices app installed and choose Back Up Now for a local copy."),
        ("Check it worked", "Look at the date under iCloud Backup in Settings. Do this every few months."),
    ]),
}

ALIASES = {
    "wifi": ["wi-fi", "wifi", "internet", "broadband", "network", "router", "online"],
    "printer": ["printer", "printing", "print", "offline"],
    "slowpc": ["slow", "sluggish", "freezing", "laggy", "pc slow", "computer slow", "speed up"],
    "nosound": ["sound", "audio", "speaker", "speakers", "volume", "no sound", "headphones", "mute"],
    "bluetooth": ["bluetooth", "pair", "pairing", "earbuds", "airpods"],
    "phonestorage": ["storage", "phone full", "storage full", "space", "iphone storage"],
    "iphonebackup": ["backup", "back up", "icloud", "iphone backup"],
}

LISTS = {
    "2fa": ("Two-factor checklist", [
        ("Email account", "Turn on two-step verification for your main email first. It can reset everything else."),
        ("Bank and money apps", "Turn on the extra security step in your banking, PayPal and card apps."),
        ("Apple ID or Google account", "Turn on two-factor in Settings, your name, Sign-In and Security (Apple) or your Google account's Security page."),
        ("Social media and shopping", "Turn on two-factor for Facebook, Instagram, Amazon and other accounts that store cards."),
        ("Use an authenticator app", "Prefer an authenticator app to text messages where you have the choice; texts can be hijacked by SIM swap."),
        ("Save backup codes", "Print or write down the recovery codes and keep them somewhere safe at home, not on the same phone."),
        ("Use a password manager", "Let one manager make and remember a different long password for each site."),
        ("Check recovery details", "Make sure your recovery email and phone number are up to date."),
    ]),
    "backup": ("Backup checklist", [
        ("Photos are in two places", "Keep your photos on the phone and in iCloud Photos or on the PC or a drive."),
        ("Phone backs up itself", "iCloud Backup is on and the last backup was recent."),
        ("PC files are copied", "Use File History, OneDrive or an external drive for Documents and Pictures."),
        ("One copy is away from home", "Keep one copy somewhere else, such as cloud storage, in case of fire or theft."),
        ("Passwords and codes are safe", "Your password manager and 2FA backup codes are backed up."),
        ("Test a restore", "Open a backed-up file from the copy to prove it really works."),
        ("Diarise it", "Set a reminder every three months to check all of the above."),
    ]),
}
