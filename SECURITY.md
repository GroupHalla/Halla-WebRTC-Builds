# Supply-chain policy

Every SDK release is built from the exact commits in `WEBRTC_REVISION` and
`DEPOT_TOOLS_REVISION`. Release ZIPs include `VERSION.txt`, `MANIFEST.sha256`
and an SPDX SBOM, and are published with an external `.sha256` file.
Consumers must verify the checksum before extraction.
