# gptfdisk 1.0.10 适配笔记

## 编译环境
- 构建系统: makefile（上游 consolidated Makefile，无 configure/CMake）
- 编译日期: 2026-10-01
- 编译器: clang 15.0.4 / clang++（/data/service/hnp/bin，profile conf 提供，R33）
- 状态: built

## 上游测试申报（R51 三步法）

| 指标 | 数值 |
|------|------|
| 上游测试总数 N | 21（检查级口径；唯一测试资产 = 单脚本 `gdisk_test.sh`） |
| 实际运行 N′ | 21 |
| 通过 | 21 |
| 失败 | 0 |
| 通过率 | **100%** |

**清点证据（第 1 步）**：`gptfdisk-1.0.10.tar.gz` 全量解包后——
- 无 `tests/`、无 `test/` 目录；非 CMake 工程（无 ctest 注册）、无 pytest 注册；
- 全树唯一测试资产是根目录单文件脚本 `gdisk_test.sh`（402 行）；
- Makefile 中 `test:` 目标 = `./gdisk_test.sh`（唯一测试入口）。

**实际运行（第 2 步）**：HarmonyOS PC（aarch64）真机执行
`sh ./gdisk_test.sh`（TMPDIR=$HOME/tmp）→ **rc=0，21 SUCCESS / 0 FAILED**。
脚本在 mktemp 临时 64MiB 镜像上驱动 gdisk + sgdisk 各 10 项场景
（建 GPT 表/建分区/改分区名/改分区类型/备份 GPT/删除分区/恢复备份/改磁盘
GUID/清 GPT 表/EOF 退出），另加 1 条临时盘创建，共 21 条断言。
证据: `~/tmp/gptfdisk-upstream-test-PC.log`（bash 与 sh 两种 shell 均复跑
通过）。conanfile.py `build()` 内已集成该脚本（can_run 时；任一 FAILED 或
rc!=0 即构建失败），并输出 `HMBS_UPSTREAM_TEST_RESULT` 标记。

**如实申报的口径备注**：脚本第 8 项“改磁盘 GUID”处两处写作
`NEW_DISK_GUID=get_diskguid`（赋值而非命令替换 `$(...)`），实际比较对象是
空串/字面量，属上游脚本自身缺陷 → 该项对 gdisk 与 sgdisk 两个二进制均恒真。
我们**不修改上游测试**，按原样运行并如实按 21 条计数；其余 19 条为真实断言。
上游 tarball 内不存在其他可运行测试套件（`fixparts`/`cgdisk` 无测试脚本）。

## 编译步骤

探索阶段（源码树内直接编译，验证工具链与依赖接线）：

```sh
cd $HOME/tmp/builds/gptfdisk-1.0.10.work
make -j1 TARGET=linux \
  CXX=/data/service/hnp/bin/clang++ \
  CXXFLAGS="-O2 -Wall -D_FILE_OFFSET_BITS=64 -I<shim> -I<三依赖 include>" \
  LDFLAGS="-L<三依赖 lib>" \
  LDLIBS="-luuid" SGDISK_LDLIBS="-lpopt" CGDISK_LDLIBS="-lncursesw"
# → gdisk / cgdisk / sgdisk / fixparts 四目标全部成功
```

固化为 conanfile.py 后：`ohc-run.py conan-verify gptfdisk 1.0.10`
（内部 `conan create -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 未应用 Linux 配置（LDLIBS/CGDISK_LDLIBS 为空，TARGET 未定义） | 上游用 `uname -s` 判定平台，HarmonyOS 不命中任何分支 | 用上游文档化的 `TARGET=linux` 开关（原生交叉编译选项，**零补丁**） |
| 2 | `gptcurses.cc:29: fatal error: 'ncursesw/ncurses.h' file not found` | conan ncurses 包头平铺在 include/（curses.h、ncurses.h），无系统式 `include/ncursesw/` 目录 | 私有 build_folder 内建 shim 头 `ncursesw/ncurses.h`（`#pragma once` + `#include <curses.h>`）；不改上游源码（audtty 先例） |
| 3 | `make -j4` 报 `jobserver mkfifo: ... Operation not permitted` | HMDFS 上 /tmp 只读（E002），GNU make jobserver FIFO 建不出来 | 按 R9 用 `-j1`（本项目规模下编译耗时完全可接受） |
| 4 | 普通镜像文件上 sgdisk/gdisk/fixparts 打印 `Error 13 when determining sector size! Setting sector size to 512` | 对普通文件 ioctl(BLKSSZGET) 失败，属预期 | 仅提示信息，rc=0 且功能正确；测试镜像即普通文件（与上游 gdisk_test.sh 同法） |
| 5 | `fixparts` 无参在无 TTY 时挂起等待键盘输入 | 交互式工具设计如此 | 测试中以管道/EOF 输入驱动，只断言 banner + MBR 加载路径 |

## 源码修改

无。0 个补丁（`patches: {}`），未改动任何上游源码文件。

## 依赖版本

| 依赖 | 版本 | 链接方式 |
|------|------|----------|
| libuuid | 2.42.2 | 静态（制品仓 shared=False，R26 系统同名库） |
| popt | 1.16 | 静态（同上） |
| ncurses | 6.6 | 静态（同上；R4 危险库，不产生 .so） |

## 验证结果

```text
# 编译（探索）
BUILD_RC=0；gdisk 338432 B / cgdisk 723456 B / sgdisk 354816 B / fixparts 121344 B

# 上游测试（R51）
sh ./gdisk_test.sh → rc=0；SUCCESS=21 FAILED=0

# 功能验证（自建 64MiB 镜像）
sgdisk -Z → rc=0；sgdisk -n 1:2048:+16M -t 1:8300 -c 1:TEST → rc=0
sgdisk -p/-i 1 → 列出 TEST 8300；gdisk -l → 同上
GPT 魔数 LBA1="EFI PART"；保护 MBR 签名 0x55AA
sgdisk -b 备份 → -Z 清空 → -l 恢复 → -p 分区回归（rc 全 0）

# R7 安全弹窗：gdisk/cgdisk/sgdisk/fixparts 均逐个执行（--version 等）
gdisk --version → "GPT fdisk (gdisk) version 1.0.10"
sgdisk --version → "GPT fdisk (sgdisk) version 1.0.10"
fixparts → "FixParts 1.0.10"；cgdisk 无 TTY → ncurses 初始化错误路径（预期）
```

## 注意事项

1. `cgdisk` 是全屏 curses 交互工具，无控制终端时无法完成自动化 UI 操作：
   测试断言其走到 ncurses 终端初始化错误路径（证明二进制可加载并进入
   curses 初始化），窗口交互本身需真实 TTY（设备上开发期已人工确认可启动）。
2. conan ncurses 包为静态库 + 平铺头；其他需要 `<ncursesw/...>` 的软件可复用
   本包的 shim 手法（见 `conanfile.py::_make_ncursesw_shim`）。
3. 上游 Makefile 的 `test:` 不经过 `make all`，`make test` 直接跑脚本；本包
   在 build() 里先 make 四工具再跑测试。
4. 制品仓中 libuuid 有 2.40.4 备用版本；本包按用户指定使用 2.42.2。

## 发现与知识

- ✅ 上游 gptfdisk 的 Makefile 用 `uname -s` 选平台，HarmonyOS 上必须显式
  `TARGET=linux` 才能拿到 Linux 默认链接库（这是上游文档化开关，不需要补丁）。已沉淀: knowledge/drafts/E545-draft-BA2E.kv
- ✅ conan ncurses(6.6) 头是平铺布局；`<ncursesw/ncurses.h>` 类包含需私有 shim。已沉淀: knowledge/drafts/E546-draft-8845.kv
- ✅ GNU make `-jN`（N>1）在 HMDFS 上因 jobserver FIFO 无法创建而退化为串行且
  打印告警；直接 `-j1` 更干净（与 R9 一致）。已沉淀: knowledge/drafts/E547-draft-9DFE.kv
- ✅ 普通文件镜像上 `BLKSSZGET` 失败（Error 13）是预期噪音，不影响 GPT 读写。已沉淀: knowledge/drafts/E548-draft-0712.kv

编译结束。
---

**编译结束**: 2026-10-11 23:54
**最终状态**: built
