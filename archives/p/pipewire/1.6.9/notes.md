# pipewire 1.6.9 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-10-18
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 官方源码 tarball（GitLab 归档）
# https://gitlab.freedesktop.org/pipewire/pipewire/-/archive/1.6.9/pipewire-1.6.9.tar.gz

# conan 最小化配置（关闭所有外部可选依赖，保留核心库 + spa 插件 + 测试）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

meson 关键选项（由配方 generate() 写入）：

```text
tests=enabled            spa-plugins=enabled        examples=disabled
docs=disabled            man=disabled               session-managers=[]
libsystemd=disabled      systemd-system-service=disabled
systemd-user-service=disabled
pipewire-jack=disabled   pipewire-alsa=disabled     pipewire-v4l2=disabled
alsa=disabled            bluez5=disabled            jack=disabled
dbus=disabled            sndfile=disabled           ffmpeg=disabled
vulkan=disabled          gstreamer=disabled         udev=disabled
```

与 1.4.9 的差异：上游 1.6.9 把 `systemd` 选项拆分为 `libsystemd` 与
`systemd-system-service` / `systemd-user-service`，三者均显式禁用。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pthread_cancel` 未声明 | OHOS libc (musl 系) 不提供 POSIX 线程取消 API | meson `cc.has_function('pthread_cancel')` 特性检测；data-loop.c 在缺失时把 cancel 分支改为与 cancel=false 相同的 `pw_loop_invoke(do_stop)` 唤醒停止路径，无信号、线程走正常 cleanup（信号处理器内 `pthread_exit` 在 musl 上不可靠，实测间歇崩溃） |
| 2 | `pthread_setaffinity_np` 未声明 | OHOS libc 无该 API | 特性检测 + thread_setaffinity 回退为忽略该亲和性请求（返回 0） |
| 3 | `dgettext`/`dngettext`/`bindtextdomain`/`bind_textdomain_codeset` 未声明 | OHOS libc 无 gettext 实现（libintl.h 仅头文件宏，无库） | 特性检测 + pipewire.c i18n 函数回退为原样返回 msgid |
| 4 | `rindex` 未声明 (test-config.c) | OHOS libc 无 POSIX 遗留 rindex | 改用标准 `strrchr` |
| 5 | open_memstream fseek 覆盖写不生效（test-spa-json.c `[[],` vs `[[]]`） | musl 的 open_memstream 在 fclose 时不保证缓冲同步；fseek 覆盖写需要显式 fflush | validate_strict_json 的 done 标签处加 `fflush(f)`；json_data 测试 fclose 前显式 fflush |
| 6 | open_memstream 无 fflush 时 fclose 后 free 触发 SIGTRAP (double-free) | musl open_memstream fclose 后内部缓冲状态与 glibc 不同，未 flush 时释放外部指针导致 double-free | json_data 测试在 fclose 前显式 fflush(fres)，保证缓冲所有权正常交接 |
| 7 | memfd `fstat` 返回 EACCES（test-pw-utils mempool_issue4884） | OHOS memfd 不支持 fstat（返回 EACCES），pw_memblock_map 因 fstat 失败返回 NULL | mem.c 仅在 fstat 失败为 EACCES/EPERM 时回退：先用 lseek(SEEK_END) 从 fd 读取实际大小（覆盖 pw_mempool_import 导入、本地未记录 size 的块，即 protocol-native MemFd 共享路径），fd 不可 seek 时再用已知 block size 做边界校验；其余 errno（EBADF/EINTR/EIO）保持原失败语义 |
| 8 | logger 文件输出立即读不到（test-support logger_truncate_long_lines 等） | musl 的 line buffering (setlinebuf) 仅对终端生效，普通文件流不自动 flush | logger.c 非 trace 路径 fputs 后显式 `fflush(impl->file)` |
| 9 | 构建到 721/775 失败：`ln: cannot create symbolic link ... pipewire-pulse: Permission denied` | HMDFS 拒绝 symlink 创建（EPERM）；src/daemon/meson.build 用 `ln -sf` 生成别名 custom_target，并用 `install_symlink` 安装别名 | custom_target 改用 `cp -f` 物化；`install_symlink` 改为 `meson.add_install_script` 在安装后复制 `bin/pipewire` |
| 10 | 安装期版本化 .so 符号链接同样会撞 EPERM | shared_library 的 `version`/`soversion` 会生成 libpipewire-0.3.so.0 → .so 符号链接链 | src/pipewire/meson.build 去掉 version/soversion，安装单个无版本 `libpipewire-0.3.so` |
| 11 | 安装后的 bin/pipewire、pw-cli 在真机执行报 `Operation not permitted`（EPERM） | OHOS 对已签名 ELF 做完整性校验；meson 安装期 `fix_rpath` 会抹掉构建树 rpath（X 填充 + .dynamic 清零，实测 111 字节变化），改动字节后 execve 直接 EPERM | 配方 `package()` 在 `meson.install()` 后用构建树里未被改动的原始 ELF 覆盖安装副本（含守护进程别名重新物化），保持签名有效；运行时库定位交给 LD_LIBRARY_PATH |
| 12 | 打包守护进程在 `$HOME/tmp` 启动时 `bind() failed with error: Operation not permitted` | HMDFS（用户主目录所在文件系统）拒绝 AF_UNIX `bind(2)`；`/tmp` 只读、`/data/local/tmp` 无权限 | test_package 在运行前探测可绑定目录（本机为 `/data/storage/el2/base`），探测成功则启动打包守护进程跑完整客户端连接 + sync 往返；探测不到时该用例报 SKIP，消费者流程改由 `pw_context_connect_self()`（上游 examples/tests 同款进程内图 API）执行 |
| 13 | 上游 `test-loop` 的 `cancel_thread_while_dispatching` 超时（meson test 15s 超时，exit 1） | 该用例的事件处理器在 dispatch 中 `for (;;) pause()`，靠 `pthread_cancel` 中断线程并触发清理；OHOS libc 无 `pthread_cancel`，唤醒停止路径无法中断阻塞中的 dispatch | `test/test-loop.c` 按上游 ABI 尺寸用例同款写法加能力门：`HAVE_PTHREAD_CANCEL` 缺失时该用例返回 `PWTEST_SKIP`（状态 SKIP，不计失败）；有该能力的平台原样执行 |

## 源码修改

共 11 个文件（相对官方 tag 1.6.9）：
1. `meson.build` — check_functions 增加 pthread_cancel / pthread_setaffinity_np / dgettext / dngettext / bindtextdomain / bind_textdomain_codeset 特性检测
2. `src/pipewire/data-loop.c` — 引入 `config.h` 使 `HAVE_PTHREAD_CANCEL` 在编译单元内可见；pthread_cancel 缺失时 cancel 分支改为 `pw_loop_invoke(do_stop)` 唤醒停止（无信号，线程走正常 cleanup）
3. `src/pipewire/thread.c` — 引入 `config.h` 使 `HAVE_PTHREAD_SETAFFINITY_NP` 在编译单元内可见；pthread_setaffinity_np 缺失守卫
4. `src/pipewire/pipewire.c` — gettext 系列缺失守卫（`bindtextdomain` 与 `bind_textdomain_codeset` 分别按各自的能力宏守卫）
5. `src/pipewire/mem.c` — memfd fstat 失败为 EACCES/EPERM 时用 lseek 取 fd 实际大小，取不到时回退 block size
6. `test/test-config.c` — rindex → strrchr
7. `test/test-spa-json.c` — open_memstream 显式 fflush（done 标签 + fclose 前）
8. `spa/plugins/support/logger.c` — fputs 后显式 fflush
9. `src/daemon/meson.build` — 守护进程别名由符号链接改为复制（构建树 + 安装期），安装脚本按 `bindir` 选项定位目标目录
10. `src/pipewire/meson.build` — libpipewire 去掉 version/soversion，单文件安装
11. `test/test-loop.c` — `cancel_thread_while_dispatching` 在 `HAVE_PTHREAD_CANCEL` 缺失时返回 `PWTEST_SKIP`（能力门，与上游 ABI 用例同款）

## 依赖版本

无外部 conan 依赖（核心库只依赖 libc/dl/pthread/m；可选外部依赖全部禁用）。

## 验证结果

真机（OHOS aarch64，clang 15.0.4）conan create 通过，test_package 共 7 个消费者用例全部 PASS：

```text
TEST PASS: library_version (1.6.9)   (test_pipewire, 1 个用例)
TEST PASS: mempool_memfd_map         (test_ohos)
TEST PASS: mempool_import_map        (test_ohos)
TEST PASS: data_loop_cancel          (test_ohos)
TEST PASS: consumer_self_connect     (test_ohos)
TEST PASS: daemon_exec_smoke         (test_ohos)
TEST PASS: daemon_client_e2e         (test_ohos)
TEST SUMMARY: 6 passed, 0 failed
```

`daemon_exec_smoke` 直接执行打包的 `bin/pipewire --version`（不可 SKIP，覆盖已签名 ELF
的 execve 检查）；`daemon_client_e2e` 在探测到的可绑定目录用 `mkdtemp` 建临时 runtime
目录，启动打包的 `bin/pipewire` 守护进程，客户端经 protocol-native 连接并完成 core sync
往返，结束后清理 socket 与 `pipewire-0.lock`；`consumer_self_connect` 走上游
examples/tests 同款 `pw_context_connect_self()` 进程内图 API（创建 stream、更新属性、
sync 往返）；`mempool_import_map` 覆盖从另一个 mempool 导入 MemFd 的映射路径。

构建树内运行上游测试套件：

```bash
meson test -C build-release  # Ok: 50, Fail: 0
# 子用例统计：198 PASS / 10 SKIP / 0 FAIL
#   SKIP 明细：logger_journal、logger_journal_chain（无 journald），
#             properties_abi/array_test_abi/buffer_abi_sizes/json_abi/utils_abi_sizes/
#             node_io_abi_sizes/pod_abi_sizes（框架对 ABI 尺寸测试的环境跳过），
#             cancel_thread_while_dispatching（无 pthread_cancel，能力门 SKIP）
```

安装树检查：`find <package> -type l` 为 0，`libpipewire-0.3.so` 单文件安装，
SONAME 为 `libpipewire-0.3.so`；`bin/pipewire-pulse|avb|aes67` 为真实副本。

## 注意事项

- OHOS libc 为 musl 系，与 glibc 的 open_memstream / setlinebuf / fstat(memfd) 行为不同，已在测试与 logger 中显式 flush 适配
- 特性检测优先于平台宏（不用 `__OHOS__`），保证可移植性
- 会话管理器 (session-managers) 默认 wireplumber 依赖外部，配置时显式禁用 `-Dsession-managers=[]`
- 1.6.9 相对 1.4.9 新增 `test-spa-format.c`（spa JSON 格式化测试），补丁 0008 的行号与上下文已按新源码重新生成
---
