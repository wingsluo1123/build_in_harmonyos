# wvkbd HarmonyOS system input method

This Stage project registers `InputMethodService` as an `inputMethod` extension.
It targets HarmonyOS 6.1 / API 23. The checked build used the installed DevEco
Studio 26 SDK; the code uses the public API 23 `InputClient` interface.

## Build

1. Build/install `wvkbd/0.15` with an OHOS aarch64 Conan profile, then generate
   `CMakeDeps` for that same package and the chosen HAP build type. The native
   target must resolve `wvkbd::core`; no source-tree fallback is provided.
2. Set `WVKBD_CONAN_GENERATORS` to that CMakeDeps directory. Set
   `DEVECO_STUDIO_HOME` to the installed DevEco Studio directory and
   `DEVECO_SDK_HOME` to its `sdk` directory. Add the bundled Node executable to
   PATH. Run `ohpm install` in the app project so the local native declaration
   package is available to ArkTS.
3. Run `hvigorw.bat assembleHap --mode module -p product=default
   -p buildMode=release --no-daemon`. Match the Conan build type to the HAP mode.
   The source profile intentionally has no signing configuration; sign the
   output locally through DevEco Studio using a profile for this bundle and
   device. Keep all keys, certificates and provisioning profiles outside Git.
4. Enable and select wvkbd in the system input method settings. Focus an editor
   in another app. The system starts the extension and displays its panel.

Use a clean source checkout when exporting the Conan package. Hvigor build
outputs, SDK paths, dependency caches and signing material are machine-local.
`test_package/tests/test_ime_project.py` checks project registration only; it
does not establish input behavior. The device runner verifies real editor input.

## Behavior

The UI enumerates the core's six-row layout and UTF-8 labels. Shift is one-shot;
Caps Lock persists within a session; starting/stopping input resets both.
Text and Backspace use the active public `InputClient`; Enter forwards the
editor's `enterKeyType` to `sendKeyFunction`. Hide calls the public keyboard
controller. Operations are serialized and bound to their originating session.
No entered text or client attributes are logged. Lifecycle messages contain
only a generated process run ID, session number and event name. They are
observable with the `wvkbd` log tag and support start/stop/panel verification.

The HAP contains the GPL-3.0-only adapted wvkbd core. Full upstream attribution
and license are in the companion Conan package and core source directory.
