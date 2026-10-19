# lcmaps-plugins-verify-proxy 1.5.13 - OHOS adaptation notes

## Delivered surface

- `lib/lcmaps/liblcmaps_verify_proxy.so`
- `lib/lcmaps/lcmaps_verify_proxy.mod`
- `bin/verify-proxy-tool`

## Platform changes

- `config.guess` and `config.sub` recognize the HarmonyOS `aarch64-unknown-linux-ohos` tuple.
- `configure` creates temporary directories with `chmod 755`; HMDFS does not preserve POSIX `0700` semantics reliably.
- The plugin is explicitly linked against `liblcmaps_without_gsi` and `libcrypto`, because an OHOS `dlopen()`ed DSO cannot rely on the host process to supply those symbols. This does not assume that OpenSSL is a shared library.
- The install hook falls back from `ln -s` to `cp` when HMDFS rejects creation of the `.mod` entry.

## Verification

OpenDesk runs the repository CI script with `CI_PACKAGES=archives/l/lcmaps-plugins-verify-proxy/1.5.13`. The consumer test loads the installed `.mod` with `RTLD_NOW`, resolves the five LCMAPS plugin entry points, checks the installed artifacts, and executes `verify-proxy-tool -h`.

The consumer coverage is recorded as 12 assertions: 11 checks in the C harness (four installed files, one `dlopen`, five symbols, one `dlclose`) plus the CLI smoke run.

Upstream ships no automated test suite; the manual `plugin_test.c` programs are not wired into any build target. This is recorded in `test_package/MANIFEST.yml`.
