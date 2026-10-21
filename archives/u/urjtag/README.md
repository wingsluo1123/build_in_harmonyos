# urjtag

Universal JTAG library, server and tools — a JTAG debugging / flash
programming tool set (descendant of the OpenWince JTAG tools).

- Upstream: http://urjtag.org (project files now hosted on SourceForge)
- License: GPL-2.0-or-later
- Language: pure C (188 `.c` / 91 `.h` in the release tarball)

## Artifacts

- `liburjtag.a` — the embeddable Universal JTAG library (static; the
  bundled libtool cannot build shared libraries for the `ohos` host_os)
- `jtag` — interactive command-line client (statically linked against
  liburjtag; USB cable support via libusb, command history via readline)
- `bsdl2jtag` — BSDL-to-JTAG-script converter
- flash part database under `share/urjtag/` (MANUFACTURERS, altera/..., ...)

## OHOS (HarmonyOS PC, aarch64) adaptation

See `2021.03/notes.md` and `2021.03/manifest.yaml`.
