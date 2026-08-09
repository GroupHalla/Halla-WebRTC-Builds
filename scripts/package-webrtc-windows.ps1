param(
  [Parameter(Mandatory=$true)][string]$CheckoutRoot,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [Parameter(Mandatory=$true)][string]$TagName
)

$ErrorActionPreference = "Stop"
$src = Join-Path $CheckoutRoot "src"
$out = Join-Path $src "out\Release"
$pkg = Join-Path $CheckoutRoot "halla-webrtc-sdk"
$include = Join-Path $pkg "include"
$libdir = Join-Path $pkg "lib\windows-x64"
$licenses = Join-Path $pkg "licenses"

Remove-Item -Recurse -Force $pkg -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $include, $libdir, $licenses | Out-Null

# Copy public and internal headers used by native WebRTC consumers. This keeps
# paths relative to Chromium's src root (api/, rtc_base/, modules/, pc/, etc.).
$headerExt = @("*.h", "*.hpp", "*.hh", "*.inc")
$includeRoots = @(
  "api", "audio", "call", "common_audio", "common_video", "logging", "media",
  "modules", "p2p", "pc", "rtc_base", "sdk", "stats", "system_wrappers",
  "third_party\abseil-cpp\absl", "third_party\libyuv\include", "video"
)
foreach ($root in $includeRoots) {
  $from = Join-Path $src $root
  if (Test-Path $from) {
    foreach ($pattern in $headerExt) {
      Get-ChildItem $from -Recurse -File -Filter $pattern | ForEach-Object {
        $rel = $_.FullName.Substring($src.Length + 1)
        $dest = Join-Path $include $rel
        New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
        Copy-Item $_.FullName $dest -Force
      }
    }
  }
}

# Generated headers (protobuf/build flags/etc.)
$gen = Join-Path $out "gen"
if (Test-Path $gen) {
  Get-ChildItem $gen -Recurse -File -Include $headerExt | ForEach-Object {
    $rel = $_.FullName.Substring($gen.Length + 1)
    $dest = Join-Path $include $rel
    New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
    Copy-Item $_.FullName $dest -Force
  }
}

# The default GN target creates obj/webrtc.lib for Windows static builds.
$candidates = @(
  (Join-Path $out "obj\webrtc.lib"),
  (Join-Path $out "webrtc.lib")
)
$lib = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $lib) {
  Write-Host "Available .lib files:"
  Get-ChildItem $out -Recurse -Filter "*.lib" | Select-Object -First 50 | ForEach-Object { Write-Host $_.FullName }
  throw "webrtc.lib not found"
}
Copy-Item $lib (Join-Path $libdir "webrtc.lib") -Force

# Basic license metadata.
Copy-Item (Join-Path $src "LICENSE") (Join-Path $licenses "LICENSE.webrtc") -Force -ErrorAction SilentlyContinue
Set-Content -Path (Join-Path $pkg "VERSION.txt") -Value @(
  "tag=$TagName",
  "target=windows-x64",
  "built=$(Get-Date -AsUTC -Format o)"
)

$zip = Join-Path $OutDir "halla-webrtc-windows-x64-$TagName.zip"
Remove-Item -Force $zip -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $pkg "*") -DestinationPath $zip
Write-Host "Packaged $zip"
