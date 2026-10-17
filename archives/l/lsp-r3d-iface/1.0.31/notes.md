# lsp-r3d-iface 1.0.31 适配笔记

## 编译环境
- 构建系统: makefile（上游自研 make 系统：`make config` → `make` → `make install`）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15（OHOS SDK，`-stdlib=libc++`，C++17）
- 状态: built

## 编译步骤

配方（`conanfile.py`）内的等价手动流程：

```bash
# 1) 解包主源码 + 预置两个内嵌依赖源码（替代上游 make fetch 的 git clone）
tar xzf lsp-r3d-iface-1.0.31.tar.gz && cd lsp-r3d-iface-1.0.31
tar xzf lsp-common-lib-1.0.49.tar.gz && mv lsp-common-lib-1.0.49 modules/lsp-common-lib
tar xzf lsp-test-fw-1.0.35.tar.gz    && mv lsp-test-fw-1.0.35    modules/lsp-test-fw

# 2) 对内嵌 lsp-common-lib 打 OHOS qsort_r 补丁（与 lsp-common-lib 1.0.49 归档内容一致）
patch -p1 -d modules/lsp-common-lib -i <archive>/patches/modules/0001-lsp-common-lib-qsort_r-ohos.patch

# 3) 配置（强制 Linux 语义）→ 编译 → 安装
make config PLATFORM=Linux FEATURES="test strict" PREFIX=<prefix> CXX=clang++
make -j1 CXX=clang++          # src/Makefile 递归内嵌编译两个依赖
make install
```

平台判定：上游 `make` 按 `uname -s` 探测平台，OpenHarmony PC 返回 `HarmonyOS`，
上游不识别落入 Unknown 分支，`make config` 必须显式传 `PLATFORM=Linux`；
OHOS aarch64 目标（`-march=armv8-a+asimd`）与上游 Linux 路径一致，本包源码
无 `#ifdef` 平台差异，**本包源码零补丁**。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建期 `make fetch` git clone 两个 lsp-* 依赖，联网不可用 | 上游把 lsp-common-lib（生产）与 lsp-test-fw（测试）按 `*TYPE=src` 内嵌编译，靠 git clone 取源码 | conandata.yml 按上游 `modules.mk` pin 的版本登记两个 tarball，`source()` 预置到 `modules/<name>/`，构建完全离线 |
| 2 | 内嵌的 lsp-common-lib 编译报 `no member named 'qsort_r'` | OHOS libc（musl）不提供 GNU qsort_r，而该依赖源码与独立版相同 | 复用 lsp-common-lib 1.0.49 归档的 0001 补丁（改 `qsort` + 线程局部比较器上下文），放在 `patches/modules/` 由配方在预置后应用 |
| 3 | 消费者测试编译报找不到 `<lsp-plug.in/common/types.h>` | 本包公共头（`include/lsp-plug.in/r3d/iface/*.h`）引用 lsp-common-lib 的头文件，而上游只安装自己的头文件 | `requirements()` 声明 `lsp-common-lib/1.0.49@ohpcd/stable` 并加 `transitive_headers=True`（仅 `requires` 不加该 trait 时 CMakeDeps 生成的依赖 include 目录为空） |
| 4 | 依赖解析失败 `Package 'lsp-common-lib/1.0.49' not resolved` | Conan 2 不把裸 `name/version` 解析到 `@ohpcd/stable`；缓存里残留的早期无 user/channel recipe 还会被静默选中（表现为 include 目录为空） | requires 写全 `@ohpcd/stable`（R27），并 `conan remove` 清理缓存里的无 user/channel 残留 |
| 5 | W3 本地 CI / CI 的 L0i 门禁失败 `unpublished_deps` | R36 要求每个 requires 依赖都先发布到制品仓，`lsp-common-lib` 的 PR 尚未合入发布 | **发布顺序约束，非配方缺陷**：按 lsp-test-fw → lsp-common-lib → lsp-r3d-iface → lsp-r3d-base-lib 顺序逐级发布；本包 conan-verify 已全绿 |
| 6 | 消费者测试断言连续失败 | 测试自身预期写错：`Factory::enumerate(0)` 就是本用例注册的 factory（不是 NULL）；类型/枚举在 `lsp::r3d` 命名空间内 | 修正断言与 `using namespace lsp::r3d` |

## 源码修改

| 文件 | 补丁 | 内容 |
|------|------|------|
| `modules/lsp-common-lib/src/main/stdlib.cpp`（预置后） | `patches/modules/0001-lsp-common-lib-qsort_r-ohos.patch` | 与 lsp-common-lib 1.0.49 归档的 0001 补丁内容一致，仅路径基准不同（作用于预置的内嵌依赖而非独立包） |

本包 `src/main/*.cpp` 零修改。

## 依赖版本

- 生产依赖：`lsp-common-lib 1.0.49`（Conan requires，头文件传递；目标码由上游
  `*TYPE=src` 机制内嵌编译，源码由 conandata.yml 预置）。
- 构建期源码依赖：`lsp-test-fw 1.0.35`（FEATURES=test 时内嵌编译，不进生产包）。
- 编译器：OHOS SDK 26.0.0.18 自带 clang/clang++ 15.0.4；Conan profile：
  `ohos-local`（等价 `ci/conan/profiles/ohos-aarch64`，仅工具链路径本地化）。

## 验证结果

```bash
# conan create + test_package（G0-G4 全绿）
python3 scripts/ohc-run.py conan-verify lsp-r3d-iface 1.0.31 --profile ohos-local
#   G1: PASS   G2: PASS（含 test_package 消费者测试）
#   verdict: PASS
```

test_package 消费者测试（`test_package/test.cpp`，9 项断言）：
- 编译期校验版本宏 1.0.31；
- `Factory::enumerate(0)` 取回本用例注册的 factory、`enumerate(1)` 为 NULL；
- 经枚举到的 `factory_t` 实调 `metadata(id)`/`create(id)` 函数指针表（0 号有值、
  非 0 号 NULL，调用计数校验）；
- 注册链表遍历（`Factory::list()`/`next()`）非空；
- 枚举值与结构布局自洽。

上游测试：上游 `src/test/` 只有测试框架入口（无任何 utest 用例），因此上游
注册用例数为 0，验证以 test_package 消费者测试为主（详见 MANIFEST.yml）。

## 交付物

| 文件 | 说明 |
|------|------|
| `patches/modules/0001-lsp-common-lib-qsort_r-ohos.patch` | 预置内嵌 lsp-common-lib 的 OHOS 移植补丁 |
| `reports/conan-create.log` | 完整构建日志 |
| `reports/conan-verify-report.md` | G0-G4 验证报告（PASS） |

包内容（shared=False 语义）：`lib/liblsp-r3d-iface-1.0.31.a`（已含内嵌的
lsp-common-lib 目标码）+ `lib/pkgconfig/lsp-r3d-iface.pc` +
头文件 `include/lsp-plug.in/r3d/iface/**`。

## 注意事项

- **发布顺序（R36）**：本包 `requires("lsp-common-lib/1.0.49@ohpcd/stable")`，
  lsp-common-lib 必须先发布到制品仓，否则本地 W3 与 CI 的 L0i 门禁硬失败。
  赛事侧依赖库本身即为优先审核项，按依赖链顺序逐级提交即可。
- **补丁位置**：`patches/modules/` 下的补丁不进 conandata 的 `patches` 表，
  由配方 `source()` 应用；若移到 `patches/` 顶层，clean-verify 的 G0 会因
  主源码树里没有该文件而失败。
- 若关闭 `FEATURES` 里的 `test`，就不需要预置 lsp-test-fw；本配方保持上游
  默认启用上游测试。
- 下游 `lsp-r3d-base-lib` 头文件位于
  `include/lsp-plug.in/r3d/base/**`（本包不含）。

---

**编译结束**: 2026-09-29 01:55
**最终状态**: built
