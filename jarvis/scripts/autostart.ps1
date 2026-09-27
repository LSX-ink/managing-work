# Start Jarvis by itself when you log in to Windows (adds a shortcut to your Startup folder).
#   .\scripts\autostart.ps1          turn it on
#   .\scripts\autostart.ps1 -Remove  turn it off
param([switch]$Remove)

$startup = [Environment]::GetFolderPath('Startup')
$link = Join-Path $startup 'Jarvis.lnk'

if ($Remove) {
    Remove-Item $link -ErrorAction SilentlyContinue
    Write-Output "Done. Jarvis won't start with Windows any more."
    return
}

$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($link)
$shortcut.TargetPath = Join-Path $PSScriptRoot 'start-jarvis.cmd'
$shortcut.WorkingDirectory = Split-Path $PSScriptRoot
$shortcut.WindowStyle = 7  # minimised
$shortcut.Save()
Write-Output "Done. Jarvis will start by itself next time you log in to Windows, and the HUD will open."
