#!/usr/bin/env python3
"""Empacota o SDK WebRTC Linux x64 a partir do checkout do libwebrtc.

Porta do scripts/package-webrtc-windows.ps1: copia os headers públicos e
internos usados por consumidores nativos (caminhos relativos à raiz src do
Chromium), a biblioteca estática do alvo `webrtc`, e gera VERSION.txt,
SBOM.spdx.json e MANIFEST.sha256 com a mesma estrutura do pacote Windows.
"""

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import sys
import zipfile
from datetime import datetime, timezone

HEADER_EXTS = {".h", ".hpp", ".hh", ".inc"}
INCLUDE_ROOTS = [
    "api", "audio", "call", "common_audio", "common_video", "logging", "media",
    "modules", "p2p", "pc", "rtc_base", "sdk", "stats", "system_wrappers",
    "third_party/abseil-cpp/absl", "third_party/libyuv/include", "video",
]


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_headers(source_root: pathlib.Path, include_dir: pathlib.Path) -> None:
    copied = 0
    for root_name in INCLUDE_ROOTS:
        root = source_root / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in HEADER_EXTS:
                continue
            relative = path.relative_to(source_root)
            destination = include_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            copied += 1
    return copied


def copy_generated_headers(out_dir: pathlib.Path, include_dir: pathlib.Path) -> int:
    generated = out_dir / "gen"
    if not generated.is_dir():
        return 0
    copied = 0
    for path in generated.rglob("*"):
        if not path.is_file() or path.suffix not in HEADER_EXTS:
            continue
        relative = path.relative_to(generated)
        destination = include_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied += 1
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout-root", required=True,
                        help="Diretório que contém src/ (checkout do webrtc)")
    parser.add_argument("--out-dir", required=True,
                        help="Onde gravar o ZIP final")
    parser.add_argument("--tag-name", required=True)
    parser.add_argument("--webrtc-revision", required=True)
    parser.add_argument("--depot-tools-revision", required=True)
    args = parser.parse_args()

    checkout_root = pathlib.Path(args.checkout_root).resolve()
    out_dir = pathlib.Path(args.out_dir).resolve()
    src = checkout_root / "src"
    build_out = src / "out" / "Release"
    package = checkout_root / "halla-webrtc-sdk"
    include_dir = package / "include"
    lib_dir = package / "lib" / "linux-x64"
    licenses_dir = package / "licenses"

    if package.exists():
        shutil.rmtree(package)
    include_dir.mkdir(parents=True)
    lib_dir.mkdir(parents=True)
    licenses_dir.mkdir(parents=True)

    copied = copy_headers(src, include_dir)
    copied += copy_generated_headers(build_out, include_dir)
    print(f"Copied {copied} headers")

    # O alvo GN `webrtc` produz obj/libwebrtc.a no Linux (no Windows é
    # obj/webrtc.lib); aceitamos ambos por simetria com o script Windows.
    candidates = [build_out / "obj" / "libwebrtc.a", build_out / "libwebrtc.a"]
    static_lib = next((path for path in candidates if path.is_file()), None)
    if static_lib is None:
        print("ERROR: libwebrtc.a not found; listing .a files:", file=sys.stderr)
        for path in sorted(build_out.rglob("*.a"))[:80]:
            print(f"  {path}", file=sys.stderr)
        return 1
    shutil.copy2(static_lib, lib_dir / "libwebrtc.a")
    print(f"Packaged {static_lib}")

    webrtc_license = src / "LICENSE"
    if webrtc_license.is_file():
        shutil.copy2(webrtc_license, licenses_dir / "LICENSE.webrtc")

    gn_args = pathlib.Path(__file__).resolve().parent.parent / "gn_args" / "linux-x64.gn"
    version_lines = [
        f"tag={args.tag_name}",
        "target=linux-x64",
        f"webrtc_revision={args.webrtc_revision}",
        f"depot_tools_revision={args.depot_tools_revision}",
        f"gn_args_sha256={sha256_file(gn_args)}",
        f"built={datetime.now(timezone.utc).isoformat()}",
    ]
    (package / "VERSION.txt").write_text("\n".join(version_lines) + "\n", encoding="utf-8")

    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"Halla-WebRTC-Linux-x64-{args.tag_name}",
        "documentNamespace": (
            "https://github.com/GroupHalla/Halla-WebRTC-Builds/"
            f"{args.tag_name}/{args.webrtc_revision}"),
        "creationInfo": {
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "creators": ["Tool: Halla-WebRTC-Builds"],
        },
        "packages": [{
            "name": "libwebrtc",
            "SPDXID": "SPDXRef-Package-libwebrtc",
            "versionInfo": args.webrtc_revision,
            "downloadLocation": f"git+https://webrtc.googlesource.com/src.git@{args.webrtc_revision}",
            "filesAnalyzed": False,
            "licenseConcluded": "BSD-3-Clause",
            "licenseDeclared": "BSD-3-Clause",
        }],
    }
    (package / "SBOM.spdx.json").write_text(
        json.dumps(sbom, indent=2), encoding="utf-8")

    manifest_lines = []
    for path in sorted(package.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.sha256":
            continue
        relative = path.relative_to(package).as_posix()
        manifest_lines.append(f"{sha256_file(path)}  {relative}")
    (package / "MANIFEST.sha256").write_text("\n".join(manifest_lines) + "\n",
                                              encoding="ascii")

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"halla-webrtc-linux-x64-{args.tag_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(package).as_posix())
    print(f"Packaged {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
