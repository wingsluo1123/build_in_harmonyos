# nvim-lspconfig 2.5.0

## Summary

This is a Neovim Lua runtime plugin. The recipe downloads the official GitHub
tag and packages `lua/`, `plugin/`, `doc/`, `README.md`, and `LICENSE.md` under
`share/nvim-lspconfig`.

## Tests

The local `test_package` checks that core Lua, plugin, help, and license files
exist in the installed package. It does not start Neovim, because an interactive
editor session is not required to verify this share-only package locally.

## OHOS notes

No native code is compiled. Runtime use still requires a target Neovim
installation and language server binaries outside this package.

## New Port Validation

Date: 2026-07-31

Validated on the new OHOS device port `33332` with isolated job
`nvim-lspconfig-2.5.0-newport-r1`.

- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-2.5.0-nvim-lspconfig-2.5.0-newport-r1-conan-20260731-174230-35628`
- Command:
  `zsh ci/conan/build_and_test.sh archives/n/nvim-lspconfig/2.5.0`
- Result: `Build Summary` success, 1 package built, 0 failed
- Full package reference:
  `nvim-lspconfig/2.5.0#0b521047a14375a4b873fbfe242ed13c:fc3eeb021243959114a0318489539cad6d087e28#9188daae0e498b7a9b9943b83ed3f58b`
- Gate summary:
  `L0=pass`, `L1=pass(test_package executed)`, `L2=skip(no bin/ dir)`,
  `L4=pass(no patches)`, `L5=warn(no bin/lib artifacts; share-only plugin)`
