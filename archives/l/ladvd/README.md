# ladvd

`ladvd` is a link-layer discovery daemon and query client supporting LLDP,
CDP, EDP, FDP and NDP. This archive contains the HarmonyOS PC adaptation of
version `1.1.2`.

## HarmonyOS PC adaptation

- Treat the canonical `linux-ohos` target as the upstream Linux networking
  backend while retaining upstream protocol behavior.
- Reuse host-generated Autotools files because native `autoreconf` cannot
  reliably operate on the HarmonyOS storage filesystem.
- Preserve assignments that upstream placed inside `assert()` expressions so
  Release (`NDEBUG`) builds still validate packets and obtain raw sockets.
- Run all seven upstream Check executables (45 cases) on the target with a
  private writable temporary directory, then test the two installed commands.
- Make nested Check helper processes terminate normally after the parent sends
  SIGTERM, while explicitly rejecting a failed `fork()`.
- Keep the upstream logging oracle stable across Check's `START_TEST` macro
  implementation change by deriving the active function name from `__func__`;
  this is documented as draft knowledge E14861 with a versioned three-arm
  comparison.
- Sign the target test executables and packaged daemon and verify that each
  resulting ELF contains exactly one `.codesign` section.

## Dependencies

- `libevent/2.1.13`
- `libpcap/1.10.6`
- `check/0.15.2` (test only)

## References

- Upstream project: <https://github.com/sspans/ladvd>
- Release source: <https://github.com/sspans/ladvd/releases/tag/v1.1.2>
