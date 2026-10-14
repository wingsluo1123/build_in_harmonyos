# vile

vile is a vi-like text editor with Emacs-style multiple buffers and windows.
This package builds the terminal `vile` executable and its syntax filters.

## HarmonyOS adaptation

- The upstream `config.sub` already accepts `aarch64-unknown-linux-ohos`.
- The build uses the wide-character ncurses driver and the Conan `ncurses/6.6` dependency.
- The packaged executable is validated with a HarmonyOS ABI checker and runtime smoke tests.

## Dependencies

- `ncurses/6.6` for terminal handling and wide-character support
- `flex/2.6.4` at build time for syntax-filter generation

## References

- Homepage: https://invisible-island.net/vile/
- Source: https://invisible-island.net/archives/vile/current/vile-9.8za.tgz
