# pxr-ts 26.08 适配笔记

## 编译环境

- 构建系统: cmake (Conan 2)
- 编译器: clang/clang++ (15)
- 目标平台: HarmonyOS PC / OHOS aarch64
- 上游: Pixar OpenUSD v26.08（`pxr/base/ts` 时间样条库）

## 编译步骤

1. 从 GitHub 下载 OpenUSD v26.08 源码 tarball（`gh-proxy.com` 镜像优先）
2. 校验 SHA256：`4bccbb95cddda1dbeef2f74a08b9456352f2aa91bfd4578c0c613009c7950149`
3. 应用 OHOS 可移植性补丁 `patches/0001-arch-tf-fixes-for-ohos.patch`
4. `conan create`，CMake 目标 `ts`；关闭成像 / Python / 工具链等非必要模块
5. 打包 `libusd_{ts,vt,gf,trace,js,tf,arch}.a` 与其头文件

## 依赖闭包（关键）

`pxr/base/ts/CMakeLists.txt` 里写着 `set(libs vt gf tf)`；顺着依赖再往下走两层：

| 库 | 其自身依赖 |
|---|---|
| `ts` | `vt`, `gf`, `tf` |
| `vt` | `arch`, `tf`, `gf`, `trace`, `TBB::tbb` |
| `gf` | `arch`, `tf` |
| `trace` | `arch`, `tf`, `js` |
| `js` | `arch`, `tf` |
| `tf` | `arch` |
| `arch` | — |
| `work` | 纯头文件，无 `.a` |

`package()` 与 `cpp_info.libs` 按**拓扑序**（每个依赖都排在其使用者之后）：
`ts, vt, gf, trace, js, tf, arch`。静态库只单遍扫描，这个顺序不能随意调 ——
少一个库、或把依赖排到使用者前面，消费者链接期就会报 `undefined symbol`。
`work` 只有头文件，按头文件闭包一并收走。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `_SC_LEVEL1_DCACHE_LINESIZE` 未定义 | OHOS musl 的 sysconf 不支持此常量 | 加 `#ifdef` 特性守卫，缺失时回退 64 |
| 2 | `strerror_r` 返回类型不匹配 | OHOS musl 用 POSIX 版（返回 int），非 GNU 版（返回 char*） | 移除 `_GNU_SOURCE` 分支，走 POSIX 路径 |
| 3 | `__environ` 未声明 | OHOS musl 不提供 glibc 的 `__environ` | 改用 `environ`（`unistd.h` 声明） |
| 4 | `DEFFILEMODE` 未定义 | OHOS 的 `sys/stat.h` 不定义此宏 | 扩展 `#ifdef` 条件并补默认值 `0666` |
| 5 | lld 链接期报缺 `libxml2.so.16` (E132) | SDK 的 clang 驱动派发 lld，lld 的 RUNPATH 只找 SDK `llvm/lib` | 构建前把 SDK `llvm/lib` 前置进 `LD_LIBRARY_PATH` |
| 6 | 消费者链接期报 `undefined symbol: …::JsWriter::JsWriter(…)`（真机实测） | 库闭包最初只按 `ts -> vt/gf/tf` 推出 `{ts, vt, gf, tf, trace, arch}`，漏了 `trace -> js`；`libusd_trace.a` 的 `reporter.cpp` / `serialization.cpp` 用到 `JsWriter` / `JsValue` / `JsParseStream`，这些符号定义在 `libusd_js.a` | 把 `js` 加入库与头文件闭包，并把 `cpp_info.libs` 重排为拓扑序 `ts, vt, gf, trace, js, tf, arch` |

## 源码修改

补丁文件：`patches/0001-arch-tf-fixes-for-ohos.patch`

内容为 4 处特性守卫式改动（`pxr/base/arch` 的 3 个文件 + `pxr/base/tf/atomicRenameUtil.cpp`），
**不使用平台宏判断**，因此对 Linux/macOS 上游行为零影响。
该补丁与同族 `pxr-gf 26.08`、`pxr-kind 26.08` 完全一致（逐字节相同）。

## 依赖版本

- `tbb/2023.0.0`（ohpcd 制品仓）

## 验证结果

```bash
conan create archives/p/pxr-ts/26.08 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

真机（HarmonyOS PC / aarch64 / clang 15.0.4）实测：`conan create` 通过，`package()`
打包静态库与头文件，test_package 编译并运行成功，关键输出：

```
======== Testing the package: Executing test ========
pxr-ts/26.08 (test package): RUN: ./test_pxr_ts
pxr-ts smoke test: OK (Eval(1.0)=10, Eval(0.5)=0, ArchStrerror(ENOENT)="No such file or directory")
```

## 上游测试说明

上游 `pxr/base/ts/testenv/` 自带 C++ 与 Python 测试（`testTsSplineAPI.cpp`、
`testTsSplineEval.cpp` 等 10 个 `testTs*.cpp` 用例 + 7 个 `testTs*.py` 用例，
另有 2 个 `tsTest_*.py` 支撑模块 —— `tsTest_TsFramework.py` / `tsTest_TsVsBezier.py`，
被上面用例 import，不是独立用例）。这些用例由
`PXR_BUILD_TESTS` 控制，且依赖 `tsTest` 框架与 Python 绑定。

本配方沿用同族 `pxr-vt` / `pxr-gf` / `pxr-kind` 的既定做法，以
`PXR_BUILD_TESTS=OFF`、`PXR_ENABLE_PYTHON_SUPPORT=OFF` 构建，因此不运行上游
测试套件，改为提供等价的 C++ 消费者测试 `test_package/test_pxr_ts.cpp`，
覆盖 `TsSpline` 的构造 / 值类型 / 结点插入 / 求值，以及依赖闭包
`arch` / `tf` / `vt` / `gf` 各一个基础接口（用于在链接期捕获静态库缺漏或顺序错误）。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libusd_ts.a` `libusd_vt.a` `libusd_gf.a` `libusd_trace.a` `libusd_js.a` `libusd_tf.a` `libusd_arch.a` | 静态库 |
| `include/pxr/base/{ts,vt,gf,trace,js,tf,arch,work}/*.h` | 源码头文件 |
| `include/pxr/pxr.h` | 构建期生成的头文件 |

## 注意事项

- 本包为**静态库**（`shared=False`），与同族 pxr-* 一致，无 ELF 签名需求。
- `cpp_info.libs` 按拓扑序（依赖者在前）写入，以保证消费者静态链接正确；
  `js` 是必需项 —— 消费者即使完全不碰 JSON，只要链到 `libusd_trace.a` 就间接需要它。
- 本机（鸿蒙 PC）实测 `gh-proxy.com` 直连时 conan 的断点续传偶发卡在半途
  （`source()` 停住不动）。可用 curl 预下 tarball 后临时把本机 `conandata.yml`
  指向 `file://` 再构建（**仅本机临时改动，不入库**）—— CI 的
  `ci/conan/build_and_test.sh` 本身就有同款「预下载 + 临时改写」兜底。
