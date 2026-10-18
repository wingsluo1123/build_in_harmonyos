# kdesu 6.26.0 notes

## 背景

kdesu 是 KDE Frameworks 6 的提权抽象库，提供 `KDESu::SuProcess` /
`SshProcess` / `StubProcess` / `Client`（`libKF6Su.so`），并安装两个内部辅助
程序：`kdesud`（密码缓存守护进程）与 `kdesu_stub`（经 su/sudo/doas 拉起的
提权辅助 ELF）。本包是 **首次适配**（上游 main 与制品仓均无 kdesu，`conan
list kdesu/*` 实测 Found 0 recipes，R37 不适用），版本取与 KF6 **6.26** 系列
对齐的 6.26.0。

消费方：依赖 `KF6::Su` 的 KDE 提权前端；本批暂无可直接引用的下游卡，包本身
提交制品仓供后续前端使用。

## 依赖（W0 已核）

| 类型 | 依赖 | 制品仓状态 |
|------|------|-----------|
| required | `qtbase/6.11.1` | 已发布 |
| required | `kconfig/6.26.0.1` | 已发布 |
| required | `kcoreaddons/6.26.0.1` | 已发布 |
| required | `ki18n/6.26.0` | 已发布 |
| required | `kpty/6.26.0` | 已发布（`KF6::Pty` 是 KF6Su 的 PUBLIC 依赖） |
| tool_requires | `ecm/6.26.0` | 已发布 |
| optional | `X11` | OHOS sysroot 无此包，`find_package(X11)` 失败 → `HAVE_X11=0` |

## 平台事实（缺口核验）

- **X11 可选**：上游 `CMakeLists.txt` 的 `find_package(X11)` 非 REQUIRED；
  `config-kdesu.h.cmake` 的 `HAVE_X11` 为 0 时 `kcookie` 的 Xauthority 分支
  编译剔除，无需补丁。
- **pty 由 kpty 提供**：`SuProcess` 经 `KPty` 分配伪终端；头/符号在 sysroot
  齐全（kpty 6.26.0 记录），本包不重复上报。
- **符号探测全部成立**：`check_function_exists(setpriority/getpeereid/initgroups)`、
  `check_include_files(sys/select.h)`、`check_type_size("struct ucred")` 在 OHOS
  sysroot 均通过，生成的头宏无缺口。
- **R8**：本包 **零补丁**（`patches_applied: []`），不存在平台宏注入。
- **设备沙箱限制（非源码缺陷）**：真机沙箱禁止 pty 分配（`openpty` 被拒），
  且设备无 `su`/`sudo`/`doas` 可执行文件、当前 uid 20020084 无 passwd 条目。
  这直接决定上游 `kdesutest` 的实测结果，见下节。

## 适配要点

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单（OHOS 不在列表内）。
- `BUILD_SHARED_LIBS=ON`（`shared=True` 默认）、`BUILD_TESTING=ON`（上游
  autotests 随构建实跑）。
- **SONAME**：`os=OHOS` 时注入
  `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,`（kcodecs 6.26.0 /
  E330 先例）。设备 profile 另带 `no-versioned-soname` user_toolchain（/storage
  建链 EPERM），实测产出单文件 `libKF6Su.so`，`DT_SONAME=libKF6Su.so`，
  满足 L5a；包内 `*.cmake` 无 `IMPORTED_NO_SONAME TRUE`。
- `cmake_find_mode = none` + `builddirs = lib/cmake`：上游自带
  `KF6SuConfig.cmake` 会 `find_dependency(KF6Pty)`，必须让 CMake 使用上游
  config，而不是 CMakeDeps 替身。
- `ECM_MODULE_PATH` 手工设置（CMakeDeps 生成的 `ECMConfig.cmake` 不传递该
  变量）；`conan_cmakedeps_paths.cmake` 手工生成（qtbase 使用
  `cmake_find_mode=none`，CMakeDeps 不会把其 `lib/cmake` 加进
  `CMAKE_PREFIX_PATH`）。
- 配置/测试运行前把 `/system/lib64` 前置到 `LD_LIBRARY_PATH`（沙箱内不兼容
  的 `libc++_shared.so` 会遮蔽兼容版本，kconfig/kpty 6.26.0 先例）。
- **安装布局**：`kdesud` / `kdesu_stub` 安装到 `KDE_INSTALL_LIBEXECDIR_KF`，
  本平台实测解析为 `<prefix>/bin/kf6/`（ECM 在 WIN32 判定下以 BINDIR 为基准）。
  两者均为库内部调用的辅助程序，不是用户命令行工具；配方 `package_type=library`
  且无 `cpp_info.bindirs`，CI L0k 判为库包，**不需要 commands.json**（与
  kio/kservice 的帮手布局一致）。

## 上游测试申报（R51 三步法）

**第一步：清点**（解包 6.26.0 源码实测）

- 测试源：
  - `autotests/kdesutest.cpp` —— QTest 6 个功能槽
    `sudoGoodPassword` / `sudoBadPassword` / `doasBadPassword` /
    `doasGoodPassword` / `suGoodPassword` / `suBadPassword`（另有
    `initTestCase`），经 `ecm_add_test` 注册 CTest 目标 `kdesutest`；
    驱动 `SuProcess` 对 `autotests/sudo|su` 两个 python 夹具脚本提权。
  - `src/kdesud/autotests/kdesudtest.cpp` —— QTest 槽
    `commandWithDoubleQuotes`（`KDESu::Client::escape` 的词法往返），链接
    `../lexer.cpp`，CTest 目标 `kdesudtest`。
- **CTest 目标数 = 2**（`BUILD_TESTING=ON` 时均注册）。

**第二步：实跑** —— `build()` 调用 `_run_upstream_tests()` 分两段执行：

1. **硬门**：`ctest --test-dir <build> --output-on-failure --no-tests=error
   --timeout 300 -E "^kdesutest$"` —— 除环境受阻的 `kdesutest` 外全部目标
   必须通过；`--no-tests=error` 保证目标注册丢失（零测试）时构建失败，
   与 karchive/kapptemplate 配方惯例一致。
2. **已知豁免**：`ctest --test-dir <build> --output-on-failure
   -R "^kdesutest$" --timeout 300` 单独执行 `kdesutest`；非 0 时追加一条
   明确 warning（含 rc 与「已记录的缺口、不是通过」字样），不把失败伪装成
   通过（R51）。

**第三步：回填（真机 W3 实测 2026-10-17）**

- 实测结果：**2 个目标 / 1 通过**。
  - `kdesudtest` ✅ Passed 0.03s —— 词法往返用例通过。
  - `kdesutest` ❌ Failed 0.07s —— `initTestCase` PASS 后，6 个功能槽全部
    `FAIL!`。第一个失败点即：
    `kf.pty: Can't open a pseudo teletype` /
    `kf.su: [ src/ptyprocess.cpp : 136 ] Failed to open PTY.`，随后
    `'result == 0' returned FALSE`。所有 6 槽在同一处失败，测试在拉起
    su/sudo 之前就退出。QTest 汇总：`2 passed, 6 failed, 0 skipped`
    （2 个为 init/cleanup 基础设施槽）。
- 归因：**设备沙箱禁止 pty 分配**（`openpty` 路径被拒；本通道的交互链路也
  以 `pty.fork` 替代 `openpty` 可用）。此外设备无 `su`/`sudo`/`doas`
  可执行文件，当前 uid 20020084 也没有 passwd 条目，即便 pty 可用，端到端
  提权流程也无法完成。
- 处置：按实测如实申报（本文件 + `manifest.yaml` + `test_package/MANIFEST.yml`），
  **不宣称上游测试通过**；断言级覆盖由 `test_package/` 的真实消费者用例承担。
  真机日志中的 `kf.config.core: Couldn't write ... kdesu-consumer-testrc`
  是沙箱 HOME 不可写导致的持久化告警，不影响内存态配置语义（10 项检查全过）。

## 消费者测试（test_package）

`test_package/test.cpp` 是真实消费者用例（不是空壳断言）：以
`find_package(KF6Su)` + `target_link_libraries(test_kdesu KF6::Su KF6::ConfigCore)`
引入本包，共 **10 个检查点**：

1. `SuProcess` 默认 `super-user-command` 为 `su`
2. `sudo` 配置写入后被读回
3. `sudo` + root 时 `useUsersOwnPassword()` 为 true
4. `doas` 配置写入后被读回
5. 未知值回退到编译期默认 `su`
6. `SshProcess` 构造且初始提示为空
7. （安装检查）`kdesu_stub` 可启动
8. （安装检查）写入 `stop` 后进程正常结束
9. （安装检查）退出码 0
10. （安装检查）输出包含协议提示 `kdesu_stub` 与结束标记 `end`

第 7–10 项通过 `QProcess` 真实执行安装出来的 `kdesu_stub` ELF，覆盖
「安装产物可运行 + 协议安装检查」链路；CMakeLists 同时探测
`bin/kf6/`、`bin/`、`libexec/kf6/`、`libexec/` 四种布局（本平台实测
命中 `bin/kf6/kdesu_stub`）。

## 验证

- 源码 sha256 实测 `37df33a1236850b6bebd773a1aeab56ca597e347432924ca5855369337d4be24`
  （57156 字节，与官方 `.sha256` 一致），设备源缓存以该 sha256 播种。
- 真机 `conan create`（`ohos-aarch64-full` ×2）**成功**，包
  `e886653ed482c51d724fb6dbbae64215e92ef341`（recipe revision
  `75e7c11650674cad5d6bf2d831e1c0f7`）；打包清单：`lib/libKF6Su.so`、
  `bin/kf6/kdesud`、`bin/kf6/kdesu_stub`、8 个头文件、4 个 CMake 配置文件、
  `share/qlogging-categories6/ksu.categories`、60 个 `.mo`。
- `test_package` 实测：CTest `1/1 Passed`，`./test_kdesu` 输出
  `10 PASS / 0 FAIL`、`failures=0`。
- 上游测试实测见上节：2 目标 / 1 通过（kdesudtest PASS，kdesutest 因设备
  沙箱无 pty、无 su/sudo 而失败，如实申报）。
---
