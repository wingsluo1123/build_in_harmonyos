# mini-httpd 1.3 adaptation notes

## Scope

- Package: `mini-httpd/1.3`
- Upstream archive: `mini_httpd-1.30.tar.gz` (任务版本 1.3 对应上游归档版本 1.30)
- Source: `https://acme.com/software/mini_httpd/mini_httpd-1.30.tar.gz`
- SHA256: `9c4481802af8dde2e164062185c279e9274525c3af93d014fdc0b80cf30bca6e`

## Version mapping

- 竞赛任务版本: `mini-httpd 1.3`
- 上游官方归档版本: `mini_httpd-1.30.tar.gz`
- 上游 version.h: `#define SERVER_SOFTWARE "mini_httpd/1.30 26Oct2018"`
- 说明: 官网不存在 1.3 版本的独立归档，1.3 是竞赛给定的任务版本号，对应上游实际 1.30 版本。不能把版本号当小数处理。

## Platform constraints

| Constraint | Status | Notes |
|------------|--------|-------|
| chroot()   | EXCLUDE_LIST | HarmonyOS PC 不支持 chroot 系统调用 |
| setuid/setgid | 可用（EPERM on non-root） | setuid/setgid 系统调用可用；setreuid/setregid 触发 SIGSYS（未实现） |
| TMPDIR | `$HOME/tmp` | `/tmp` 只读，需设置 TMPDIR |
| symlink | 不支持覆盖式 ln -sf | 需先 rm 再 ln |
| ELF signing | sign-elf required | 可执行文件需签名 |
| /bin/sh | 无 | 需 CONFIG_SHELL 或 bash |

## Build notes

- Build system: raw Makefile, no configure script
- Builds two binaries: `mini_httpd` and `htpasswd`
- `CC=clang` (OHOS 可能无 GCC)
- `-lcrypt` needed for htpasswd, provided by musl libc on OHOS
- No external dependencies beyond system libc
- No SSL support (SSL_TREE not configured - would need OpenSSL package)

## Upstream tests

- mini_httpd 上游没有独立的 test/ 或 tests/ 目录
- Makefile 中无 `check` / `test` target
- 上游测试: 0/0 (N/A)
- 新增 smoke test: `mini_httpd --help` 或 `mini_httpd -V`

## Source acquisition

- 主 URL: `https://acme.com/software/mini_httpd/mini_httpd-1.30.tar.gz` ✅ 200 OK
- 备用 URL: 同上 (1.3 版本不存在，1.30 为正确归档)
- 归档根目录: `mini_httpd-1.30/`
- 源码内版本标记: `mini_httpd/1.30 26Oct2018` (version.h)
---

**编译结束**: 2026-08-05 10:04
**最终状态**: built
