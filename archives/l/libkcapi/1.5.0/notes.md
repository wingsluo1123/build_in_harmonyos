# libkcapi 1.5.0 适配笔记

## 构建环境

- 构建系统: Autotools
- 编译日期: 2026-07-15
- 编译器: clang / clang++
- 平台: HarmonyOS PC (aarch64)
- 状态: built

## 源码

- URL: https://github.com/smuellerDD/libkcapi/archive/refs/tags/v1.5.0.tar.gz
- SHA-256: `f1d827738bda03065afd03315479b058f43493ab6e896821b947f391aa566ba0`

## Conan 配方

Git tag 快照不包含 `configure`，而 CI Worker 不提供 `aclocal`。配方因此导出由
上游 `configure.ac` 和 `Makefile.am` 生成的 `prebuilt.tar.gz`，构建时解压这些
Autotools 文件，再以 `--disable-shared --enable-static` 配置、编译和安装。

`--build` 三元组由 `settings.arch` 推导（`config.guess` 无法识别 HongMeng 主机），
不再硬编码单一 CPU。

`0001-lib-kcapi-kernel-if.c.patch` 处理 Linux UAPI 头文件中的 `sockaddr_storage`
名称冲突：`<linux/netlink.h>` 与 `<linux/rtnetlink.h>` 会间接引入
`<linux/socket.h>`，在缺少 `<linux/libc-compat.h>` 的 C 库上会重复定义
`struct sockaddr_storage`。补丁在解析这两个 UAPI 头期间把内核版本重命名为
`__libkcapi_uapi_sockaddr_storage`，解析完立即 `#undef`。

该守卫**无条件生效、不含任何平台条件编译宏**（项目规则 R8）：本翻译单元只使用
UAPI 头里的 `struct sockaddr_alg` / `struct sockaddr_nl`，重命名对其余代码是
no-op，在所有平台上行为一致。

## 验证

`test_package` 编译并链接 `libkcapi::libkcapi`，共 8 条断言：

1. `kcapi_version()` 返回非零版本号
2. `kcapi_versionstring()` 正确填充版本字符串
3. `kcapi_md_sha256("")` 返回 32 字节
4. 空串摘要与 FIPS 180-4 向量一致
5. `kcapi_md_init("sha256")` 成功
6. `kcapi_md_digestsize()` == 32
7. `kcapi_md_digest("abc")` 返回 32 字节
8. `SHA-256("abc")` 与 FIPS 180-4 向量一致

断言 3～8 会真实走进补丁所修改的 `lib/kcapi-kernel-if.c`（AF_ALG socket 路径），
因此测试覆盖了补丁改动本身，而不是只验证链接是否成功。

若沙箱内无 AF_ALG 权限，测试打印 `SKIP` 并输出 `errno`，明确区分「平台受限」与
「库缺陷」，不把平台限制伪装成通过。

上游 `Makefile.am` 未定义 `check` target（`make check` 不存在），测试由
`test/test.sh` 驱动并依赖内核 AF_ALG 与已安装的 `kcapi-*` 工具，故未纳入构建，
详见 `test_package/MANIFEST.yml`。
