# Final forced-build evidence

## Reproduction command

```sh
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build='sdl12-compat/1.2.68@ohpcd/stable'
```

The complete unmodified stdout/stderr is committed as `evidence/final-conan-create.log`. It contains 691 lines (46,389 bytes) and has SHA256:

```text
87543e5d4584a8f99d32e7501cbd4330e017fa0f50b0ebe84df6255bbb81e7bf
```

The framework-generated `reports/conan-create.log` is ignored and belongs to an earlier verification run; it is not evidence for this final revision. The excerpts below are readability aids and intentionally normalize long paths; the committed `.log` file is the byte-exact raw record. `evidence/l5-raw-evidence.md` records the corresponding final package inspection.

## Verbatim identity and dependency excerpt

```text
sdl12-compat/1.2.68@ohpcd/stable: Copied 1 '.txt' file: SDL2-LICENSE.txt
sdl12-compat/1.2.68@ohpcd/stable: Exported: sdl12-compat/1.2.68@ohpcd/stable#4e019b9fc09df67215d2d2ac33647eab (2026-08-15 09:26:07 UTC)
sdl12-compat/1.2.68@ohpcd/stable: Forced build from source
    sdl12-compat/1.2.68@ohpcd/stable#4e019b9fc09df67215d2d2ac33647eab:92219b911295cbf30b8c778a4da3b51506c9d757 - Build
    sdl2/2.30.10#9a6fd1dbbc0ac1eef2a42639df48e3b4:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#96027f33d6086703ce6fe4e4502533b3 - Cache
```

## Verbatim SDL2 relink excerpt

```text
sdl12-compat/1.2.68@ohpcd/stable: RUN: /data/service/hnp/bin/clang -shared -Wl,-z,defs -Wl,-soname,libSDL2-2.0.so.0 -Wl,--whole-archive /storage/Users/currentUser/.conan2/p/sdl25504c61a83af3/p/lib/libSDL2.a -Wl,--no-whole-archive -lm -ldl -lpthread -o /storage/Users/currentUser/.conan2/p/b/sdl122d4424ee6c2cc/b/build/Release/libSDL2-2.0.so.0
```

## Verbatim upstream-test excerpt

```text
sdl12-compat/1.2.68@ohpcd/stable: RUN: <build>/testver
Compiled version: 1.2.68
Linked version: 1.2.68
sdl12-compat/1.2.68@ohpcd/stable: RUN: <build>/testplatform
All data types are the expected size.
Detected a little endian machine.
sdl12-compat/1.2.68@ohpcd/stable: RUN: <build>/testerror
Child thread error string: Thread #1 (...) had a problem: nevermind
Main thread error string: No worries
sdl12-compat/1.2.68@ohpcd/stable: RUN: <build>/testiconv
UTF-8 decoder capability and stress test
THE END
```

`testiconv` explicitly describes itself as a smoke/stress display program rather than a pass/fail conformance test; the task documentation does not count it as a full conformance assertion.

## Verbatim package and consumer excerpt

```text
sdl12-compat/1.2.68@ohpcd/stable: package(): Packaged 2 '.txt' files: LICENSE.txt, SDL2-LICENSE.txt
sdl12-compat/1.2.68@ohpcd/stable: Created package revision add464ab86072d9d626c35518c8863c5
sdl12-compat/1.2.68@ohpcd/stable: Full package reference: sdl12-compat/1.2.68@ohpcd/stable#4e019b9fc09df67215d2d2ac33647eab:92219b911295cbf30b8c778a4da3b51506c9d757#add464ab86072d9d626c35518c8863c5
sdl12-compat/1.2.68@ohpcd/stable (test package): Running test()
sdl12-compat/1.2.68@ohpcd/stable (test package): RUN: ./test_sdl12_compat
sdl12-compat consumer test passed
```

The consumer receives the exact Conan package path in `EXPECTED_SDL2_PATH`. HarmonyOS exposes loaded files under an HMDFS alias, so the test matches the unchanged `.conan2/.../lib/libSDL2-2.0.so.0` relative suffix in `/proc/self/maps` rather than claiming inode identity across aliases.
