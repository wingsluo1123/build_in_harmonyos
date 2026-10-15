# libretro 20260530.083400.g8926b0c6c347 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4
- Conan 2.29.1

## Verification

- `conan-verify libretro 20260530.083400.g8926b0c6c347`: exit 0 (G0-G4 PASS)
- `CI_PACKAGES="archives/l/libretro/20260530.083400.g8926b0c6c347" zsh ci/conan/build_and_test.sh`: exit 0
- L0: passed
- L1: passed
- L1e R34 negative test: passed
- L2: skipped (no bin/ dir)
- L4: passed
- L5: passed

## test_package

Two consumer-style L1 tests:

1. **test.c** — consumer smoke: dlopen yabause_libretro.so, call retro_api_version/retro_get_system_info
   - consumer ok: library_name=Yabause library_version=v0.9.15 valid_extensions=cue|iso|mds|ccd|zip|chd|m3u retro_api_version=1

2. **test_ohos.c** — HarmonyOS-specific (assertion-free, if+return style):
   - ABI closure — dlsym all 25 mandatory retro_* entry points
   - Frontend wiring — set_environment/set_video_refresh/set_audio_sample(_batch)/set_input_poll/set_input_state/set_controller_port_device
   - OHOS runtime lifecycle — retro_init -> retro_get_system_info -> retro_deinit
   - ohos lifecycle ok: 25/25 mandatory retro_* symbols resolved

- Test cases: 2
- Passed: 2
- Failed: 0
- Skipped: 0

## Upstream tests

Per R51 three-step method (enumeration → real execution → honest backfill):

- 5 vendored libretro-common unit test programs (libcheck framework), 127 total checks
- 126 pass / 1 fail (test_word_wrap — upstream vendored snapshot stale expectation, platform-independent; verified upstream master produces identical output)
- 0 errors / 0 skipped
- Evidence: builds/libretro-upstream-test-rerun.log

## Result

The recipe was verified on an OpenHarmony aarch64 device and is eligible for published status.
