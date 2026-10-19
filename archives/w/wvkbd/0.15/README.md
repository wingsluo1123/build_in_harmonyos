# wvkbd 0.15 for HarmonyOS PC

This archive builds the wvkbd keyboard core for AArch64 OHOS and packages a
HarmonyOS Stage input method extension. It follows the system IME lifecycle,
renders the keyboard with ArkUI, and routes key events to the active input
client through IMEKit.

## Contents

- `harmonyos/core/`: portable C keyboard layout and modifier state
- `harmonyos/ime_app/`: system input method HAP source and NAPI adapter
- `test_package/`: Conan consumer, C cases, test HAP, and HDC device runner
- `manifest.yaml`: version metadata
- `notes.md`: build and adaptation record
- `PORTING_REPORT.md`: final validation evidence
- `PR_DESCRIPTION.md`: contest review description based on the repository template

Build with Conan using an OHOS AArch64 host profile. The HAP project declares
DevEco's compile SDK separately from its HarmonyOS 6.1 compatibility and target
versions. `test_package/README-harmonyos-device.md` documents local SDK and
signing configuration; signing files and generated HAPs stay outside Git.
