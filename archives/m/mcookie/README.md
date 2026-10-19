# mcookie

mcookie generates a 128-bit hexadecimal "magic cookie" for use with xauth(1).
This package builds the `mcookie` command from the util-linux 2.42.2 source
release.

## OHOS adaptation

- Uses the util-linux Autotools build.
- Enables only `mcookie` (no libuuid needed; entropy via `getrandom()`/`/dev/urandom`).
- Applies the existing HarmonyOS `config.guess` detection patch.
- Avoids `/tmp` by using a build-folder temporary directory.

## Dependencies

No external Conan dependencies.

## References

- https://github.com/util-linux/util-linux
- https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/v2.42/
