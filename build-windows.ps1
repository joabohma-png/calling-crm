$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  throw "Python Launcher (py) saknas. Installera Python 3.12+ från python.org."
}
py -3 -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "PyInstaller saknas. Installera med: py -3 -m pip install pyinstaller"
  exit 2
}
py -3 -m PyInstaller --noconfirm --clean --onedir --name CallingCRM --paths . launcher.py
New-Item -ItemType Directory -Force -Path dist\CallingCRM\data | Out-Null
Copy-Item start-windows.cmd dist\CallingCRM\start-windows.cmd -Force
Write-Host "Byggd: dist\CallingCRM"
