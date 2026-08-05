# vusted 2.5.3-1 adaptation notes

## Scope

This package adds Vusted 2.5.3-1 as the Neovim-backed Busted wrapper needed by
the nvim-lspconfig Path B validation chain.

## Source

- Upstream repository: https://github.com/notomo/vusted
- Source archive: https://github.com/notomo/vusted/archive/refs/tags/v2.5.3.tar.gz
- Mirror: https://gh-proxy.com/https://github.com/notomo/vusted/archive/refs/tags/v2.5.3.tar.gz
- SHA256: b7e15560ecc822fe5da5dfa8229ea1e30895f3c28c79e16c694f57f43416ba42
- LuaRocks release: 2.5.3-1

## Package layout

- Installs `bin/vusted` and `bin/vusted_entry.vim`
- Installs `lua/vusted/*.lua` to `share/lua/5.4/vusted/`
- Installs `lua/busted/outputHandlers/vusted/default.lua` to
  `share/lua/5.4/busted/outputHandlers/vusted/default.lua`
- Copies the MIT license to `licenses/LICENSE`

## Local adaptation

Upstream `vusted_entry.vim` assumes a LuaRocks deployment and shells out to
`luarocks config` to locate Lua module directories. The Conan package patches
the entry script to append `LUA_PATH` and `LUA_CPATH` from the environment
instead. `vusted --version` is also patched to print `2.5.3` directly rather
than shelling out to `luarocks show`.

## Upstream tests

The upstream test suite contains 24 `it(...)` cases under `spec/lua/vusted` by
static count. Full execution requires packaged `nvim` and is pending OHOS
validation.

## Validation plan

The test package will require `neovim/0.11.3`, compose `LUA_PATH` and
`LUA_CPATH` across Vusted, Busted, and all Lua dependencies, and run a minimal
Vusted spec with packaged `nvim --headless`.

## Validation results

- Pending OHOS new-port validation

