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
- Installs `bin/busted` to `bin/busted`
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

Penlight also requires `luafilesystem/1.8.0-1` for `pl.dir`, which Busted
loads through `busted.modules.test_file_loader`.

## Upstream tests

The upstream tarball includes a Busted self-test suite under `spec/`. Full
execution is pending the OHOS new-port validation run after all test-runner
dependencies are available in the same isolated Conan home.

## Validation plan

The test package requires `lua/5.4.8`, builds a small C program against
`liblua.a`, explicitly composes `LUA_PATH` and `LUA_CPATH` across all Lua
dependencies, and loads Busted core modules to verify version metadata and
dependency resolution.

## Validation results

- Pending OHOS new-port validation

