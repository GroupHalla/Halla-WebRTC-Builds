from pathlib import Path
import re
import sys
import urllib.request

root = Path(__file__).resolve().parents[1]
version = (root / "VERSION").read_text(encoding="utf-8").strip()
assert re.fullmatch(r"\d+\.\d+\.\d+", version)
revisions = {}
for name in ("WEBRTC_REVISION", "DEPOT_TOOLS_REVISION"):
    revisions[name] = (root / name).read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"[0-9a-f]{40}", revisions[name]), name
workflow = (root / ".github/workflows/build-webrtc-windows.yml").read_text(encoding="utf-8")
android_workflow = (root / ".github/workflows/build-webrtc-android.yml").read_text(encoding="utf-8")
packager = (root / "scripts/package-webrtc-windows.ps1").read_text(encoding="utf-8")
assert "MANIFEST.sha256" in packager and "zip.sha256" in workflow
assert "CreatePeerConnection" in (root / "samples/factory_smoke.cpp").read_text(encoding="utf-8")
for workflow_text in (workflow, android_workflow):
    for line in workflow_text.splitlines():
        if "uses:" in line:
            ref = line.split("@", 1)[-1].split()[0]
            assert re.fullmatch(r"[0-9a-f]{40}", ref), line

android_version = (root / "ANDROID_VERSION").read_text(encoding="utf-8").strip()
assert re.fullmatch(r"\d+\.\d+\.\d+", android_version)
external_audio = (root / "android-sdk/src/main/java/com/halla/webrtc/audio/HallaExternalAudioDeviceModule.java").read_text(encoding="utf-8")
pcm_queue = (root / "android-sdk/src/main/java/com/halla/webrtc/audio/HallaPcmQueue.java").read_text(encoding="utf-8")
assert "setAudioBufferCallback" in external_audio
assert "setAudioRecordEnabled(false)" in external_audio
assert "pushPcm16Mono48k" in external_audio
assert "CALLBACK_INTERVAL_NS = 10_000_000L" in pcm_queue
assert "MAX_BUFFERED_BYTES" in pcm_queue
patcher = (root / "tools/patch_webrtc_android_aar.py").read_text(encoding="utf-8")
assert 'target.replace(b"hasArray", b"isDirect")' in patcher
assert "EXPECTED_UPSTREAM_SHA256" in patcher
assert "halla-webrtc-android-144.7559.09-p1.aar" in android_workflow

if "--verify-upstream" in sys.argv:
    import time
    import urllib.error

    urls = {
        "WEBRTC_REVISION": "https://webrtc.googlesource.com/src/+/{revision}?format=JSON",
        "DEPOT_TOOLS_REVISION": "https://chromium.googlesource.com/chromium/tools/depot_tools/+/{revision}?format=JSON",
    }
    for name, template in urls.items():
        url = template.format(revision=revisions[name])
        request = urllib.request.Request(url, headers={"User-Agent": "Halla-WebRTC-policy"})
        # googlesource responde 503 intermitentemente (visto 2x no mesmo dia
        # nos runs de 2026-09-25); o gate de política não pode reprovar o
        # repositório por indisponibilidade transitória do upstream.
        last_error = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    assert response.status == 200, (name, response.status)
                    body = response.read(256)
                    assert revisions[name].encode() in body, f"{name} não pertence ao upstream esperado"
                last_error = None
                break
            except urllib.error.HTTPError as error:
                if error.code not in (503, 502, 504):
                    raise
                last_error = error
                print(f"upstream {name}: HTTP {error.code}, tentativa {attempt + 1}/4")
                time.sleep(10 * (attempt + 1))
        if last_error is not None:
            raise last_error
        print(f"verified upstream: {name}")

print(f"WebRTC build policy OK: {version}")
