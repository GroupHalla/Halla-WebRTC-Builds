#!/usr/bin/env python3
"""Patch the pinned WebRTC Android AAR for external AudioBufferCallback input."""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import zipfile

EXPECTED_UPSTREAM_SHA256 = "34cf91dd7497e5fe88adb76ba29ccae35db42dd6614ce548b79ce037b6d634d5"
TARGET_CLASS = "org/webrtc/audio/WebRtcAudioRecord.class"


def rewrite_zip(source: bytes, replacements: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source), "r") as zin, zipfile.ZipFile(output, "w") as zout:
        for info in zin.infolist():
            data = replacements.get(info.filename, zin.read(info.filename))
            clone = zipfile.ZipInfo(info.filename, info.date_time)
            clone.compress_type = info.compress_type
            clone.comment = info.comment
            clone.extra = info.extra
            clone.internal_attr = info.internal_attr
            clone.external_attr = info.external_attr
            clone.create_system = info.create_system
            zout.writestr(clone, data)
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    aar = args.input.read_bytes()
    actual = hashlib.sha256(aar).hexdigest()
    if actual != EXPECTED_UPSTREAM_SHA256:
        raise SystemExit(f"upstream AAR checksum mismatch: {actual}")

    with zipfile.ZipFile(io.BytesIO(aar), "r") as archive:
        classes_jar = archive.read("classes.jar")
    with zipfile.ZipFile(io.BytesIO(classes_jar), "r") as classes:
        target = classes.read(TARGET_CLASS)

    if target.count(b"hasArray") != 1 or b"isDirect" in target:
        raise SystemExit("unexpected WebRtcAudioRecord bytecode; refusing patch")
    # Both JVM method names are eight bytes and have the same ()Z descriptor,
    # so this changes only the constant-pool method name. The resulting bytecode
    # verifies that the native cache buffer is direct instead of incorrectly
    # requiring a Java backing array.
    patched_class = target.replace(b"hasArray", b"isDirect")
    patched_classes = rewrite_zip(classes_jar, {TARGET_CLASS: patched_class})
    patched_aar = rewrite_zip(aar, {"classes.jar": patched_classes})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched_aar)

    with zipfile.ZipFile(io.BytesIO(patched_aar), "r") as archive:
        check_jar = archive.read("classes.jar")
    with zipfile.ZipFile(io.BytesIO(check_jar), "r") as classes:
        check = classes.read(TARGET_CLASS)
    if b"hasArray" in check or check.count(b"isDirect") != 1:
        raise SystemExit("post-patch verification failed")
    print(f"patched AAR OK: {hashlib.sha256(patched_aar).hexdigest()}")


if __name__ == "__main__":
    main()
