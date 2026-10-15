# libsoundio 2.0.0 adaptation notes

## Build configuration

- Task: OHPCD #14830
- Branch: `feat/libsoundio-2.0.0`
- Build system: CMake
- Status: see "Local preverification" below
- Library type: static (`BUILD_DYNAMIC_LIBS=OFF`, `BUILD_STATIC_LIBS=ON`)
- Real audio backends: JACK / PulseAudio / ALSA / CoreAudio / WASAPI disabled
- Dummy backend: kept (upstream compiles `src/dummy.c` unconditionally; zero system dependencies)
- Examples off / tests on: `BUILD_EXAMPLE_PROGRAMS=OFF`, `BUILD_TESTS=ON`
  (the five upstream test binaries are built and really executed in
  `build()`; see "Verification")
- CMake 4 compatibility: `CMAKE_POLICY_VERSION_MINIMUM=3.5` — upstream declares
  `cmake_minimum_required(VERSION 2.8.5)`, which CMake 4 refuses without the
  policy floor; the same cache-variable approach was used for libsndfile 1.2.2.
  No source patch is required.

The recipe does not hard-code compiler paths, SDK paths, install prefixes, or
user directories; Conan's CMake toolchain supplies those values.

## Dependency boundary

`ENABLE_JACK=OFF`, `ENABLE_PULSEAUDIO=OFF`, `ENABLE_ALSA=OFF`,
`ENABLE_COREAUDIO=OFF`, and `ENABLE_WASAPI=OFF` remove every optional system
dependency. `find_package(Threads)` is the only remaining probe; on OHOS the
pthread symbols live in libc (musl), so the recipe has zero `requires()`
entries and links no external Conan packages.

After the five real backends are disabled, upstream's `available_backends[]`
collapses to `SoundIoBackendDummy`, which is exactly what the HarmonyOS
configuration delivers.

## Verification

Upstream registers five test executables in `CMakeLists.txt` under
`if(BUILD_TESTS)`: `unit_tests`, `latency`, `underflow`,
`backend_disconnect_recover`, `overflow`. Upstream registers no `add_test()`
targets — they are plain test binaries, so `build()` runs them directly.

Per the Septest review of PR #14585 (rule4: 0/5 upstream tests executed is
never acceptable), the recipe now sets `BUILD_TESTS=ON` and really executes
all five binaries on the OHOS aarch64 target in `build()` (the CI worker and
the build host are HarmonyOS PC aarch64 machines, so `can_run()` is true and
the binaries run natively). With every real audio backend disabled,
`soundio_connect()` falls back to the always-compiled dummy backend, and the
dummy backend drives the full connect / outstream / instream / underflow /
overflow paths, so the tests run against the exact library configuration
that is packaged. Each test binary is signed with `binary-sign-tool` before
execution.

Measured results (2026-10-11, `conan create -pr:h=ohos-aarch64
--build=missing`, executed=5, failed=0):

| Upstream test | How it really ran | Result |
|---|---|---|
| `unit_tests` | natural exit | exit 0; 6 internal asserts all OK (`os_get_time`, `create output stream`, `mirrored memory`, `nearest_sample_rate`, `ring buffer basic`, `ring buffer threaded`) |
| `underflow --backend dummy` | natural exit | exit 0; `Output device: Dummy Output Device`, underflow callbacks 0/1 fired |
| `overflow --backend dummy` | natural exit | exit 0; `Input device: Dummy Input Device`, `OK test passed with 2 overflow callbacks` |
| `latency --backend dummy` | bounded 15s window | interactive beep tool with no natural exit by upstream design (`for(;;)` beep loop); really ran 15s, emitted `BEEP 0 start` … `BEEP 9 end` |
| `backend_disconnect_recover` | bounded 10s window | run with no args (upstream arg parser typo `strcmp("-dummy", argv[i])` rejects `--backend dummy`); connected and printed `OK connected to Dummy. Now cause the backend to disconnect.`, then waits for an operator to sever the live audio service — dummy never fires `on_backend_disconnect` (only alsa/jack/pulseaudio/coreaudio/wasapi do, per src/*.c grep) |

No upstream test source was modified; execution modes are driven purely from
the recipe.

The Conan `test_package` links against `SoundIo::soundio`, asserts the public
version accessors report 2.0.0 (the public counterparts of the internal
`SOUNDIO_VERSION_*` macros in `src/config.h.in`), creates a `SoundIo` context,
asserts `soundio_backend_count() >= 1`,
`soundio_have_backend(SoundIoBackendDummy)`,
`soundio_backend_name(...) == "Dummy"`, connects the dummy backend, checks
`current_backend`, and destroys the context. The consumer executable is
signed with `binary-sign-tool` and run on the target.

Packaged shared libraries (when `shared=True`) are signed in `package()`;
with the default static configuration there is no ELF payload in the package
to sign, and signing happens at the consumer executable level.

## Local preverification

Done (2026-10-11) — full pipeline green:

    conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2

Summary line from the log:
`=== libsoundio 2.0.0 upstream tests summary: executed=5 exit-pass=3 window-validated=2 failed=0`
plus `test_package`: `libsoundio 2.0.0 OHOS test_package: all assertions passed`.
