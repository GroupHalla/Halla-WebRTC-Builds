# Halla WebRTC Builds

Reproducible WebRTC SDKs used by Halla Desktop and Halla Mobile.

## Current release line

- Package version: `0.1.14` (`VERSION`)
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
git tag v0.1.14
git push origin v0.1.14
```

The workflow checks out immutable WebRTC/depot_tools revisions, builds with GN
and Ninja, creates an SPDX SBOM and runs a real MSVC factory link smoke test.

## Halla Desktop usage

```bash
cmake -S . -B build \
  -DHALLA_WEBRTC_SDK_DIR=/path/to/halla-webrtc-sdk \
  -DHALLA_ENABLE_WEBRTC_NATIVE=ON
```

## Android external-audio SDK

`android-sdk/` adds a stable PCM-injection API on top of the maintained
`io.github.webrtc-sdk:android` AAR. It uses libwebrtc's public
`JavaAudioDeviceModule.AudioBufferCallback`, while disabling the microphone
owned by that ADM, so Halla can feed `AudioPlaybackCapture` without opening a
second microphone.

Input contract:

- signed PCM 16-bit little-endian;
- mono, 48 kHz;
- arbitrary chunk sizes (internally paced into 10 ms WebRTC buffers);
- bounded two-second queue.

```java
HallaExternalAudioDeviceModule external =
    HallaExternalAudioDeviceModule.create(context);
PeerConnectionFactory factory = PeerConnectionFactory.builder()
    .setAudioDeviceModule(external.audioDeviceModule())
    .createPeerConnectionFactory();
external.pushPcm16Mono48k(pcm);
```

Release tags use `android-v$(cat ANDROID_VERSION)` and publish the wrapper AAR,
sources JAR, Maven POM, checksums and a patched upstream AAR. The pinned upstream
build incorrectly checked `hasArray()` after allocating its native direct audio
buffer; Halla's reproducible patch changes that check to `isDirect()`, allowing
the public external-audio callback to initialize.
