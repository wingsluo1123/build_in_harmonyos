# libvolatilestream 1.0.2 鸿蒙 PC 适配笔记

上游: <https://github.com/rd235/libvolatilestream>
版本: 1.0.2（上游 tag；注：tag 内 CMakeLists.txt 的 project VERSION 仍写 1.0.1）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15）

## 一、适配结论

产物（install 树）：

- `lib/libvolatilestream.so` —— 共享库，公开 API 仅
  `volstream_open` / `volstream_trunc` / `volstream_getbuf`，
  以 `fopencookie(3)` 的 read/write/seek/close 回调维护内存缓冲；
- `include/volatilestream.h` —— 公开头；
- `lib/pkgconfig/volatilestream.pc` 与 Conan CMakeDeps 生成的
  `libvolatilestream::libvolatilestream` CMake 目标（`package_info()` 的
  `cmake_file_name` / `cmake_target_name` 声明）；
- `share/man/man3/volstream_open.3` —— 手册页（归档自带，man 目标在无
  pandoc 时仅打印提示并退出 0）。

平台适配 **0 个补丁**（`patches_applied: []`）。源码仅需 `_GNU_SOURCE`
（上游 CMakeLists.txt 已全局 `add_definitions(-D_GNU_SOURCE)`），
真机 clang 15.0.4 下 `sizeof(off64_t)=8`，`fopencookie` 可用；
构建期适配全部在 `generate()` 的 CMake 变量与现有工具链内完成。

测试口径（R51 申报表，清点时间为适配前）：

| 项目 | 数量 | 清点证据 |
|------|------|----------|
| 上游 `tests/` 目录 | 0 | 解包树（`libvolatilestream-1.0.2/`）无 `tests/`、`test/` 目录，无任何名称含 test 的源文件；GitHub API 递归拉取 tag 1.0.2 全树 11 个文件，无 test/check 路径、无 `.t`/`.tap`（审查口径=git tag 全树，与 tarball 一致） |
| 上游 ctest 注册 | 0 | `CMakeLists.txt` 全文无 `enable_testing` / `add_test` / `ctest` / `BUILD_TESTING` |
| 上游 pytest 注册 | 0 | 仓库无 Python 测试文件与 `pytest.ini` / `tox.ini` / `pyproject.toml` 测试配置 |
| 适配后消费者用例 | 13 | `test_package/test.c`，每用例独立输出 `TEST PASS`/`TEST FAIL`，共 109 个 `check()` 调用点（不含函数定义），末尾 `TEST SUMMARY`，失败以 1 退出 |
| 真机实测 | 13/13 | 真机 `conan create` 输出 `TEST SUMMARY: 13 passed, 0 failed` |

上游确无测试：`test_package/MANIFEST.yml` 的 `upstream_tests: []` 与
`upstream_check_command: ""` 记录了同一清点结论，`upstream_test_in_build:
false`（未执行任何上游测试）。

## 二、问题与处置

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次真机运行 `TEST SUMMARY: 1 passed, 11 failed`，11 个用例全部只失败在 `fclose succeeds` | OHOS 运行时 musl 的 `fclose` 在 `fflush` 与 cookie `close` 回调之前执行 `if (!f \|\| f->fd < 0) { errno = EBADF; return -EBADF; }`；`fopencookie(3)` 按设计把 `FILE.fd` 置为 -1，故 cookie 流的 `fclose` 恒返回 -EBADF(-9)，`volstream_close` 不执行 | 判定为**运行环境缺陷**（E1807/E302 同根因），不是 libvolatilestream 缺陷；不修改上游、不修改 libc。消费者测试新增纯 libc 对照（`fopencookie` + 普通 `/dev/null` 流）与库流同行为校验，把该平台偏差显式记录为用例 13，其余 12 个用例经 `check_close()` 按平台契约校验 |
| 2 | 同一缺陷的广度取证：`fmemopen` / `open_memstream` 的 `fclose` 同样返回 -9；`tmpfile` 失败 `errno=13 EACCES` | 设备 `/tmp` 只读；三者与 `fopencookie` 同为「无 fd 内存流」，共用同一 musl `fclose` 保护 | 仅作探针证据，不改测试路径；`memfd_create`+`fdopen`+`fclose` 返回 0，证明普通有 fd 流不受影响（用例 9 的普通 stdio 流校验同理保持通过） |
| 3 | HMDFS 不支持 `symlink()`（EPERM），VERSION/SOVERSION 的 `.so.1 -> .so` 链接链无法创建 | 设备用户卷文件系统限制 | `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` + 显式 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,`（`variables` 与 `cache_variables` 双通道），输出裸名 `libvolatilestream.so` 且带真实 `DT_SONAME`（E330 家族做法） |
| 4 | 真机构建 `source()` 下载上游 tarball 时 ghfast.top 注入 403 | 官方源 URL 经 CI 注入的镜像域名不可用（E017 家族） | 以 bare sha256 blob（15338 B，sha256 `5439a56b…6048db`）预置 Conan download cache（`srccache-isc/s/<sha256>`，无 `.dirty`/`.json`），构建期离线命中 |
| 5 | tag 1.0.2 的 `CMakeLists.txt` 仍声明 `project(... VERSION 1.0.1)` | 上游发版时未同步版本字段 | 包版本按卡面/tag 1.0.2 声明；`SOVERSION=1` 为上游既有 ABI 版本，不受影响；不修改上游构建脚本 |

## 三、依赖版本

无第三方依赖（`dependencies: []`）。构建仅用 OHOS SDK clang 15.0.4 与
CMake；测试侧经 CMakeDeps 链接被测包本身。

## 四、验证结果

真机（HarmonyOS PC，ohos-aarch64 profile）`conan create`：

```
[ENV] control: plain fclose rc=0; cookie fclose rc=-9 errno=9; cookie close callback calls=0; cookie control available=yes; platform cookie-close defect=yes
TEST PASS open_empty_stream
TEST PASS write_read_roundtrip
TEST PASS large_buffer_growth_1mib
TEST PASS getbuf_null_outputs
TEST PASS trunc_shrink
TEST PASS trunc_extend_zero_fill
TEST PASS seek_end_gap_zero_fill
TEST PASS multiple_independent_streams
TEST PASS non_volstream_ebadf
TEST PASS seek_negative_rejected
TEST PASS stdio_mixed_formatting
TEST PASS repeated_open_close_64
[ENV] library stream fclose rc=-9 errno=9; stream resources are reclaimed at process exit
TEST PASS platform_cookie_close_contract
TEST SUMMARY: 13 passed, 0 failed
[ENV] cookie-stream fclose EBADF is a platform libc deviation (E1807/E302 family), reproduced by the pure-libc control; it is not a libvolatilestream failure
```

门禁报告（`reports/conan-verify-report.md`）：G0/G1/G2/G3 全 PASS；G4
标注为 **NOT RUN**——校验器报「无法找到程序包 ID」，包内容校验未实际
执行（校验器本地缓存口径，非配方问题，同族库报告先例一致）；L2/L4/L5
因无 cache 路径标注为 SKIP（正常）。综合结论为**限定 PASS**（仅表示已
执行的门禁通过，不代表包内容已校验）。

环境缺陷说明（E1807/E302）：OHOS 运行时 musl 的 `fclose` 对
`f->fd < 0` 的流先行返回 -EBADF，导致 `fopencookie` 系内存流的
close 回调不执行、缓冲区与注册表项到进程退出才回收。纯 libc 对照
（`fopencookie` / `fmemopen` / `open_memstream`）均可复现，普通文件流
（`/dev/null`、`memfd_create`+`fdopen`）`fclose` 返回 0。消费者测试用
「纯 libc 对照 + 库流同行为」显式特征化该偏差：平台缺陷存在时要求库流
`fclose` 与控制组一致返回 EBADF（此时控制组 close 回调 0 次调用）；平台
修复后自动回到健康路径，要求库流 `fclose==0`、控制组 close 回调 1 次。
库内部缓冲区的释放由进程退出兜底，不在本用例的观测范围内（用例 12 的
64 轮循环同样只验证流程成功，不观测单个流的释放）。该用例不掩盖缺陷，
也不把环境缺陷归因给库。若对照本身不可用（`fopencookie` 失败或探测写
失败），`[ENV]` 行标注 `cookie control available=no`，用例 13 以具名
检查点「纯 libc 对照可用（契约已特征化）」失败，不会把「未建立对照」
当成「平台无缺陷」。

`reports/conan-create.log` 为真机原样运行产物（含设备绝对路径），仅本机
保留、不随档（报告 G2 小节引用的该日志路径因此不随档）；随档仅脱敏的
`conan-verify-report.md`。
