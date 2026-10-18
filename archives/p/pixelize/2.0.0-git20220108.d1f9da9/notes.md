# pixelize 2.0.0-git20220108.d1f9da9 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure、无 install 目标）
- 编译日期: 2026-10-16
- 编译器: clang 15（OpenHarmony SDK llvm，交叉三元组 aarch64-linux-ohos）
- 状态: built

## 软件概况

pixelize — photomosaic builder（Paul Wilkins 2000-2009 / Jean-Christophe
Dubois 2020-2022，https://github.com/jcdubois/pixelize）：

- `make_db`（bin/）：把一组小图并入图像数据库 pic_db.dat
  （-r/--reset 重建，[FILE...] 逐个并入）。
- `pixelize`（bin/）：GTK3 GUI（glade 定义经 tools/glade2c 内嵌为 C
  字符串常量 include/pixelize_model.h），把输入图像重绘为由数据库小图
  拼接的马赛克；-i/-o/-m 进入命令行模式（-m command line mode）。
- 上游无 release tag：版本号 2.0.0 取自快照根 pixelize-2.0.0.lsm；
  d1f9da98ed4074f55db7c5ab4f701d70437810a3（2022-01-08）与 Debian
  pixelize_2.0.0~git20220108.d1f9da9 打包同一上游点。
- License: GPL-2.0-or-later（上游 LICENSE 为 GPLv2 全文）。

## 编译步骤

```bash
# 交叉编译（WSL，host=OHOS/armv8/clang15/libc++/cppstd17，build=x86_64 Linux）
cd /root/ohpcd-work/build/pixelize-2.0.0-git20220108.d1f9da9
conan create /root/ohpcd-work/wt-pixelize/archives/p/pixelize/2.0.0-git20220108.d1f9da9 \
    -pr:h ohos-aarch64-wsl-xbuild -pr:b default --build=missing
```

1. 配方 `source()` 拉 GitHub 官方 commit 归档（上游无 tag；sha256 见
   conandata.yml）
2. 补丁 0001：移除 Makefile 的 `-Werror` 与生成规则里的 `clang-format -i`
3. `build()` 用 conan 自带 Python 跑上游 `tools/glade2c` 预生成
   `include/pixelize_model.h`（构建环境无 clang-format；生成物 mtime 新于
   glade 输入，Makefile 规则不再触发）
4. `make -j1 CC=<conf>`（R9：HMDFS 不允许 jobserver FIFO）：Makefile
   反引号 pkg-config 经 PkgConfigDeps（gtk+-3.0/gmodule-2.0.pc）+
   tool_requires pkgconf（VirtualBuildEnv PATH）解析；**PKG_CONFIG_PATH
   由配方显式注入 generators_folder**（本 conan 2.29.1 的 PkgConfigDeps
   不设置该变量，AutotoolsToolchain 才设——纯 make 配方须自行注入，
   abiword-plugin-docbook/3.0.8 同款显式注入），depend 由
   `include depend` 自动重建
5. `package()` 手工拷贝 bin/{pixelize,make_db}、share/man/man1/*.1、
   licenses/LICENSE（上游无 install 目标）
6. `test_package/` 用 `sh test.sh <pixelize-bin> <make_db-bin>` 跑
   6 个端到端断言 + conanfile.py ELF e_machine 门禁

## 依赖版本

- gtk/3.24.43（pkg_config_name=gtk+-3.0，aris/2.2 同款钉版；broadway
  后端——适配鸿蒙无原生显示系统；glib 组件导出 gmodule-2.0.pc）
- pkgconf/3.0.5（tool_requires：pkg-config 可执行文件）

## 设计取舍

- `-Werror` 移除走 conandata 补丁（而非构建期文本替换）：Makefile 是
  上游真实源文件，源码修改透明可审计（Debian
  patches/Don-t-build-with-Werror 同源决策，bug #1117362）。
- pixelize_model.h 预生成而非依赖 Makefile 生成规则：规则里的
  `clang-format -i` 在构建环境不存在，tools/glade2c 的 shebang
  `#!/usr/bin/python` 也指向现代环境没有的解释器；预生成产物 mtime
  新于 glade 输入，规则不再触发（clang-format 只做代码排版，删去
  不影响生成内容的语义）。
- 上游 Makefile 的 `CLFLAS` 拼写错误行（GDK/GTK_DISABLE_DEPRECATED）
  从未生效，保持原样。
- GUI 无法无头运行（gtk 为 broadway 后端，需 broadwayd + 浏览器）：
  测试断言 --help（显示初始化前路径）、未知选项与无显示启动的失败
  路径（almanah/0.12.4 同款无头负向断言）。

## 上游测试清点（R51 三步法）

- 上游 pixelize d1f9da9 无自动化测试套件：Makefile 无 check/TESTS
  目标（目标清点：all/make_db/pixelize/obj/depend/clean）；快照 54 个
  文件中无 test_* 源文件；无 CI 配置。

### 测试四维账本

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static（上游静态声明） | 0 | 上游无自动化测试（清点证据见上） |
| N_registered（构建系统注册） | 0 | 无 check/TESTS 目标 |
| N_executed（实际执行） | 0 | 上游无测试可执行 |
| N_consumer（新增消费者测试） | 7 | test_package/test.sh 6 断言 + ELF e_machine 门禁 1 |

## 测试执行环境

- x86_64 交叉宿主经 `qemu-aarch64 -L /opt/ohos-guest` 用户态仿真执行
  aarch64 产物；conanrun env（VirtualRunEnv）提供 gtk/pango/cairo 等
  conan 依赖库路径。
- 产物与依赖链（cairo/expat 等）引用 OHOS musl 特有 fortify 与随机
  符号（`__strlen_chk`/`__memcpy_chk`/`__memchr_chk`/`arc4random` 等，
  上游 musl 无），qemu `-E LD_PRELOAD` 注入 4 个兼容 shim（冒号分隔，
  musl ldso 语法）：`libchkfcnshim.so`、`libmemchrchkshim.so`、
  `libpcmchkshim.so`、`libarc4shim.so`。
- CI OHOS worker（原生 aarch64 musl）直跑，无需仿真与 shim。

## 验证结果（2026-10-16）

- `conan create ... -pr:h ohos-aarch64-wsl-xbuild -pr:b default`：RC=0
  （export → patch → glade2c 预生成 → make 交叉编译 → package →
  test_package 6/6 断言 ok，ELF e_machine 门禁通过）。
- 产物加固（readelf，两二进制一致）：
  `Type: DYN`（PIE，`FLAGS_1: PIE`）、`GNU_STACK RW`（NX）、
  `GNU_RELRO` 段存在（partial RELRO，与仓内 vimpc/aris 基线一致）。

## 源码修改

补丁 1 个（patches/0001-makefile-drop-werror-and-clang-format.patch，
portability）：
- `-Wall -Wextra -Werror` → `-Wall -Wextra`
- 移除 pixelize_model.h 生成规则中的 `clang-format -i $@`

其余均为构建期注入（glade2c 预生成、CC 命令行覆盖），不修改上游源码。

---

**编译结束**: 2026-10-16
**最终状态**: built
