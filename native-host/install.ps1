<#
.SYNOPSIS
  Register the scholar-search native messaging host for Edge and Chrome.
.DESCRIPTION
  Builds the launcher executable, writes the native messaging manifest, and
  registers the per-user key under HKCU. No elevation required.
  Use -Uninstall to remove the registration.
#>
param(
  [string]$ExtensionId = "gmaimbocfjkolcpljeekjcomakipoaph",
  [string]$Python,
  [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$hostName = "com.scholar.search"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$project = Split-Path -Parent $here

if (-not $Python) {
  $Python = Join-Path $project ".venv\Scripts\python.exe"
}

$manifestPath = Join-Path $here "$hostName.json"
$launcher = Join-Path $here "scholar-host.exe"
$pythonPathFile = Join-Path $here "python-path.txt"

if ($Uninstall) {
  foreach ($browser in @("Microsoft\Edge", "Google\Chrome")) {
    $key = "HKCU:\Software\$browser\NativeMessagingHosts\$hostName"
    if (Test-Path $key) { Remove-Item $key -Recurse -Force }
  }
  Remove-Item $manifestPath, $launcher, $pythonPathFile -Force -ErrorAction SilentlyContinue
  Write-Host "removed $hostName"
  exit 0
}

if (-not (Test-Path $Python)) {
  throw "python not found: $Python (pass -Python <path>)"
}

$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $launcher)) {
  if (-not (Test-Path $csc)) {
    throw "csc.exe not found; cannot build $launcher"
  }
  & $csc /nologo /target:exe /out:$launcher (Join-Path $here "launcher.cs") | Out-Null
}
Set-Content -Path $pythonPathFile -Value $Python -Encoding ascii

$manifest = @{
  name            = $hostName
  description     = "scholar-search native bridge"
  path            = ($launcher -replace "\\", "/")
  type            = "stdio"
  allowed_origins = @("chrome-extension://$ExtensionId/")
} | ConvertTo-Json -Compress

Set-Content -Path $manifestPath -Value $manifest -Encoding utf8

foreach ($browser in @("Microsoft\Edge", "Google\Chrome")) {
  $key = "HKCU:\Software\$browser\NativeMessagingHosts\$hostName"
  New-Item -Path $key -Force | Out-Null
  Set-ItemProperty -Path $key -Name "(Default)" -Value $manifestPath
}

Write-Host "registered $hostName"
Write-Host "  manifest : $manifestPath"
Write-Host "  launcher : $launcher"
Write-Host "  ext id   : $ExtensionId"
