# busted 2.2.0-1 adaptation notes

## Scope

This package adds LunarModules Busted 2.2.0-1 as the Lua test framework needed
by Vusted and the nvim-lspconfig Path B validation chain.

## Source

- Upstream repository: https://github.com/lunarmodules/busted
- Source archive: https://github.com/lunarmodules/busted/archive/refs/tags/v2.2.0.tar.gz
- Mirror: https://gh-proxy.com/https://github.com/lunarmodules/busted/archive/refs/tags/v2.2.0.tar.gz
- SHA256: befca10f573bb476fa1db2e3149150d65f802a71d34d1682679e640665f2dc2b
- LuaRocks release: 2.2.0-1

## Package layout

- Installs `busted.lua` to `share/lua/5.4/busted.lua`
- Installs the `busted/` module tree to `share/lua/5.4/busted/`
- Installs upstream `bin/busted` to `bin/busted.lua`
- Installs a native `bin/busted` launcher linked against packaged Lua
- Copies the MIT license to `licenses/LICENSE`

## Dependency notes

Busted 2.2.0-1 depends on the following Lua packages in this Path B chain:

- `lua_cliargs/3.0.2-1`
- `luasystem/0.6.3-1`
- `dkjson/2.8-1`
- `lua-say/1.4.1-3`
- `luassert/1.9.0-1`
- `lua-term/0.7`
- `lua-penlight/1.15.0`
- `mediator_lua/1.1.2-0`
- `luacov/0.16.0-1`

Penlight also requires `luafilesystem/1.8.0-1` for `pl.dir`, which Busted
loads through `busted.modules.test_file_loader`.

LuaCov also requires `datafile/0.11-1`. Lua CLIArgs requires `inifile/1.1-1`
for `config_loader.from_ini`.

## Upstream tests

The upstream tarball includes a Busted self-test suite under `spec/`. Full
execution passed on the OHOS new-port validation run after all test-runner
dependencies were available in the same isolated Conan home.

- Run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-upstream-specs-r7-20260807-051047-37947`
- Result: `1670 successes / 0 failures / 0 errors / 7 pending`
- Pending cases are upstream-declared pending items for async token callbacks,
  `__gc` error output, Moonscript, and LuaJIT FFI paths.

## Validation plan

The test package requires `lua/5.4.8.1`, builds a small C program against
`liblua.a`, explicitly composes `LUA_PATH` and `LUA_CPATH` across all Lua
dependencies, and loads Busted core modules to verify version metadata and
dependency resolution. It also executes packaged `bin/busted --version`.

## Validation results

- OHOS new-port build/test_package run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-luacov-chain-r6-20260807-050905-36912`
- Full ref: `busted/2.2.0-1#747ec4218b8d00828e522134b862ea34:4df0932bd77659124e53ec83e89473d223e318ac#b8bed9a5b8de4351581b2fcf35ec39b6`
- Test output: `busted smoke ok`, `2.2.0`
- Gates: L0 pass, L1 pass, L2 skip-nonblocking, L4 pass, L5 pass
- Upstream run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-upstream-specs-r7-20260807-051047-37947`
- Upstream result: `1670 successes / 0 failures / 0 errors / 7 pending`

