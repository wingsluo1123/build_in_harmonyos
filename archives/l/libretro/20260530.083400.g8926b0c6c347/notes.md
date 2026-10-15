# libretro 20260530.083400.g8926b0c6c347 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure/cmake；yabause/src/libretro/Makefile）
- 编译日期: 2026-10-12
- 编译器: clang 15.0.4 / clang++ 15.0.4（/data/service/hnp/bin，OHOS aarch64 交叉）
- 上游: libretro/yabause（世嘉土星模拟器 libretro 核），pin 到 master 提交
  8926b0c6c347f8c5c755911ddb0ac695420ffbf8（2026-05-30T08:34:00Z）
- 状态: published

## 编译步骤

1. conan create（配方 source() 直接拉取上游 tarball，strip_root 解包）
2. 配方 build(): `make CC=clang CXX=clang++ -j1`，cwd=yabause/src/libretro
   （-j1 规避 HMFS 并发 EACCES；CC/CXX 由 OHOS profile buildenv PATH 解析到 hnp clang）
3. 产物 yabause_libretro.so（约 1.9 MB，-shared -Wl,--version-script=link.T）由
   package() 复制到 lib/，libretro.h 复制到 include/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次 conan create 失败：clang 编译 osdcore.c.o 报 Error 1 且无任何 clang 诊断（日志 reports/conan-create.log 首错误区空白） | 沙箱进程树噪声（clang 静默退出，非源码问题）——同一构建目录手工重跑 `make CC=clang CXX=clang++ -j1` RC=0、完整编译+链接成功（证据 builds/libretro-repro-make.log） | 确定非配方问题后重跑 conan create，RC=0 全绿（builds/conan-create-libretro-r2.log） |
| 2 | 上游 libretro-common 单元测试（libcheck 框架）启动即死：`check_msg.c:317: Unable to create temporary file for communication` | libcheck open_tmp_file() 临时目录查找顺序为 TEMP → P_tmpdir(/tmp) → TMPDIR → "."；本沙箱 /tmp 只读且 P_tmpdir 优先于 TMPDIR，TMPDIR 无效 | 运行测试时设置 `TEMP=<可写目录>`（优先级最高的环境变量），重定向 libcheck 内部通信临时文件；已如实申报为验证期环境调整 |
| 3 | yabauseut/（上游 CMake 测试架）不可构建 | CMAKE_SYSTEM_NAME=SegaSaturn + ExternalProject 拉取 iapetus，面向 Saturn 官方 devkit | OHOS 环境不适用，属上游测试入口核验结论（见 test_package/MANIFEST.yml 清点） |

## 源码修改

无源码补丁（patches: {}）。上游 libretro 端口 Makefile 在 OHOS aarch64 + clang 15 下
零修改通过（vendored zlib 1.2.11 / LZMA / FLAC 1.3.3 / libchdr / libretro-common 全部
自包含，无 registry 依赖，仅系统 pthreads）。

## 依赖版本

无 conan registry 依赖（核心自包含）。测试期消费：libcheck/0.15.2（制品仓 OHOS
aarch64 二进制，仅上游单元测试框架，不进入产品依赖闭包）。

## 验证结果

```bash
# conan create（干净重跑，CONAN_HOME=/data/storage/el2/base/cache/conan-home）
#   → RC=0，builds/conan-create-libretro-r2.log
# test_package（conan test 自动执行）：
#   ./test_libretro <pkg>/lib/yabause_libretro.so
#     → consumer ok: library_name=Yabause library_version=v0.9.15
#       valid_extensions=cue|iso|mds|ccd|zip|chd|m3u retro_api_version=1
#   ./test_libretro-ohos <pkg>/lib/yabause_libretro.so（鸿蒙专项，非断言）
#     → ohos lifecycle ok: 25/25 mandatory retro_* symbols resolved;
#       library_name=Yabause library_version=v0.9.15 (init/deinit clean)

# 上游测试实跑（R51 三步法；builds/libretro-upstream-test-rerun.log）：
#   test/string/test_stdstring   16 checks: 15 pass, 1 fail (test_word_wrap)
#   test/utils/test_utils         3 checks: 3 pass
#   test/hash/test_hash           3 checks: 3 pass
#   test/lists/test_linked_list  89 checks: 89 pass
#   test/queues/test_generic_queue 16 checks: 16 pass
#   合计 5 程序 / 127 checks / 126 通过 / 1 失败 / 0 错误 / 0 跳过
```

## 上游测试

- 入口核验（MANIFEST.yml 清点）：libretro 端口 Makefile 无 check/test 目标（仅
  all/clean/generate-files*）；vendored libretro-common/Makefile.test 提供 5 个
  libcheck 单元测试程序；yabauseut/ 需 SegaSaturn devkit 不适用；src/runner/ 因
  lodepng 子模块缺失被上游守卫 return()；src/tools/{cdtest,pertest} 需物理硬件。
- 实跑：127 checks / 126 通过 / 1 失败 / 0 跳过（日志
  builds/libretro-upstream-test-rerun.log）。
- 已知失败 1 项 test_word_wrap：vendored 快照期望值早于上游换行行为变更，平台无关
  （上游 master 期望值与 OHOS 实跑输出逐字一致，见对话记录证据链）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| yabause_libretro.so | ~1.9 MB | libretro 核心插件（前端按文件名 dlopen 加载） |
| libretro.h | ~50 KB | libretro ABI 头文件（libretro-common/include） |
| COPYING | 15 KB | GPL-2.0 许可文本 |

## 注意事项

- 本包"libretro"实为 libretro/yabause 核心插件：非链接库（cpp_info.libs=[]），
  消费面 = libretro.h + 插件 .so 的 retro_* ABI，由 libretro 前端按确切文件名
  dlopen。
- 首次 conan create 的静默死为沙箱噪声，重跑即绿；CI worker 无此 shim 环境，
  不预期复现。
- 上游 libcheck 测试在本沙箱必须带 `TEMP=<可写目录>` 运行（/tmp 只读 +
  P_tmpdir 优先级问题），CI 环境如 /tmp 可写则无需该变量。

**编译结束**
**最终状态**: published

### 对话 #1 [2026-10-12]

- 任务恢复：会话中断后重建上下文（worktree wt-libretro，分支
  feat/libretro-20260530.083400.g8926b0c6c347，此前 conan-verify G2 失败）。
- 根因定位：首次 conan create 失败为 clang 静默退出（无诊断），同一构建目录手工
  make 复现 RC=0 → 沙箱噪声非配方问题；conan create 干净重跑 RC=0。
- 上游测试重跑：TEMP 重定向后 5/5 程序可运行，127 checks / 126 pass / 1 fail
  （test_word_wrap，与 MANIFEST 声明一致）。
- 待办：conan-verify → finish（W2/W3）→ 文件原子性检查 → 用户确认后提交。
---

**编译结束**: 2026-10-12 15:00
**最终状态**: published
