# ShoGy-HR · extract the game database (Game2.dcb) + names (global.ini) from your own Star Citizen install.
# Read-only: it never changes the game. Needs unp4k.exe (https://github.com/dolkensp/unp4k/releases).
# Run:  right-click > "Run with PowerShell"   (or:  powershell -ExecutionPolicy Bypass -File .\extract_game_data.ps1)

param([string]$P4k = "", [string]$Unp4k = "")
$ErrorActionPreference = "Stop"
function Say($t, $c = "Cyan") { Write-Host $t -ForegroundColor $c }

# 1) find Data.p4k (LIVE)
if (-not $P4k) {
  $cands = @("C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k")
  foreach ($d in (Get-PSDrive -PSProvider FileSystem).Root) {
    $cands += "$d" + "Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k"
    $cands += "$d" + "Roberts Space Industries\StarCitizen\LIVE\Data.p4k"
    $cands += "$d" + "StarCitizen\LIVE\Data.p4k"
    $cands += "$d" + "Games\Roberts Space Industries\StarCitizen\LIVE\Data.p4k"
    foreach ($sub in (Get-ChildItem $d -Directory -ErrorAction SilentlyContinue)) {
      $cands += Join-Path $sub.FullName "Roberts Space Industries\StarCitizen\LIVE\Data.p4k"
    }
  }
  # several installs (old leftovers)? take the most recently updated one
  $P4k = $cands | Select-Object -Unique | Where-Object { Test-Path $_ } |
    Sort-Object { (Get-Item $_).LastWriteTime } -Descending | Select-Object -First 1
}
if (-not $P4k) { $P4k = Read-Host "Data.p4k not found. Paste the full path to ...\StarCitizen\LIVE\Data.p4k" }
if (-not (Test-Path $P4k)) { Say "Data.p4k not found: $P4k" Red; Read-Host "Enter to close"; exit 1 }
$live = Split-Path $P4k
Say ("Game: {0}  (updated {1})" -f $P4k, (Get-Item $P4k).LastWriteTime)

# 2) find unp4k.exe (next to this script, in Downloads or Desktop)
if (-not $Unp4k) {
  $roots = @($PSScriptRoot, "$env:USERPROFILE\Downloads", "$env:USERPROFILE\Desktop") | Where-Object { $_ -and (Test-Path $_) }
  foreach ($r in $roots) {
    $f = Get-ChildItem $r -Recurse -Filter unp4k.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($f) { $Unp4k = $f.FullName; break }
  }
}
if (-not $Unp4k) { $Unp4k = Read-Host "unp4k.exe not found. Paste the full path to unp4k.exe" }
if (-not (Test-Path $Unp4k)) { Say "unp4k.exe not found: $Unp4k" Red; Read-Host "Enter to close"; exit 1 }
Say "unp4k: $Unp4k"

# 3) extract into a fresh work folder next to this script
$ver = "unknown"
$bm = Join-Path $live "build_manifest.id"
if (Test-Path $bm) {
  try { $j = Get-Content $bm -Raw | ConvertFrom-Json; $ver = "$($j.Data.Branch)-$($j.Data.RequestedP4ChangeNum)" } catch {}
}
$out = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$work = Join-Path $out "SC_data_extract"
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
New-Item -ItemType Directory $work | Out-Null
Push-Location $work
try {
  Say "Extracting Game2.dcb (game database), this can take a few minutes..."
  & $Unp4k $P4k "Game2.dcb" 2>&1 | Select-Object -Last 5
  Say "Extracting global.ini (item names)..."
  & $Unp4k $P4k "global.ini" 2>&1 | Select-Object -Last 3
  # keep only English
  Get-ChildItem $work -Recurse -Filter global.ini | Where-Object { $_.FullName -notmatch "\\english\\" } | Remove-Item -Force
} finally { Pop-Location }
if (Test-Path $bm) { Copy-Item $bm $work }

$dcb = Get-ChildItem $work -Recurse -Filter Game2.dcb | Select-Object -First 1
$ini = Get-ChildItem $work -Recurse -Filter global.ini | Where-Object { $_.FullName -match "\\english\\" } | Select-Object -First 1
if (-not $dcb) { Say "Game2.dcb was NOT extracted. Send ShoGy-HR a screenshot of this window." Red; Read-Host "Enter to close"; exit 1 }
Say ("Game2.dcb  {0:N0} MB" -f ($dcb.Length / 1MB)) Green
if ($ini) { Say ("global.ini {0:N1} MB" -f ($ini.Length / 1MB)) Green } else { Say "global.ini missing (names), continuing" Yellow }

# 4) zip it
$zip = Join-Path $out ("SC_data_{0}.zip" -f ($ver -replace '[^\w\.-]', '_'))
if (Test-Path $zip) { Remove-Item $zip -Force }
Say "Zipping..."
Compress-Archive -Path (Join-Path $work "*") -DestinationPath $zip -CompressionLevel Optimal
Say ("DONE: {0}  ({1:N0} MB)" -f $zip, ((Get-Item $zip).Length / 1MB)) Green
Remove-Item $work -Recurse -Force
Say "Send this zip to Claude." Green
Start-Process explorer.exe "/select,`"$zip`""
Read-Host "Enter to close"
