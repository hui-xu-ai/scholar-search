<#
.SYNOPSIS
  Register the scholar-search native messaging host for Edge and Chrome.
.DESCRIPTION
  Writes a launcher, a native messaging manifest, and the per-user registry
  key under HKCU. No elevation required. Run with -Uninstall to remove.
#>
param(
  [Parameter(Mandatory = $true)][string]$ExtensionId,
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
$launcher = Join-Path $here "run-host.cmd"

if ($Uninstall) {
  foreach ($browser in @("Microsoft\Edge", "Google\Chrome")) {
    $key = "HKCU:\Software\$browser\NativeMessagingHosts\$hostName"
    if (Test-Path $key) { Remove-Item $key -Recurse -Force }
  }
  Remove-Item $manifestPath, $launcher -Force -ErrorAction SilentlyContinue
  Write-Host "removed $hostName"
  exit 0
}

if (-not (Test-Path $Python)) {
  throw "python not found: $Python (pass -Python <path>)"
}

@"
@echo off
"$Python" -u "$here\main.py"
"@ | Set-Content -Path $launcher -Encoding ascii

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
