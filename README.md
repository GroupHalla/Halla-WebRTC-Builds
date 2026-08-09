# Halla WebRTC Builds

Prebuilt native WebRTC SDK packages used by the Halla desktop client.

The Halla desktop repository consumes these release assets through `HALLA_WEBRTC_SDK_DIR`.
Artifacts are intentionally kept out of the application repositories because libwebrtc is large and expensive to build.

## Packages

Initial target:

- `halla-webrtc-windows-x64-<tag>.zip`

Planned targets:

- `halla-webrtc-linux-x64-<tag>.tar.gz`
- `halla-webrtc-linux-arm64-<tag>.tar.gz`

## Package layout

```text
halla-webrtc-sdk/
  VERSION.txt
  include/          # WebRTC headers and generated headers
  lib/windows-x64/  # webrtc.lib
  licenses/
```

## Building

The Windows workflow builds libwebrtc with Chromium `depot_tools`, GN and Ninja.
It is intentionally manual/tag-driven because a full WebRTC build is large and slow.

```text
git tag v0.1.0
git push origin v0.1.0
```

or run the workflow manually from GitHub Actions.

## Halla Desktop usage

After publishing a release asset, Halla desktop can download and configure with:

```bash
cmake -S . -B build -DHALLA_WEBRTC_SDK_DIR=/path/to/halla-webrtc-sdk
```
