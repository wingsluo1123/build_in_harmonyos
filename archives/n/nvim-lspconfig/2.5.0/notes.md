# nvim-lspconfig 2.5.0

## Summary

This is a Neovim Lua runtime plugin. The recipe downloads the official GitHub
tag and packages `lua/`, `lsp/`, `plugin/`, `doc/`, upstream `test/`,
`README.md`, and `LICENSE.md` under `share/nvim-lspconfig`.

## Tests

Upstream ships a Vusted test suite:

- `make test` -> `vusted ./test`
- `test/lspconfig_spec.lua` contains 9 spec cases covering `root_pattern`,
  archive-subpath stripping, user-command option parsing, available-server
  filtering, setup hooks, and config normalization.

The OHOS runner used here does not provide `nvim` or `vusted`. The local
`test_package` therefore checks that upstream `lsp/` and `test/` are packaged
and executes Python assertions against the same upstream spec fixtures and
behavior inputs.

## OHOS notes

No native code is compiled. Runtime use still requires a target Neovim
installation and language server binaries outside this package.

## New Port Validation

Date: 2026-07-31

Validated on the new OHOS device port `33332` with isolated job
`nvim-lspconfig-2.5.0-upstreamtests-r1`.

- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-2.5.0-nvim-lspconfig-2.5.0-upstreamtests-r1-conan-20260731-201209-60932`
- Command:
  `zsh ci/conan/build_and_test.sh archives/n/nvim-lspconfig/2.5.0`
- Lock wait: 1251 seconds
- Result: `Build Summary` success, 1 package built, 0 failed
- Full package reference:
  `nvim-lspconfig/2.5.0#3f006260fd93db5f07869ea1861f8cb8:fc3eeb021243959114a0318489539cad6d087e28#cb1f15ff469b7765c6ec36c6cfe3fdf3`
- Gate summary:
  `L0=pass`, `L1=pass(test_package executed)`, `L2=skip(no bin/ dir)`,
  `L4=pass(no patches)`, `L5=warn(no bin/lib artifacts; share-only plugin)`
- Test evidence: `test_package` ran
  `test_nvim_lspconfig.py` and printed
  `nvim-lspconfig upstream spec cases and runtime files are packaged`.
