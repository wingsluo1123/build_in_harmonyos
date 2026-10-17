# wdfs 1.4.2 适配笔记

## 基本信息

| 项 | 值 |
|----|----|
| 软件 | wdfs（WebDAV 用户态文件系统，FUSE 2.x） |
| 版本 | 1.4.2 |
| 上游 | https://github.com/codyps/wdfs（无 tag；版本以 master `configure.ac` `AC_INIT(wdfs, 1.4.2)` 与 `ChangeLog` 首条 1.4.2 确认） |
| 源码 | `https://github.com/codyps/wdfs/archive/3fa703545e384dca75417b01a45a534a253ef4c7.tar.gz`（固定 master HEAD 提交，2015-11-14） |
| sha256 | `6001cf77011a1d9e98a4e7734baba9fe58cd20363ff0de62c15290ca8346b237` |
| 构建系统 | autotools（tarball 自带 2015 年生成的 configure/Makefile.in，不需 bootstrap） |
| 依赖 | `libfuse/2.9.9`、`neon/0.34.0`、`glib/2.88.3.1`（`zlib/1.3.2` override） |
| 补丁 | 无（平台差异全部在配方 generate()/build() 内处理） |
| 产物 | `bin/wdfs`（`src/Makefile.am`: `bin_PROGRAMS = wdfs`），命令声明见 `archives/w/wdfs/commands.json` |
| 状态 | published（本地 conan create 全绿，见下） |

## 编译验证（本地 conan create，与 CI 同源 profile）

```
conan create archives/w/wdfs/1.4.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=missing
```

结果：**通过**（TMPDIR 日志 `$HOME/tmp/wdfs/w3-3.log`，5/5 断言）

> 注意：本机 shell 环境的 `CPPFLAGS=-I$HOME/usr/local/include`、`LDFLAGS=-L$HOME/usr/local/lib`、
> `LD_LIBRARY_PATH=$HOME/usr/local/lib` 会污染构建（见下表 #5），本地验证须
> `env -u CPPFLAGS -u CFLAGS -u CXXFLAGS -u LDFLAGS -u LD_LIBRARY_PATH` 对齐 CI 干净环境。

## 遇到的问题与解决方案

| # | 现象 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan graph` 报 `Version conflict: zlib/1.3.2 vs zlib/1.3.1` | `neon/0.34.0` 约束 `zlib/1.3.1`，`glib/2.88.3.1` 约束 `zlib/1.3.2`（其已发布 binary 按 1.3.2 构建） | recipe `requirements()` 加 `self.requires("zlib/1.3.2", override=True)`；zlib 补丁版间 API/ABI 兼容，仓库 1.3.2 为 `-fPIC` 静态版（不引入运行期 libz.so） |
| 2 | `fatal error: 'ne_props.h' file not found` | neon 公开头安装在 `<prefix>/include/neon/`，而源码用无前缀 `#include <ne_props.h>`；PkgConfigDeps 生成的 `neon.pc` 只有 `Cflags: -I<prefix>/include` | `generate()` 手写 `neon.pc`（`-I<prefix>/include/neon -I<prefix>/include`，与上游 neon.pc 约定一致），覆盖同名生成物 |
| 3 | `PKG_CHECK_MODULES(WDFS, [fuse >= 2.5.0 ...])` 无 `fuse` 模块 | libfuse 配方未定义 `pkg_config_name`，PkgConfigDeps 生成的是 `libfuse.pc` | 手写 `fuse.pc`（milepost：mtpfs 同款先例），只用于存在性/版本检查，真实链接闭包由 AutotoolsDeps 提供 |
| 4 | 运行期 `Error relocating .../bin/wdfs: pthread_setcanceltype: symbol not found`（rc=127） | OHOS musl libc 未导出 `pthread_setcanceltype`（`/system/lib64/libc.so` 只有 `pthread_cancel`、`pthread_setcancelstate`），而 `src/cache.c` 缓存回收线程调用它设置异步取消类型；`-Wl,--unresolved-symbols=ignore-all` 使链接成功但运行期解析失败 | 配方 `generate()` 生成语义兼容实现 `wdfs_libc_compat.c`（校验取消类型、按线程记录并返回旧值）编译为 `.o` 后随可执行文件链入；本平台取消类型保持缺省 `PTHREAD_CANCEL_DEFERRED`，取消仍由 `pthread_setcancelstate` 使能并在下一个取消点（缓存线程 `sleep()`）生效 |
| 5 | 运行期 `g_libintl_*: symbol not found`（仅本机出现） | 本机 `LDFLAGS=-L$HOME/usr/local/lib` 在链接行中先于 `LIBS`，`-lglib-2.0` 命中宿主 `libglib-2.0.a`（静态），其 i18n 引用 proxy-libintl 的 `g_libintl_*`；CI 干净环境下 `-lglib-2.0` 解析到 conan glib 共享库，无此问题 | 非配方缺陷：本地验证须 unset 宿主 `CPPFLAGS/LDFLAGS/LD_LIBRARY_PATH` 后复跑（复跑后仅剩 #4，修复 #4 后全绿） |
| 6 | `config.status` 生成临时目录不可写 | HMDFS 上 `umask 077 && mktemp -d` 造出构建用户写不进的目录（E011/E386，mtpfs/libfuse 先例） | `build()` 内联 `umask 077`→`umask 022`（configure 属 autoconf 生成物，refresh-patch 政策拒绝出补丁，故内联） |
| 7 | 上游 configure 写死 `/usr/local/lib/pkgconfig` | `configure.ac` 的 `export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH` 会把宿主前缀插到 pkg-config 搜索路径最前（本机该目录含同名 `glib-2.0.pc`） | `build()` 内联去掉该前缀，只保留 conan generators 目录（R49：不注入共享系统前缀） |

## 上游测试清点（R51 三步法）

* 源码树**无任何测试**：`find . -iname '*test*'` 空结果；`Makefile.am` 仅 `SUBDIRS = src`，`src/Makefile.am` 仅 `bin_PROGRAMS = wdfs` + `wdfs_SOURCES`；无 `TESTS` / `check_PROGRAMS` / `check-local` / `AC_CONFIG_TESTDIR`；`configure.ac` 无测试配置。
* 结论：**上游测试用例数 = 0**（无测试套件，非"未运行"）。
* 按 TEST_QUALITY_SPEC 补全自研消费者测试（`test_package/`）：`test.sh` + `webdav_stub.py`，共 **5 项断言**，通过率 **5/5 = 100%**：
  1. `wdfs --version` → rc=0，banner 含 `wdfs version: 1.4.2`
  2. `wdfs --help` → rc=1，打印 wdfs 选项帮助（同时验证 libfuse 符号闭合与 FUSE 参数构造）
  3. `wdfs`（无参数）→ rc=1，报 `missing webdav uri`
  4. **端到端消费者用例**：本地最小 WebDAV server（`webdav_stub.py`）就绪后运行 `wdfs -f <uri> <mnt>`，server 侧记录到真实 `OPTIONS /dav` 请求（`src/webdav.c: setup_webdav_session` 的 `ne_options`），证明 neon WebDAV 会话语路打通
  5. 同一用例进程正常结束（rc ∈ {0,1,124}，拒绝 126/127/139）

## 平台限制与功能边界

* 真实 FUSE 挂载需内核 `/dev/fuse` 可用；CI 沙箱中 `fuse: failed to open /dev/fuse: Permission denied`（属环境限制，测试以"server 收到 OPTIONS + 进程未崩溃"为通过条件，见 #4 用例）。
* 缓存回收线程的**异步**取消类型（`PTHREAD_CANCEL_ASYNCHRONOUS`）在本平台不可用（libc 无该符号），退回缺省延迟取消语义；线程阻塞在 `sleep()` 取消点上，退出时 `pthread_cancel` + `pthread_join` 仍可终止该线程，主功能（WebDAV 挂载读写）不受影响。
* neon 由仓库 `neon/0.34.0` 提供（静态、`--without-ssl` 适配版），故 `https://` WebDAV 资源的 TLS 能力取决于该依赖的既有适配结论，本包不做额外改动。
* **需人工确认适配完整性**：真实 FUSE 挂载（`/dev/fuse` 可用环境下的读写/属性/删除/MOVE 路径）与运行期 libc 对
  `pthread_cancel`/`pthread_setcancelstate` 的动态解析，CI 沙箱均不可达，仅由本地 conan create 的 CLI 分支 +
  WebDAV 端到端用例覆盖；上线前建议在具备 `/dev/fuse` 的真机上做一次挂载冒烟。
---

**编译结束**: 2026-10-16 20:28
**最终状态**: published
