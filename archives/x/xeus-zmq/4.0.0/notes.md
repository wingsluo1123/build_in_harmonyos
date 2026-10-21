# xeus-zmq 4.0.0 — 适配进度

> 分支: feat/xeus-zmq-4.0.0
> Worktree: D:\harmonyos\worktrees\xeus-zmq
> 真机验证 worktree: $HOME/wt-xeus-zmq（feat/xeus-zmq-4.0.0-wt）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | xeus-zmq |
| 版本 | 4.0.0 |
| 状态 | ✅ 真机 `conan create` 通过（含 test_package 运行） |
| 构建系统 | CMake（cmake_minimum_required 3.16） |
| C++ 标准 | C++17，共享库 libxeus-zmq.so（SOVERSION 8） |
| 源码 | https://github.com/jupyter-xeus/xeus-zmq/archive/refs/tags/4.0.0.tar.gz |
| sha256 | 6a87c0edeefae1350743071cd78c825d6ab21e771b52610ef7e41c434af20db6 |

## 二、W0 依赖检查（2026-10-04 结论 + 真机实测确认）
| 依赖 | 上游要求 | 仓库现状 | 结论 |
|------|----------|----------|------|
| xeus | `>=6,<7`（dev env）| ✅ xeus/6.0.5（已由独立 PR 适配）| OK，真机命中 6.0.5 二进制 |
| nlohmann_json | >=3.11.3 | ✅ 3.12.0 | OK |
| cppzmq | >=4.8.1 | ✅ 4.10.0 | OK |
| zeromq/libzmq | >=4.3.2 | ✅ 4.3.5 | OK |
| OpenSSL | REQUIRED | ✅ 3.0.16 | OK |
| libsodium | 仅静态/CURVE | ➖ `XEUS_ZMQ_BUILD_WITHOUT_LIBSODIUM=ON` 关闭 | OK |

## 三、构建/可选特性裁剪
- `XEUS_ZMQ_BUILD_TESTS=OFF`（默认打包）：消费者级 API 由 test_package 覆盖。
- **`tests=True` option（`-o xeus-zmq/*:tests=True`）**：构建上游测试二进制（`XEUS_ZMQ_BUILD_TESTS=ON`），并真实执行可运行的上游 ctest 测试（见"六·一"）。
- `XEUS_ZMQ_BUILD_WITHOUT_LIBSODIUM=ON`：仓库内 zeromq 已 `WITH_LIBSODIUM=OFF`。
- OHOS/Linux 下沿用二进制签名逻辑（llvm-objcopy 去 codesign + binary-sign-tool 自签名）。

## 四、真机验证结果（2026-10-15）
- 真机：aarch64 / OHOS 6.0 / clang 15 / libc++ / Release；profile `ohos-aarch64`。
- `conan create archives/x/xeus-zmq/4.0.0 -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing -c tools.build:jobs=2` **成功**。
- 产物：`xeus-zmq/4.0.0` revision `16930510fc44e96eff2c04baa087bc5b`，package `16782922c4bdd3fd3526adf6ad5abe492687efc7`；`libxeus-zmq.so`（4.5MB）已签名。
- test_package：CMake 配置 → 编译 → **真机运行 `./test_xeus_zmq` 输出 `xeus-zmq version: 4.0.0 / test passed`**（7 项断言：版本宏 4/0/0、binary SOVERSION 宏 8/0/0、`xeus::make_zmq_context()` 非空）。

### 构建修复链（本轮逐次排除）
1. `xeus/[>=6.0,<7.0]` 逗号写法 → Conan 2.31 报 `invalid option` → 改空格分隔 `[>=6.0 <7.0]`。
2. 主配方缺 `generators = "CMakeDeps"` → 依赖 config 不生成、find_package(xeus) 失败 → 补类属性。
3. `find_package(xeus 5.0.0)` 拒绝 6.0.5：CMakeDeps ConfigVersion 强制 major 对齐 → patch `xeus_REQUIRED_VERSION` 5.0.0→6.0.0。
4. OpenSSL shim 引用未加载的 `openssl::openssl` → shim 改为 `include(openssl-config.cmake)` 转发 + 暴露 `OpenSSL::Crypto`（注意 python `.format()` 需 `{{CMAKE_CURRENT_LIST_DIR}}` 转义）。
5. 签名工具路径写死 `/data/service/hnp/bin/binary-sign-tool`，真机实际在 `/storage/Users/currentUser/usr/local/bin` → `shutil.which(...) or 路径 fallback`。

### rule4 修复（上游测试真实执行，2026-10-15）
- **配方新增 `tests` option**（默认 False）：`-o xeus-zmq/*:tests=True` 时 `XEUS_ZMQ_BUILD_TESTS=ON` + `requires doctest/2.5.2`（ohpcd 已发布），构建全部上游测试二进制并在 `build()` 内真实执行 ctest。
- **真机执行结果**：`ctest --output-on-failure -R test_handshake` → `1/1 Test #4: test_handshake Passed (0.11 sec)`，`100% tests passed, 0 tests failed out of 1`；随后 test_package 7 断言同样通过，`conan create -o tests=True` 全流程成功。
- **上游测试构成（ctest 注册 4 项）**：
  - `test_handshake`（C++ 集成测试）：真实启动 `test_kernel_shell` kernel 进程，完成 kernel 注册 handshake + `kernel_info_request`/`shutdown_request` 消息往返 —— **真机已真实执行并通过**。
  - `test_kernel` / `test_kernel_control` / `test_kernel_shell`（pytest 驱动）：需要 pytest + jupyter_client + pyzmq 在 Python 侧 spawn 活 kernel 并走 Jupyter 消息协议 —— **未执行，技术原因**：真机 Python 3.12 无 jupyter_client/pyzmq（pytest 9.1.1 已装）；pyzmq 无 OHOS 预编译 wheel，源码构建需编译 libzmq Python 绑定（Cython + zmq 构建栈），超出三方库适配范围；且该 3 项为 kernel 协议级测试，属上游 Linux 桌面 CI 范畴。
- **Conan 2.31 工具坑**：`from conan.tools.cmake import CTest` 不存在（ImportError）；`CMake` 对象无 `build_folder` 属性 → ctest 用 `self.run("ctest ...", cwd=self.build_folder)`。

## 五、test_package 实质断言
`test.cpp`（7 项断言，真机运行通过）：
1. 校验安装头文件中的 `XEUS_ZMQ_VERSION_*` 宏为 4.0.0（3 项）；
2. 校验 `XEUS_ZMQ_BINARY_*`（SOVERSION）宏为 8/0/0，与 `libxeus-zmq.so.8` 一致（3 项）；
3. 调用真实 API `xeus::make_zmq_context()`，断言返回非空（创建 ZeroMQ 后端 context）。

## 五·一、知识草稿（路径 B 贡献创新）
- `knowledge/drafts/DRAFT-xeus-zmq-4.0.0-cmakedeps-consumer-view-mismatch.{md,kv}`
- 问题类：Conan 2 库消费链上 CMakeDeps 生成视图与上游 CMakeLists 期望不匹配
  （ConfigVersion 强制 major 对齐拒绝旧版本要求、命名空间 target 需 alias 桥接、
  header-only 包装库不传播底层库、openssl 无 config 需转发式 shim、签名工具双路径、
  版本范围语法、generators 声明缺失）。
- 通用性：适用于所有"消费多个已发布 Conan 库、上游 CMakeLists 直接链接无命名空间
  target / 依赖 header-only 包装库 / 依赖无 CMake config 库"的 Conan 2 配方
  （非 xeus-zmq 单库 case-by-case 补丁）。
- 查重：知识库 drafts 中无 CMakeDeps ConfigVersion major 对齐 / cppzmq header-only
  链接传播 / openssl config shim 主题条目（仅有库被消费侧的
  DRAFT-xeus-5.0-test-package-explicit-deps-target-compat 与签名工具运行环境的
  DRAFT-binary-sign-tool-buildenv-ldlibrarypath，主题互补不重复）。

## 六、下一步（真机空闲窗口排队）
```sh
# 单包 shadow CI（复用已验证的配方与分支）
CI_PACKAGES="archives/x/xeus-zmq/4.0.0" zsh ci/conan/build_and_test.sh
# 或 shadow runner
/path/to/run-ohos-shadow-ci.sh archives/x/xeus-zmq/4.0.0
```
真机重建命令（已跑通模板）：
```sh
cd $HOME/wt-xeus-zmq
export PATH="$HOME/.local/bin:/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:$PATH"
export TMPDIR=$HOME/wt-xeus-zmq/tmpbuild   # /tmp 只读，必须指向可写目录
conan create archives/x/xeus-zmq/4.0.0 -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing -c tools.build:jobs=2
```
构建日志存档：`$HOME/wt-xeus-zmq/build.log`。

## 六·一、上游测试执行命令（rule4 修复，真机已跑通）
```sh
# 需先装 pytest（test/CMakeLists.txt 的 find_program(PYTEST ... REQUIRED) 硬要求）
python3 -m pip install pytest
# 带 tests option 构建并真实执行上游 ctest（test_handshake）
conan create archives/x/xeus-zmq/4.0.0 -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing \
  -c tools.build:jobs=2 -o xeus-zmq/*:tests=True
# 日志：$HOME/wt-xeus-zmq/build_tests.log；期望输出：
#   1/1 Test #4: test_handshake ... Passed  0.11 sec
#   100% tests passed, 0 tests failed out of 1
```

## 七、对话记录
### 对话 #1 — 2026-10-04（本机前置）
**操作**: 创建 worktree、下载源码、分析 CMakeLists、编写配方与 test_package。
**结果**: 配方文件就绪；识别出 xeus 依赖缺失这一硬阻塞（不混入本 PR）。
### 对话 #2 — 2026-10-15（真机验证）
**操作**: xeus/6.0.5 已由他人适配并发布 → 真机 worktree 拉分支，逐次修复版本范围/CMakeDeps/版本要求/OpenSSL shim/签名路径。
**结果**: `conan create` + test_package 真机运行全部通过（HEAD 39af4bbf7e）；PR #15977 创建（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15977）。
### 对话 #3 — 2026-10-15（rule4 修复：真实执行上游测试）
**操作**: 审查 FAIL（rule4：上游 7 用例 0/7 未测）→ 配方新增 `tests` option（XEUS_ZMQ_BUILD_TESTS=ON + doctest 依赖），真机 `conan create -o tests=True` 构建全部上游测试二进制，ctest 真实执行 `test_handshake` 通过（1/1, 0.11s）；pytest 3 项因真机无 jupyter_client/pyzmq（pyzmq 无 OHOS wheel）给出技术原因。同步更新 PR 描述（上游测试通过率 1/4）、notes/manifest。
**结果**: 上游测试真实执行 1/1 通过；待推送 → /rebuild → CI → /ai review。
