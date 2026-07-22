# lua/5.4.7 — OpenHarmony PC (aarch64) Migration

## Summary

Port Lua 5.4.7 to OpenHarmony PC as a Conan recipe at `@ohpcd/stable`. This
unblocks the INSTEAD Engine 3.5.2 migration (which requires lua) and any
other downstream that embeds Lua on OHOS.

## Build / Package

| Stage | Result |
|---|---|
| Build system | Makefile (upstream `linux` target) |
| Toolchain | clang 15 from hnp, bionic libc (aarch64) |
| Output | `liblua.a` (static, per R26), `bin/lua`, `bin/luac`, public headers |
| Patches | none (no upstream source mods — bionic is Linux-compatible) |

### Notable workarounds

1. **Lua's Makefile hardcodes `CC= gcc -std=gnu99`** at line 7 of
   `src/Makefile`. Makefile-defined variables override environment
   variables, so `export CC=clang` is ineffective. We pass
   `CC='clang -std=gnu99'` on the make command line (in `build()`),
   which is the only path that beats Makefile's command-line
   definitions.

2. **`make -j$(nproc)` fails on HMDFS** because the make jobserver
   tries to `mkfifo` in CWD. We pin `-j1`.

3. **Headers stripped of `src/` prefix**: Upstream tarball has Lua's
   public headers (`lua.h`, `luaconf.h`, `lualib.h`, `lauxlib.h`) at the
   top level — but our `strip_root=True` extraction drops them under
   `<src>/`. The `package()` step flattens them to `<pkg>/include/`
   with `keep_path=False`. Private headers (`ldo.h`, `lvm.h`, ...) are
   intentionally not exported.

4. **`cpp_info.bindirs = ["bin"]` advertised**: Required so downstream
   test_packages (e.g. INSTEAD's) can find `lua` / `luac` on PATH via
   VirtualRunEnv.

## G2 (conan create) — PASS

```
lua/5.4.7@ohpcd/stable: Package '9c916678...' built
lua/5.4.7@ohpcd/stable: Packaged 27 '.h' files
lua/5.4.7@ohpcd/stable: Packaged 1 '.a' file: liblua.a
lua/5.4.7@ohpcd/stable: Packaged 2 files: lua, luac
```

## R34 — test_package

Six assertions, all pass:

1. ✅ `lua` binary present at `<pkg>/bin/lua`
2. ✅ `luac` binary present at `<pkg>/bin/luac`
3. ✅ `liblua.a` present at `<pkg>/lib/liblua.a`
4. ✅ `lua -v` reports `Lua 5.4.7`
5. ✅ `luac -v` reports `Lua 5.4.7`
6. ✅ C API smoke: `luaL_newstate` → `lua_pushinteger(42)` →
   `luaL_dostring("return 6*7")` → `lua_close()` round-trips successfully

The test_package drives `lua -v` / `luac -v` and links a tiny C driver
against `liblua.a` to verify the embedded interpreter API surface
(`lua_State` allocation, stack push, VM eval) on OHOS.

## Rules Compliance

| Rule | Status | Note |
|---|---|---|
| R6 (patches only modify sources) | ✅ N/A | no patches |
| R26 (system same-name static-only) | ✅ | static `liblua.a`, no .so |
| R34 (test_package real API) | ✅ | C API smoke + `lua -v` |
| R36 (deps first) | ✅ | no deps (Lua is standalone) |

## Knowledge-graph Notes

- **E001** (`cc` symlink): N/A — Lua's Makefile hardcodes `gcc`, not
  `cc`, and we bypass via command-line `CC=clang`.
- **HMDFS jobserver mkfifo**: HMDFS rejects `mkfifo(2)`, which makes
  `make -j>1` fail. Pin `-j1`.

## Files

```
archives/l/lua/5.4.7/
├── conanfile.py          # Makefile build, static-only, bindirs exported
├── conandata.yml         # sources + empty patches
├── manifest.yaml         # no deps
├── notes.md              # exploration notes
├── PR.md                 # this file
├── test_package/
│   ├── conanfile.py      # VirtualRunEnv + pkg_folder absolute path
│   ├── test.sh           # 6 R34 assertions
│   └── MANIFEST.yml
└── reports/
    ├── conan-create.log
    └── conan-verify-report.md
```