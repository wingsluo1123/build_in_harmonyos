# Zabbix 7.4.5 - HarmonyOS PC Adaptation Notes

## Build Configuration

- **Platform**: OpenHarmony / HarmonyOS PC arm64
- **Compiler**: clang/clang++ 15.0.4
- **Build system**: Autotools (configure + make)
- **Components enabled**: agent, zabbix_get, zabbix_sender
- **Components disabled**: server, proxy, agent2, web service, Java gateway

## Dependencies

- openssl/3.5.6.1.1 (Conan, prebuilt)
- pcre2/10.45 (Conan, prebuilt)
- zlib/1.3.1 (Conan, prebuilt)

## Patches Applied

1. **0001-dns-disable-_res-for-ohos.patch**: Disable `_res` global variable usage on HarmonyOS.
   The thread-unsafe resolver API (`_res` struct, `res_send`, `res_ninit`) is not available
   on HarmonyOS. The DNS query function falls back to returning `SYSINFO_RET_FAIL`.

2. **0002-configure-umask-for-hmdfs.patch**: Replace `umask 077` with `umask 000` in
   configure-generated config.status. HMDFS does not allow creating directories with
   restrictive permissions (owner is always file_manager).

## Platform Issues

- **config.guess/sub**: Does not recognize `aarch64-linux-ohos`, used `--build=aarch64-linux-gnu`
- **`_res` global**: Not available on HM Kernel, DNS monitoring key disabled
- **HMDFS permissions**: `mktemp -d` with `umask 077` creates directories owned by file_manager,
  making them unwritable. Fixed by using `umask 000`.

## Known Limitations

- DNS monitoring item (`net.dns`) is disabled on HarmonyOS
- No cmocka tests were run (cmocka not available, `--without-cmocka` or not configured)
- Agent2 (Go-based) not built
