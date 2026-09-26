#!/usr/bin/env python3
"""Desliga a emissão de realocações CREL no build do SDK libwebrtc.

O build config do Chromium liga `-Wa,--crel,--allow-experimental-crel`
para ELF (crbug.com/357878242) porque o Chromium se linka com lld, que
entende SHT_CREL. O SDK do Halla é consumido pelo app compilado com GCC
do Ubuntu 22.04 e LINKADO com GNU ld (binutils 2.38): realocações CREL
(``seções .crel.text``) só são suportadas pelo binutils >= 2.44 — o ld
2.38 falha com "unknown type [0x40000014] section `.crel.text'" e a
cascata "error in (...)(.eh_frame); no .eh_frame_hdr table will be
created" (o ld não consegue ler as realocações do .eh_frame, que também
saem em .crel.eh_frame).

Sem CREL o clang emite .rela.* clássico, que qualquer binutils aceita. O
lld usado no build do SDK aceita os dois formatos — remover a flag não
afeta o ninja, só o consumidor final.

Idempotente; falha (exit 1) se a âncora sumir, para o CI gritar em vez
de publicar um SDK que não linka.
"""

import re
import sys
from pathlib import Path

BUILD_GN = Path("build/config/compiler/BUILD.gn")

# Bloco exato da revisão pinada (build@0d8b711d97d1ec64909af024363817e480640fb7):
#   # Enable ELF CREL (see crbug.com/357878242) for all platforms that use ELF.
#   ...
#   if (is_linux && use_lld && current_cpu != "arm" && current_cpu != "s390x") {
#     cflags += [ "-Wa,--crel,--allow-experimental-crel" ]
#   }
# A âncora é a linha do cflags (única no arquivo); a condição do if é
# casada com whitespace flexível para tolerar reformatting do GN.
CREL_IF_RE = re.compile(
    r'if\s*\(is_linux && use_lld && current_cpu != "arm" && '
    r'current_cpu != "s390x"\)\s*\{\s*\n'
    r'(\s*)cflags \+= \[ "-Wa,--crel,--allow-experimental-crel" \]'
)

REPLACEMENT = (
    "if (false) {  # Halla: CREL off — consumidor linka com GNU ld "
    "(binutils 2.38 do Ubuntu 22.04, sem SHT_CREL)\n"
    "\\1cflags += []"
)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"uso: {sys.argv[0]} <webrtc-checkout>/src", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    gn_path = src / BUILD_GN
    if not gn_path.is_file():
        print(f"ERRO: {gn_path} não existe", file=sys.stderr)
        return 1

    text = gn_path.read_text(encoding="utf-8")

    if "Halla: CREL off" in text:
        print(f"{BUILD_GN}: patch já aplicado")
    else:
        patched, count = CREL_IF_RE.subn(REPLACEMENT, text)
        if count == 0:
            # fallback: ao menos a linha da flag tem que existir
            if "--allow-experimental-crel" in text:
                print(
                    f"ERRO: flag CREL presente em {BUILD_GN} mas o bloco "
                    "if não casou com o padrão esperado — revisar o patch "
                    "contra a revisão nova do build config",
                    file=sys.stderr,
                )
            else:
                print(
                    f"ERRO: nem a flag --allow-experimental-crel foi "
                    f"encontrada em {BUILD_GN} — verificar revisão do "
                    "build config (CREL pode ter virado default do clang)",
                    file=sys.stderr,
                )
            return 1
        if count > 1:
            print(f"AVISO: {count} ocorrências substituídas (esperado 1)")
        gn_path.write_text(patched, encoding="utf-8")
        print(f"{BUILD_GN}: CREL desligado ({count} bloco)")

    # Varredura defensiva: qualquer outro --crel ativo no build config
    # (build/**/*.gn|gni) é reportado — hoje só existe o do compiler.
    for candidate in src.glob("build/**/*.gn*"):
        try:
            body = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(body.splitlines(), 1):
            if "--crel" in line and not line.lstrip().startswith("#"):
                print(
                    f"AVISO: outro --crel ativo em {candidate}:{lineno}: "
                    f"{line.strip()}",
                    file=sys.stderr,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
