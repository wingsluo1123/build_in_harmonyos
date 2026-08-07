# Adaptation Notes - iftop 1.0_pre4

## Overview
iftop is a command-line network bandwidth monitoring tool that displays a table
of current bandwidth usage by host on a network interface. It uses libpcap for
packet capture and ncurses for its terminal (curses) interface.

- Official source: http://www.ex-parrot.com/pdw/iftop/
- Product: `iftop` executable (terminal tool — no shared library)
- Build system: autotools (configure + make)
- 类型: 【积分赛】(网络带宽监控工具)

## Source
The canonical source tarball is the official release from ex-parrot.com:
`https://www.ex-parrot.com/pdw/iftop/download/iftop-1.0pre4.tar.gz`

Note: the GitHub mirror `sqs/iftop` referenced in some docs does not exist
(HTTP 404). The official ex-parrot release tarball is used instead
(verified HTTP 200, 204665 bytes).

## Conan Recipe (1.0_pre4)
- Conan 2.x autotools recipe (`conan.tools.gnu.Autotools` / `AutotoolsToolchain`).
- `config_options`: on OHOS the `shared` option is removed (iftop is a
  standalone executable, never a shared library).
- `requirements`: declares `libpcap/1.10.6`; ncurses is supplied by the OHOS system prefix.
- `package_info`: `cpp_info.libs = []` (executable, not a linkable library);
  `bindirs = ["bin"]` exposes the installed `iftop` binary.
- The six previously verified r0 OHOS portability patches are applied by Conan.

## OHOS Adaptation
A full HarmonyOS (aarch64) build of iftop requires platform adaptation patches
that are tracked separately under `1.0_pre4-r0/patches/` (the build-records
revision). Key adaptations performed there:

1. `config.guess` / `config.sub`: add HarmonyOS (`linux-ohos`) detection.
   - `config.guess` (2012-12-29 vintage) has **no** trailing `echo "$GUESS"`
     collector, so the HarmonyOS branch must `echo` the triplet and `exit`
     directly; merely assigning a `GUESS` variable would fall through to the
     final `exit 1` ("unable to guess system type"). The upstream
     `timestamp=` line is left untouched.
   - `config.sub` needs **three** edits, not two: besides accepting
     `linux-ohos*` in `maybe_os` and in the `case $os` validation list, an
     explicit `-linux-ohos) os=-linux-ohos ;;` arm must be inserted *before*
     the generic `-linux*)` arm — otherwise that arm rewrites the OS via
     `sed 's|linux|linux-gnu|'` and yields `aarch64-unknown-linux-gnu-ohos`.
   - Verified: `config.sub aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`;
     `config.guess` on a HarmonyOS host → `aarch64-unknown-linux-ohos`.
     Because detection is now correct, the recipe no longer hardcodes
     `--build=aarch64-unknown-linux-gnu`.
2. `config/pthread.c` & `iftop.c`: `pthread_cancel` is unavailable under
   musl/OHOS — replaced with a flag + `pthread_join`, selected by the
   `HAVE_PTHREAD_CANCEL=0/1` feature macro that `generate()` probes and passes
   via `extra_defines` (no platform conditional macros in the sources, per R8).
   The guards use `#if !HAVE_PTHREAD_CANCEL` (value test) rather than
   `#ifndef`, because the macro is always defined by the toolchain.
3. `ui_common.h` / `ui_common.c`: move global variable definitions out of the
   header (extern declaration + definition in the .c) to avoid duplicate
   definition errors.

These patches have been verified to produce a working `iftop` binary on OHOS.

## Dependencies
- libpcap (packet capture) — Conan recipe `libpcap/1.10.6`.
- ncurses (terminal UI, wide-char `ncursesw`) — system prebuilt 6.5.

## Verification
The existing OHOS build (1.0_pre4-r0) confirmed a working binary:
```
$ iftop --version
iftop: unknown option --
iftop: display bandwidth usage on an interface by host
...
iftop, version 1.0pre4
```
(`--version` is not a recognized flag; iftop prints usage and exits non-zero.)

---

**编译结束**: 2026-07-15
**最终状态**: built
