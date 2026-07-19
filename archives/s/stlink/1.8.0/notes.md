# stlink 1.8.0 adaptation notes

## Source

- URL: `https://github.com/stlink-org/stlink/archive/refs/tags/v1.8.0.tar.gz`
- SHA-256: `cff760b5c212c2cc480f705b9ca7f3828d6b9c267950c6a547002cd0a1f5f6ac`

## Package

- Build system: CMake through Conan 2
- Package type: application with a static `libstlink`
- Executables: `st-flash`, `st-info`, and `st-util`
- Dependency: `libusb/1.0.27`

The software-level `commands.json` declares `stlink/1.8.0` as a tool package.
`package_info()` exports the three executables, the `bin` directory, the
`stlink::stlink` CMake target, and the transitive libusb dependency.

## HarmonyOS adaptation

The recipe reuses the seven upstream-source patches already validated by the
`1.8.0-r1` archive. They address portable headers and integer-width warnings in
the CMake flags, gdb server, chip database, flash loader, mapped files, and USB
backend. No patch modifies recipe metadata or test_package files.

## Consumer test

The test package keeps `self.requires(self.tested_reference_str)`, compiles a C
consumer against `stlink::stlink`, calls `stlink_open_usb()` and closes an
optional device, then runs `st-info --version`. No physical probe is required.

<!-- ARCHIVE-CLOSED -->
