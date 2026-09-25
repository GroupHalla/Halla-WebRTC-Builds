param(
  [Parameter(Mandatory=$true)][string]$CheckoutRoot,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [Parameter(Mandatory=$true)][string]$TagName,
  [Parameter(Mandatory=$true)][string]$WebRtcRevision,
  [Parameter(Mandatory=$true)][string]$DepotToolsRevision
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
  Get-ChildItem $out -Recurse -Filter "*.lib" | Select-Object -First 80 | ForEach-Object { Write-Host $_.FullName }
  throw "webrtc.lib not found"
}
Copy-Item $lib (Join-Path $libdir "webrtc.lib") -Force
Write-Host "Packaged $lib"

# Basic license metadata.
Copy-Item (Join-Path $src "LICENSE") (Join-Path $licenses "LICENSE.webrtc") -Force -ErrorAction SilentlyContinue
Set-Content -Path (Join-Path $pkg "VERSION.txt") -Value @(
  "tag=$TagName",
  "target=windows-x64",
  "webrtc_revision=$WebRtcRevision",
  "depot_tools_revision=$DepotToolsRevision",
  "gn_args_sha256=$((Get-FileHash (Join-Path $PSScriptRoot "..\gn_args\windows-x64.gn") -Algorithm SHA256).Hash.ToLower())",
  "built=$(Get-Date -AsUTC -Format o)"
)

$sbom = [ordered]@{
  spdxVersion = "SPDX-2.3"
  dataLicense = "CC0-1.0"
  SPDXID = "SPDXRef-DOCUMENT"
  name = "Halla-WebRTC-Windows-x64-$TagName"
  documentNamespace = "https://github.com/GroupHalla/Halla-WebRTC-Builds/$TagName/$WebRtcRevision"
  creationInfo = @{ created = (Get-Date -AsUTC -Format "yyyy-MM-ddTHH:mm:ssZ"); creators = @("Tool: Halla-WebRTC-Builds") }
  packages = @(@{
    name = "libwebrtc"
    SPDXID = "SPDXRef-Package-libwebrtc"
    versionInfo = $WebRtcRevision
    downloadLocation = "git+https://webrtc.googlesource.com/src.git@$WebRtcRevision"
    filesAnalyzed = $false
    licenseConcluded = "BSD-3-Clause"
    licenseDeclared = "BSD-3-Clause"
  })
}
$sbom | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $pkg "SBOM.spdx.json")

$manifestLines = Get-ChildItem $pkg -Recurse -File | Where-Object { $_.Name -ne "MANIFEST.sha256" } | ForEach-Object {
  $relative = $_.FullName.Substring($pkg.Length + 1).Replace('\', '/')
  $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
  "$hash  $relative"
}
$manifestLines | Set-Content -Encoding ascii (Join-Path $pkg "MANIFEST.sha256")

$zip = Join-Path $OutDir "halla-webrtc-windows-x64-$TagName.zip"
Remove-Item -Force $zip -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $pkg "*") -DestinationPath $zip
Write-Host "Packaged $zip"
