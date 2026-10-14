# vban

`vban` provides command-line senders and receivers for VBAN audio and text
streams over UDP.  This archive currently contains version `g20201011` for
HarmonyOS PC.

## HarmonyOS PC adaptation

The port builds and installs `vban_emitter`, `vban_receptor`, and
`vban_sendtext`.  It uses Conan CMake targets for the upstream audio backends,
honours `TMPDIR` for named pipes, treats a zero-length file/pipe read as EOF,
and validates the byte-oriented VBAN wire header.  Consumer tests exercise the
packaged commands over loopback UDP without requiring a physical sound device.

## Dependencies

- `alsa-lib/1.2.16.1`
- `pulseaudio/17.0.1`
- `jack/1.9.22`

## References

- Upstream project: <https://github.com/quiniouben/vban>
- VBAN protocol overview: <https://vb-audio.com/Voicemeeter/vban.htm>
