# PostgreSQL 18.3 for HarmonyOS

PostgreSQL database server and client tools (pg_dump, psql, pg_config, initdb, etc.) compiled for HarmonyOS (aarch64).

## Build

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## OHOS Adaptations

- SysV IPC skip (shmget unimplemented on OHOS)
- hmdfs permission relaxation (umask 077→022, file_perm 0600→0640)
- getpwuid fallback for OHOS
- Unix socket disable for initdb
- config.guess: HarmonyOS platform detection
