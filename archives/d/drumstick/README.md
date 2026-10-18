# Drumstick MIDI libraries

Drumstick is a set of MIDI C++ libraries using Qt idioms and style, and a C++
wrapper around the ALSA sequencer interface.

Libraries:

- **Drumstick::ALSA** — Linux/HarmonyOS-only C++/Qt wrapper around the ALSA
  Sequencer API (required by kmetronome).
- **Drumstick::File** — multiplatform SMF (.mid/.kar), RIFF RMID (.rmi) and
  Cakewalk (.wrk) file I/O.
- **Drumstick::RT** — realtime MIDI I/O library with pluggable backends
  (ALSA, Network, OSS).
- **Drumstick::Widgets** — MIDI widgets including a virtual piano keyboard.

## Versions

- `2.11.1`: latest upstream stable (tag `RELEASE_2_11_1`), adapted for
  HarmonyOS PC. Qt6 + ALSA only; optional backends disabled.

## Upstream

- Project: https://drumstick.sourceforge.io
- Source: https://github.com/pedrolcl/drumstick
- License: GPL-3.0-or-later
