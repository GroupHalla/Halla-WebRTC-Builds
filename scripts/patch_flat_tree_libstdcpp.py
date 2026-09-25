#!/usr/bin/env python3
"""Patch do rtc_base/containers/flat_tree.h para libstdc++ 12 (Ubuntu 22.04).

O flat_tree suporta lookup heterogêneo (find/lower_bound com K != key_type)
chamando o comparador transparente (std::less<void>) com uma chave do tipo
exato e um tipo de lookup diferente. Isso só compila quando os dois tipos
têm operator< util; para std::pair heterogêneos (ex.: pair<string,bool> vs
pair<string_view,bool> no call/payload_type_picker.cc) isso depende do
operator<=> heterogêneo de pair, que existe no libstdc++ >= 13, no libc++ e
no MSVC STL — mas NÃO no libstdc++ 12 do ubuntu-22.04 que o SDK usa.

O patch dá ao KeyValueCompare um fallback que sintetiza a ordem
lexicográfica elemento a elemento (a mesma semântica de operator< de pair)
quando o comparador não aceita os dois tipos. Quando aceita (libstdc++ 13+,
libc++, MSVC), o caminho original é usado sem mudança.
"""

import sys
from pathlib import Path

HELPER_ANCHOR = """// The use of "value" in this is like std::map uses, meaning it's the thing
// contained (in the case of map it's a <Kay, Mapped> pair). The Key is how
// things are looked up. In the case of a set, Key == Value. In the case of
// a map, the Key is a component of a Value."""

HELPER = """// HALLA PATCH (SDK linux-x64 com libstdc++ do Ubuntu 22.04): o lookup
// heterogêneo de flat_tree compara a chave armazenada com um tipo de lookup
// diferente através do comparador transparente. Para std::pair heterogêneos
// isso exige operator<=> de pair com 4 parâmetros de template — presente no
// libstdc++ >= 13, libc++ e MSVC STL, ausente no libstdc++ 12. Quando o
// comparador não aceita a combinação, sintetiza a ordem lexicográfica
// elemento a elemento (a mesma semântica de operator< de pair).
template <typename Comp, typename A, typename B>
bool CompareMaybeHeterogeneous(const Comp& comp, const A& a, const B& b) {
  if constexpr (requires { comp(a, b); }) {
    return comp(a, b);
  } else if constexpr (requires { bool(a < b); }) {
    return a < b;
  } else {
    if (a.first < b.first) return true;
    if (b.first < a.first) return false;
    return a.second < b.second;
  }
}

"""

CALL_OLD = """    template <typename T, typename U>
    bool operator()(const T& lhs, const U& rhs) const {
      return comp_(extract_if_value_type(lhs), extract_if_value_type(rhs));
    }"""

CALL_NEW = """    template <typename T, typename U>
    bool operator()(const T& lhs, const U& rhs) const {
      // HALLA PATCH: ver CompareMaybeHeterogeneous acima.
      return CompareMaybeHeterogeneous(
          comp_, extract_if_value_type(lhs), extract_if_value_type(rhs));
    }"""


def main() -> int:
    if len(sys.argv) != 2:
        print(f"uso: {sys.argv[0]} <webrtc-checkout>/src", file=sys.stderr)
        return 2
    header = Path(sys.argv[1]) / "rtc_base" / "containers" / "flat_tree.h"
    text = header.read_text(encoding="utf-8")

    if "CompareMaybeHeterogeneous" in text:
        print("flat_tree.h: patch já aplicado")
        return 0
    if HELPER_ANCHOR not in text or CALL_OLD not in text:
        print("flat_tree.h: âncoras do patch não encontradas — revisão "
              "do libwebrtc mudou?", file=sys.stderr)
        return 1

    text = text.replace(HELPER_ANCHOR, HELPER + HELPER_ANCHOR, 1)
    text = text.replace(CALL_OLD, CALL_NEW, 1)
    header.write_text(text, encoding="utf-8")
    print("flat_tree.h: CompareMaybeHeterogeneous injetado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
