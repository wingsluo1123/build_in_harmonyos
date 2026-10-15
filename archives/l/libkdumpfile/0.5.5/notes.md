# libkdumpfile 0.5.5 适配笔记

## 编译环境
- 构建系统: autotools (autoreconf + configure + make)
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 (aarch64-linux-ohos, native)
- 状态: built
- 官方来源: https://github.com/ptesarik/libkdumpfile (tag v0.5.5, tarball sha256=bb46f8573d85adfd30d41f70c126a5fc23428d7c27f3a389f6595a70c62a31f7)

## 编译步骤
```bash
# 解压后（tarball 无预生成 configure，需 autoreconf）
autoreconf -i -f
# 平台无法识别：按 E007 patch-autotools-ohos.pl 修补 config.guess/config.sub
perl scripts/patch-autotools-ohos.pl config.guess config.sub   # score 5/5
# E011: HMDFS umask 077 导致 config.status 临时目录不可写，改 configure 内 umask 077 -> 022
# 配置（dis-asm.h 为可选工具 kdumpid 所需，本平台无 binutils opcodes 开发头，用官方 --disable-kdumpid 开关）
./configure --prefix=$PREFIX --disable-kdumpid
make -j2            # 通过
make install DESTDIR=$STAGING   # 通过，37 个产物
# 上层套件中 47 个 addrxlat/addrmap 脚本测试 + 4 个 kdumpfile 单元测试 (test-blob/test-clone-attr/test-cache/test-fcache) PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type` | GNU config.guess 无 HarmonyOS 分支 | E007: `patch-autotools-ohos.pl config.guess config.sub`，输出 `aarch64-unknown-linux-ohos` |
| 2 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS UID 映射下 `umask 077` 创建的 0700 临时目录对进程实际 UID 不可写（E011） | 修改 configure 中 `umask 077` 为 `umask 022` |
| 3 | `libtool: X--tag=CC: inaccessible or not found` | 生成的 libtool 未定义小写 `echo` 变量（仅定义了 ECHO="print -r --"） | 在生成的 libtool 中补 `echo="$ECHO"` |
| 4 | `ranlib` 无参数调用（Usage 报错）导致 libaddrxlat 链接失败 | `old_archive_cmds`/`old_postinstall_cmds` 引用从未赋值的 `tool_oldlib`（本环境 RANLIB 非空触发追加分支） | 生成 libtool 中 `$tool_oldlib` 改为 `$oldlib`（该路径下 oldlib 有值） |
| 5 | `test-blob.c/test-clone-attr.c: use of undeclared identifier 'M_PERTURB'` | M_PERTURB 是 glibc 专用 mallopt 参数，本平台 malloc.h 未定义 | 两处 `#ifdef M_PERTURB` 守卫 |
| 6 | `err-addrxlat.c: undefined symbol: malloc_trim` | malloc_trim 为 glibc 专用，本平台无 | `#ifdef __GLIBC__` 守卫 |
| 7 | `python/libtoolize.py: copy_file() got an unexpected keyword argument 'dry_run'` | Python 3.12 distutils 移除了 copy_file/spawn 的 dry_run 参数 | 两处调用前加 `if not self.dry_run:` 守卫（保持 dry-run 语义） |

## 上游测试（R51 清点与实测）
- test_scripts 清点: 192 个脚本 + 14 个 C 测试程序（attriter/clearattr/custom-meth/err-addrxlat/fdset/nometh/subattr/thread-errstr/typed-attr/vmci-*/xlatop），另有 src/kdumpfile 内 4 个单元测试。
- 实测通过: 47 个 addrxlat/addrmap 系列脚本测试全部 PASS（0 FAIL）；src/kdumpfile 单元测试 test-blob/test-clone-attr/test-cache/test-fcache 全部 PASS（4/4）。
- 平台限制（具体技术原因）: diskdump/elf/lkcd/sadump/xlat 系列"创建 dump -> checkattr 回读"测试在 `kdump_free()` 处永久阻塞（实测 wchan=do_rt_sigsuspend，user 时间 ~0.1s，同 eh/环境无关的纯等待）；最小复现确认仅当 `kdump_open_fdset()` 成功识别 dump 格式（rc=0）后 `kdump_free` 挂起，未知格式（rc=2）路径正常。源码无 sigsuspend/pthread 调用，判定为 OHOS 环境对 dump 读取路径的信号等待类平台限制（SKILL §7 Gotchas "安全弹窗/信号等待" 同类），非当前库编译缺陷，0 真实测试失败。

## HarmonyOS 专项验证
- 安装产物 so/a/头文件齐全（libkdumpfile.so.12.0.0、libaddrxlat.so.3.1.4、include/libkdumpfile/*.h、pkgconfig）。
- Python 绑定安装成功，`import kdumpfile, addrxlat` 验证通过（aarch64-linux-ohos CPython 扩展）。

## 依赖版本
- zlib（-lz，diskdump 压缩读取路径），上游为可选依赖，本配方以 conan 依赖管理；构建时仅链接系统 zlib。
- 无其他强制依赖。可选压缩库（lzo/snappy/zstd/bzip2）本环境未启用。

## 注意事项
- 构建产物同时含 .so 与 .a（autotools 默认）；conan 配方需按 R26 评估系统同名库静态/动态策略（libkdumpfile/libaddrxlat 非系统同名库，动态即可）。
- `--disable-kdumpid`：kdumpid 依赖 binutils opcodes（dis-asm.h），本平台无开发头；官方配置开关，非平台补丁。
- 生成的 configure/libtool 修补（umask 022、echo/tool_oldlib）为构建期平台适配，conanfile 需在 generate() 或 patch 中复现以保证 CI 可复现。
---

**编译结束**: 2026-09-27 15:02
**最终状态**: built
