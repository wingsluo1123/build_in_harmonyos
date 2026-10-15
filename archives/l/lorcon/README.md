# lorcon

lorcon (Loss Of Radio CONtrol) is a generic library for injecting 802.11
frames, with packet forge (`lcpf_*`) and packet assembly (`lcpa_*`)
helpers plus channel utilities.

## Versions

| Version | Status | Date | Patches | Artifacts |
|---------|--------|------|---------|-----------|
| 2020.06.06 | built | 2026-10-14 | 0 | liborcon2 + bundled libpcap |

## OHOS adaptation

- Build: autotools (`configure` + `Makefile.in`, libtool).
- Zero committed patches; build-time handling for HMDFS umask,
  vintage `config.sub`, and optional `linux/wireless.h`.
- No Conan-level libpcap requirement: the official libpcap 1.10.6 sources
  (same URL/SHA as published `archives/l/libpcap/1.10.6`) are built
  privately with an Autotools configure and the static archive ships in
  this package, so neither CI nor preflight enters the conancenter
  bison/flex/m4 chain; `libnl` stays optional.
- The worker has no flex/bison (both hard-required by libpcap's
  configure), so `vendor/pcap_gen/` commits the four generator outputs
  produced offline by real flex 2.6.4 + Bison 3.8.2 from this exact
  tag, replayed at build time through `vendor/tools/` shims
  (`LEX`/`BISON_BYACC`). Final `libpcap.a` equals a native build.
- Upstream has no automated test suite; see `2020.06.06/notes.md` and
  `2020.06.06/test_package/MANIFEST.yml` for the audit.

## References

- https://github.com/kismetwireless/lorcon
