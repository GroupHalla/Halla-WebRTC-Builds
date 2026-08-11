from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
version = (root / "VERSION").read_text().strip()
assert re.fullmatch(r"\d+\.\d+\.\d+", version)
for name in ("WEBRTC_REVISION", "DEPOT_TOOLS_REVISION"):
    assert re.fullmatch(r"[0-9a-f]{40}", (root / name).read_text().strip()), name
workflow = (root / ".github/workflows/build-webrtc-windows.yml").read_text()
packager = (root / "scripts/package-webrtc-windows.ps1").read_text()
assert "MANIFEST.sha256" in packager and "zip.sha256" in workflow
assert "CreatePeerConnection" in (root / "samples/factory_smoke.cpp").read_text()
for line in workflow.splitlines():
    if "uses:" in line:
        ref = line.split("@", 1)[-1].split()[0]
        assert re.fullmatch(r"[0-9a-f]{40}", ref), line
print(f"WebRTC build policy OK: {version}")
