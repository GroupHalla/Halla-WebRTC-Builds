# Halla WebRTC Builds

Reproducible prebuilt native WebRTC SDK used by Halla Desktop.

## Current release line

- Package version: `0.1.13` (`VERSION`)
- WebRTC source: exact commit in `WEBRTC_REVISION`
- depot_tools: exact commit in `DEPOT_TOOLS_REVISION`
- Target: Windows x64, MSVC ABI, dynamic CRT (`/MD`)

## Release contents

```text
halla-webrtc-sdk/
  VERSION.txt
  MANIFEST.sha256
  SBOM.spdx.json
  include/
  lib/windows-x64/webrtc.lib
  licenses/
```

Every release publishes both the ZIP and `<zip>.sha256`. Consumers must verify
the external checksum before extraction and then verify `MANIFEST.sha256`.
`VERSION.txt` records both upstream commits and the GN-arguments hash.

## Building

Tag must match `v$(cat VERSION)`:

```text
git tag v0.1.13
git push origin v0.1.13
```

The workflow checks out immutable WebRTC/depot_tools revisions, builds with GN
and Ninja, creates an SPDX SBOM and runs a real MSVC factory link smoke test.

## Halla Desktop usage

```bash
cmake -S . -B build \
  -DHALLA_WEBRTC_SDK_DIR=/path/to/halla-webrtc-sdk \
  -DHALLA_ENABLE_WEBRTC_NATIVE=ON
```
