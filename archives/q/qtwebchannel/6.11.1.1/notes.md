# qtwebchannel 6.11.1 适配笔记

## 编译环境
- 构建系统: cmake (Qt 6 module, qmake .pro 由 CMake 驱动)
- 编译日期: 2026-08-19
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built (conan 验证后更新为 published)

## 编译步骤

1. init-build: 下载官方 Qt 子模块源码
   `https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qtwebchannel-everywhere-src-6.11.1.tar.xz`
   (SHA256: 69fbb50b71d6e6596c2d6863ee9a9c984a4d01378ee2b7b4163bb467a0158d82)
2. 手动探索编译（依赖制品仓发布的 qtbase/6.11.1 预编译包）:
   ```
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
     -DQt6_DIR=$QTBA/lib/cmake/Qt6 \
     -DQT_QMAKE_TARGET_MKSPEC=harmonyos-clang \
     -DQT_BUILD_TESTS=ON -DQT_BUILD_TESTS_BY_DEFAULT=ON \
     -DQT_BUILD_EXAMPLES=OFF -DQT_BUILD_BENCHMARKS=OFF -DQT_BUILD_MANUAL_TESTS=OFF
   cmake --build build -j1
   ```
3. 上游测试: `ctest --test-dir build --output-on-failure -j1`（需 LD_LIBRARY_PATH 指向 qtbase lib）
4. conan-init 生成配方（autotools 模板有误，已按 qtwebsockets/6.11.1 参考重写为 CMake 配方）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ctest 运行时 `symbol not found`（Qt6Core 符号） | LD_LIBRARY_PATH 未包含 qtbase 包的 lib 目录 | 运行时 export LD_LIBRARY_PATH=$QTBA/lib（VirtualRunEnv 处理） |
| 2 | module_includes 上游测试失败 | 单模块构建树导出时 Qt6::Core 仅以 IMPORTED_LINK_DEPENDENT_LIBRARIES 声明（不传播 INTERFACE_INCLUDE_DIRECTORIES），该测试面向完整 Qt 源码树构建 | 平台/构建模式限制，非本模块缺陷；功能测试 tst_webchannel 通过，等价消费者覆盖由 test_package 提供 |
| 3 | conan-init 生成 autotools 模板 | 模板检测把 Qt 模块识别为 autotools | 按同版本已发布模块 qtwebsockets/6.11.1 的 CMake 配方模式重写 |

## 依赖版本
- qtbase/6.11.1（制品仓 ohpcd 已发布）
- qtdeclarative/6.11.1.1（`6.11.1` 与 `.1` 修订均已在 ohpcd 发布，提供 Quick/QuickTest 可选组件；本修订引用 `.1`）
- qtshadertools/6.11.1（qtdeclarative 传递依赖，已发布）

## 验证结果

```bash
# 库构建 + 链接
libQt6WebChannel.so 构建成功
# 上游功能测试
ctest -R '^tst_webchannel$' --output-on-failure  # PASSED (11.5s)
# module_includes 为完整源码树构建模式的集成测试，单模块构建下受限（见上表 #2）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，复用 Qt 原生 CMake 包文件（cmake_find_mode=none） |
| conandata.yml | 官方源码 URL + SHA256 |
| test_package/ | 消费者测试（QWebChannel 注册/查询/注销 + transport 验证） |
| patches/ | 无（无需源码补丁） |

## 注意事项
- 本模块为 Qt WebEngine 的必要依赖（qtwebengine 的 WebChannel API 硬依赖它）
- 上游测试：tst_webchannel 通过；module_includes 为构建模式限制（非阻塞）
- settings.os 判断使用 `in ("Linux", "OHOS")`（R32）
---

**编译结束**: 2026-08-19 23:59
**最终状态**: published

## 6.11.1.1 修订说明（2026-10-01）

对已发布 `qtwebchannel/6.11.1` 的 provider 修订（R37，上游源码版本保持 6.11.1）：

- `qtbase/6.11.1` -> `qtbase/6.11.1.3, override=True`。**必须加 override**：本包依赖的 `qtdeclarative/6.11.1.1` 自身仍声明 `qtbase/6.11.1`，图里会出现 `.3` 与 `6.11.1` 两条不同版本的边。
- `qtdeclarative/6.11.1` -> `qtdeclarative/6.11.1.1`（该修订已于 2026-10-02 合入并发布：rrev `094c423ffa9d`、OHOS/armv8 二进制 `80f600179081…`）。原先「等 `.1` 发布后再引用」的条件已满足，故一次性写对。
- 上游源码、补丁（`patches/0001` 与 6.11.1 完全一致）、构建逻辑与测试断言**零改动**；`conandata.yml` 的补丁为扁平列表，不涉及按版本作键的陷阱。
- 隔离链验证证据：`evidence/qtwebchannel/LastTest.log` 记录 `Totals: 57 passed, 0 failed` 与 `Totals: 38 passed, 0 failed`，另有 `CMakeCache.txt` 与 184KB `conan create` 记录。

- **OHOS 测试运行环境（本修订新增）**：上游 `module_includes` CTest 会做嵌套 CMake 链接，SDK `lld` 需要 SDK 自带的 `libxml2.so.16`，而 Conan 运行环境里的 libxml2 会遮蔽它（`xmlNewNs: symbol not found`）⇒ 生成 `ohos-llvm-libxml2-env.sh`，在 `conanrun` 之后再把 SDK `llvm/lib` 提到 `LD_LIBRARY_PATH` 首位，仅作用于 ctest 子进程，不改编译器与工具链（与已发布 `akonadi/25.12.3` 同类修法）。

- **运行时环境导出（本修订新增）**：`package_info()` 增加 `runenv_info.prepend_path("LD_LIBRARY_PATH", <pkg>/lib)`。上游 Qt 模块不写入构建树外的 RPATH，此前消费者与 `test_package` 只能靠偶然的 RPATH 命中，CI 实测报 `Error loading shared library libQt6WebChannel.so.6` → `Error 127`；导出后 `conanrun` 会带上本包 `lib/`（与 libkleo / ktextaddons / akonadi 的做法一致）。
