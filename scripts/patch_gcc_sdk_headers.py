#!/usr/bin/env python3
"""Patches de GCC-friendliness nos headers públicos do SDK libwebrtc.

O SDK é consumido pelo app Halla compilado com GCC (libstdc++ 12 no Ubuntu
22.04); o próprio SDK é compilado com clang, que aceita construções que o
GCC rejeita. Cada patch abaixo é idempotente, documentado e não muda ABI.
"""

import sys
from pathlib import Path

PATCHES = [
    {
        "file": "p2p/base/port_interface.h",
        "why": (
            "GCC rejeita 'virtual const Network* Network() const' com "
            "-Wchanges-meaning (nome de membro igual ao nome do tipo usado "
            "no retorno no mesmo escopo — regra [basic.scope.class] que "
            "clang/MSVC não implementam). O elaborated-type-specifier "
            "'class Network' resolve sem mudar a assinatura/ABI."
        ),
        "old": "virtual const Network* Network() const = 0;",
        "new": "virtual const class Network* Network() const = 0;",
    },
]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"uso: {sys.argv[0]} <webrtc-checkout>/src", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    for patch in PATCHES:
        path = src / patch["file"]
        text = path.read_text(encoding="utf-8")
        if patch["new"] in text:
            print(f"{patch['file']}: patch já aplicado")
            continue
        if patch["old"] not in text:
            print(f"{patch['file']}: âncora não encontrada — revisão do "
                  "libwebrtc mudou?", file=sys.stderr)
            return 1
        path.write_text(text.replace(patch["old"], patch["new"], 1),
                        encoding="utf-8")
        print(f"{patch['file']}: aplicado ({patch['old']} -> {patch['new']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
