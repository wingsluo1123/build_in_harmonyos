# wvkbd

`wvkbd` is a lightweight virtual keyboard. The upstream 0.15 program is a
Wayland client; this archive ports its keyboard behavior to a HarmonyOS PC
system input method extension.

## HarmonyOS port

- Version: [0.15](0.15/README.md)
- Product source: `0.15/harmonyos/ime_app/`
- Conan recipe: `0.15/conanfile.py`
- Device acceptance harness: `0.15/test_package/run_harmonyos_device_test.py`
- Porting report and test evidence: `0.15/PORTING_REPORT.md`
- Knowledge fallback draft: `knowledge/drafts/E429-draft-D7A3.md`

The HarmonyOS app uses the system IME extension API and ArkUI. A small C core
preserves the upstream keyboard layout and modifier behavior; it does not
embed the upstream Wayland display or virtual-keyboard transport.
