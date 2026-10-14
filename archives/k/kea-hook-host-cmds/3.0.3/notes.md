# kea-hook-host-cmds 3.0.3 — OpenHarmony PC 适配笔记

## 1. 结论速览

| 项 | 结果 |
|----|------|
| 构建 | ✅ `conan create` 成功（1432/1432 ninja 目标，rc=0） |
| 上游测试 | ✅ 128/128（`dhcp-host-cmds-tests` 125 + `dhcp-host-cmds-libloadtests` 3） |
| test_package | ✅ 2/2（`test_host_cmds_hook` 消费者契约 + `test_ohos_platform` 鸿蒙特有） |
| 产物 | `lib/kea/hooks/libdhcp_host_cmds.so`（240064 bytes / 234 KiB），包 21.3 MB |
| 运行库闭包 | ✅ 20 个 `libkea-*`，与配方声明、与包内文件三方逐项一致，无缺失 |
| 补丁 | 2 个（同族继承，逐字节一致） |
| 状态 | built |

## 2. 环境与来源

| 项 | 值 |
|----|----|
| 源码 | `https://ftp.isc.org/isc/kea/3.0.3/kea-3.0.3.tar.xz` |
| SHA256 | `09702ddb078b637e85de9236cbedd3fb9d7af7c6e797026c538b45748ad4d631` |
| 上游树 | Kea 3.0.3 单工程（Meson），本包只构建 `src/hooks/dhcp/host_cmds/` 及其测试 |
| 编译器 | OHOS SDK clang/clang++（`aarch64-linux-ohos`），profile `ci/conan/profiles/ohos-aarch64` |
| 语言预检 (R47) | 判定 **cpp**，匹配（源码主体 `.cc`/`.h`，无语言迁移问题） |
| 依赖 | `boost/1.85.0`、`log4cplus/2.2.0.1`、`openssl/3.5.8.1`；测试 `gtest/1.17.0.1`；工具 `meson/1.11.0` |
| 构建日期 | 2026-09-28 |

## 3. 复现步骤

```bash
cd archives/k/kea-hook-host-cmds/3.0.3
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64
```

配方在 `build()` 内调用 Meson 并**实际执行**上游套件（`upstream_test_suites`），
失败即中断 `conan create`，不存在"只编译不跑测试"的路径。

## 4. 平台问题与对策

问题集与同族 hook 包（lease-cmds / stat-cmds / pgsql / limits …）**完全同源**：同一
`kea-3.0.3.tar.xz`、同一套平台陷阱，因此补丁为**继承复制（inherited-identical）**，
与 `archives/k/kea-hook-lease-cmds/3.0.3/patches/`、`archives/k/kea-hook-pgsql/3.0.3/patches/`
的 `0001`/`0002` 逐字节一致（比较方法：`cmp`）。

| # | 现象 | 根因 | 对策（落地位置） |
|---|------|------|-----------------|
| 1 | Meson 配置期报平台不受支持 | OHOS 上 Meson 报 `system='harmonyos'`，Kea 平台白名单只有 linux/freebsd/netbsd | `0001-meson.build.patch`：顶层把 `harmonyos` 归一化为 `linux` |
| 2 | 编译 `libkea-dhcp` 时 `struct sockaddr_storage` 重定义 | OHOS sysroot `linux/socket.h` 与 musl `sys/socket.h` 各自定义该结构 | `0002-...iface_mgr_linux.cc.patch`：define-guard 重命名（用 `__linux__ && !__GLIBC__` 判定，非平台宏空壳，含实质逻辑） |
| 3 | boost 编译报 `pthread_setcancelstate` 未声明 | OHOS musl `pthread.h` 不提供该扩展 | 配方 `extra_cxxflags` 定义 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 4 | Meson 探测归档器失败 | clang 工具链下 Meson 用裸名 `llvm-ar`/`llvm-ranlib`，裸名不在 PATH | 配方从 `tools.build:compiler_executables` 推导**绝对路径**写入 machine file |
| 5 | 配置期 `cpp.run()` 探针（log4cplus）失败 | 探针必须在 host 侧运行，共享依赖需可见 | 配方在 Meson 配置环境注入 host 依赖 libdirs 到 `LD_LIBRARY_PATH`（build_folder 私有 prefix，不写共享 `/usr/local`） |

> 关于"历史可迁移性"核验（W0b）：以上 5 条均为**同一上游树在 CI 型 clean 环境**下的结论
> （同族 7 个包已按此配方通过 CI），工具链均为 CI 具备的 gcc/clang/make/meson，无设备特有
> 工具链依赖 —— 本包的 `conan create`（本地 W3 同源流程）全量重建 1432 个目标并通过 128 项
> 用例，即为对本包的一次独立复现。

### 上游测试申报（R51）

| 项 | 数量 | 说明 |
|----|------|------|
| 上游测试目录 | 2 | `src/hooks/dhcp/host_cmds/tests/`（单元测试）、`src/hooks/dhcp/host_cmds/libloadtests/`（libload 测试） |
| Meson 注册套件 | 2 | `dhcp-host-cmds-tests`、`dhcp-host-cmds-libloadtests` |
| 实际执行 | 2/2 | 均在 `conan create` 的 `build()` 内执行 |
| 用例数 | 128 | 125 + 3，实测通过率 100% |
| 未执行 | 无 | 其它 Meson 套件属 Kea 其它组件（需特权/网络夹具），与本 hook 无关，故不纳入 |

⚠️ 命名陷阱：libload 套件的**目录名**（`libloadtests/`）、**产物名**
（`dhcp-host-cmds-libload-tests`）与 **Meson 注册名**（`dhcp-host-cmds-libloadtests`）
三者不一致，必须用 `meson test --list -C <builddir>` 确认真名，否则套件"静默不执行"。

### 鸿蒙特有测试（1 项）

`test_package/test_ohos_platform.c`：断言产物 `libdhcp_host_cmds.so` 的平台 ABI 特征 ——
`ELFCLASS64`/`EM_AARCH64`、`DT_NEEDED` 链接 musl `libc.so`（而非 glibc `libc.so.6`）、
链接 `libc++_shared.so`，并由 OHOS 加载器 `dlopen(RTLD_NOW|RTLD_LOCAL)` 实际解析
（覆盖 20 个 Kea 运行库闭包）——1/1 通过。

### 运行库闭包核对（R26 相关）

配方声明的 `kea_runtime_libs`（20 项）通过纯 ELF `DT_NEEDED` 广度优先遍历与包内实际文件
核对：**声明 == 闭包 == 包内**，无缺失、无多余。仅用于声明 NEEDED 传递闭包
（`cpp_info.libs=[]`，不改写产物的 DT_NEEDED）。

## 5. 产物信息

| 项 | 值 |
|----|----|
| 插件 | `lib/kea/hooks/libdhcp_host_cmds.so`（240064 bytes） |
| hook ABI | `KEA_HOOKS_VERSION = 30003` |
| `cpp_info` | `libs=[]`、`includedirs=[]`、`bindirs=[]`、`libdirs=["lib"]` |
| 可执行文件 | 无 → 不需要软件级 `commands.json`（R38 不适用） |
| 包大小 | 21.3 MB（插件本体 + 其 `dlopen` 依赖的 20 个 Kea 运行库，以 soname 符号链接去重，无重复拷贝） |

## 6. 待办 / 后续

- [ ] 无阻塞项。若制品仓后续升级 boost，需回归验证 1.85.0 之外版本是否补齐 Kea 所需头文件。
- [ ] 同族其它 hook（legal-log / forensic-log 等）可按本包同一模式复制适配。

## 7. 变更记录

| 日期 | 变更 |
|------|------|
| 2026-09-28 | 首次适配：Meson 交叉构建 + OHOS 平台补丁继承 + 128 项上游用例与 1 项鸿蒙特有测试验证 |
---

**编译结束**: 2026-09-28 23:46
**最终状态**: built
