# pesign

对 PE/COFF 二进制（UEFI 应用、shim、内核镜像等）做**签名与校验**的工具集。
上游：<https://github.com/rhboot/pesign>

| 版本 | 说明 |
|------|------|
| [116](116/notes.md) | 当前适配版本（HarmonyOS PC / ohos-aarch64） |

## 这个包提供什么

- `bin/pesign` —— 签名服务与命令行
- `bin/efikeygen` —— 生成自签名证书
- `bin/authvar`、`bin/pesign-client`、`bin/pesigcheck`、`bin/pesum`

## 适配要点（细节见各版本 notes.md）

1. **musl 垫片**：musl 缺 `error_t` / `qsort_r` / `secure_getenv` / `program_invocation_*` ——
   配方生成 `conan_musl_shim.h`（放在源码树 `include/` 里、由 CFLAGS 的 `-include` 引入）声明它们，
   并编出 `.o` 实现 `secure_getenv` + 给 `program_invocation_*` 加 **weak 兜底定义**。
2. **链接库名要按包内实际文件来**：上游 `nss.pc` 的 `-lnss/-lnssutil/-lfreebl` 在 conan 的 nss 包里
   对不上（真正含 NSS 符号的是 `libnss3.so`）→ 配方扫描依赖包 `lib/` 生成 `-l` 列表；并显式带
   `-L` 与 **`-Wl,-rpath`**（否则运行期 `Error loading shared library libfreebl3.so`，rc=127）。
3. **手写 Makefile 的注入通道**：只有 `CFLAGS`/`LDFLAGS` 真进了编译/链接命令（`ARCH_CFLAGS` 没有）；
   make 的忽略错误前缀 `-` 必须在**制表符之后**。
4. **如实记录的偏离**：`secure_getenv`→`getenv`、man 页不构建、`-Werror` 降级、去掉 `-fshort-wchar`。
5. **测试边界**：真正签名需要 NSS 证书库与 EFI 环境，沙箱只验证"产物可用 + CLI 真跑"。
