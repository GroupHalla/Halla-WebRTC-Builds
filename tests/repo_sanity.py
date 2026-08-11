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
packager = (root / "scripts/package-webrtc-windows.ps1").read_text(encoding="utf-8")
assert "MANIFEST.sha256" in packager and "zip.sha256" in workflow
assert "CreatePeerConnection" in (root / "samples/factory_smoke.cpp").read_text(encoding="utf-8")
for line in workflow.splitlines():
    if "uses:" in line:
        ref = line.split("@", 1)[-1].split()[0]
        assert re.fullmatch(r"[0-9a-f]{40}", ref), line

if "--verify-upstream" in sys.argv:
    urls = {
        "WEBRTC_REVISION": "https://webrtc.googlesource.com/src/+/{revision}?format=JSON",
        "DEPOT_TOOLS_REVISION": "https://chromium.googlesource.com/chromium/tools/depot_tools/+/{revision}?format=JSON",
    }
    for name, template in urls.items():
        url = template.format(revision=revisions[name])
        request = urllib.request.Request(url, headers={"User-Agent": "Halla-WebRTC-policy"})
        with urllib.request.urlopen(request, timeout=30) as response:
            assert response.status == 200, (name, response.status)
            body = response.read(256)
            assert revisions[name].encode() in body, f"{name} não pertence ao upstream esperado"
        print(f"verified upstream: {name}")

print(f"WebRTC build policy OK: {version}")
