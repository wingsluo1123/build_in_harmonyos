# DRAFT-rawrec-0.9.991-compiler-probe-replace-in-file-manual-audit
> 手写Makefile绝对路径先探测回退且漂移补丁改用配方内精确替换
## 问题特征（真实日志片段/标记）
- `make: /data/service/hnp/bin/clang: No such file or directory` + `Error 127`，`conan create`退出码1；此时`HMBS_BUILD_TOOLS`显示make在`/storage/Users/currentUser/usr/local/bin/make`而非`/data`路径。
- `Failed to apply patch 0001-makefile-respect-env-flags.patch, source file is different - src/Makefile, actual: CC = gcc`。
- `WARN: invalid hunk no.1 at 35 for target file b'b/src/audio_init.c'`与`invalid hunk no.2 at 67`及`patch stream is incomplete`。
- `HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh", "jobs":1}`环境下test_package硬编码`/data/service/hnp/bin/bash`失效；evidence门禁`no_tests/0 不允许通过`但上游存在`src/test_dsp_params.c`。
## 根因
- 配方直接取`tools.build:compiler_executables:c`绝对路径拼`make -j1 CC=...`且无`isfile+X_OK`校验，该路径在真机已失效；`test_package`同样硬编码shell绝对路径。
- 上游`src/Makefile`在`OPTFLAGS`与`CFLAGS`之间有注释块与空行，统一补丁首hunk上下文假设与真实字节不一致导致漂移；`0002`补丁hunk头新行数虚标为39/39/40而实际为29/29/30且空白行缺前导空格，被Conan严格校验拒绝。
- `src/test_dsp_params.c`经`OBJS=$(patsubst %.c,%.o,$(wildcard *.c))`链接进主二进制且仅提供`test_dsp_params()`生产ioctl逻辑、无harness，却被审计为测试缺失，`MANIFEST.yml`又用`auto`口径加非空`check`命令，不符合`manual_audit`空命令要求。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 在`archives/r/rawrec/0.9.991/conanfile.py`新增`_resolve_cc`与`_resolve_make`：conf绝对路径先校验`isfile+X_OK`，失效则warn并试同目录`clang`兄弟再试`PATH`中`clang/cc/gcc`；`make`优先`HMBS_MAKE`与`user.hmbs:make_path`并校验，回退`PATH`中`make/gmake`；`build()`改用解析后路径执行`make -j1 CC=<resolved> OPTFLAGS=-O0 DEBUGFLAGS=-g1`。
2. 删除漂移的`patches/0001-makefile-respect-env-flags.patch`并从`conandata.yml`移除条目，在`build()`中用`replace_in_file`做三处精确替换：`CC = gcc`改为`CC ?= gcc`、`CFLAGS`块改为`CFLAGS+=/CPPFLAGS+=/LDFLAGS?=/LIBS`追加语义、修正链接顺序；仅替换一次避免误改`debug`目标`CC = gcc-3.2`。
3. 用`git diff`重生成`patches/0002-soundcard-header-fallback.patch`，修正hunk头为`20,7/20,29`、`16,7/16,29`、`7,7/7,30`，空白行保留单空格前缀，经`git apply --check`验证。
4. 在`test_package/conanfile.py`新增`_resolve_shell`按`CONFIG_SHELL/SHELL`校验回退`/bin/sh`并末选`which sh`；`test_package/test.sh`改`#!/bin/sh`保持POSIX兼容，`commands.json`改为`sh test.sh`。
5. 重写`test_package/MANIFEST.yml`为`check/test`空命令加`manual_audit`口径，指名`src/test_dsp_params.c`为生产代码；同步`conanfile.py`中`HMBS_UPSTREAM_TEST_RESULT`为空`command`加详细`reason`、`notes.md`与PR描述。
6. `conandata.yml`将真机可用官方`SourceForge`地址前置、`ibiblio`保留回退，`sha256`逐字不变；`manifest.yaml`清理已删除`0001`残留记录。
## 禁止策略
- 禁止不经存在性探测直接使用绝对`CC/make/shell`：违例将复现`/data/service/hnp/bin/clang: No such file or directory`与`Error 127`。
- 禁止为漂移手写Makefile继续打统一补丁或虚标hunk计数：违例将复现`source file is different`与`invalid hunk`。
- 禁止将`test_dsp_params.c`生产文件计为上游测试或用`auto`口径加非空`check`放行：违例将致`evidence incomplete`。
## 与相近条目的边界（查重）
- 命中均为通用`HMBS_PLATFORM_CAPABILITIES`样板或异因异构建系统条目，与本任务`Error127`、hunk计数虚标、`test_dsp_params.c`生产代码`manual_audit`无实质重叠。
- 本条目跨库复用模式为：绝对`CC/make/shell`先校验`isfile+X_OK`再回退`PATH`兄弟与`HMBS_MAKE`，及统一补丁漂移时改用`replace_in_file`三处精确替换，不适用于`cmake/autotools`标准构建系统。
## 适用判断
- 当配方经`tools.build:compiler_executables`传入绝对`CC`且真机报`No such file/Error 127`时适用。
- 当手写Makefile配方用统一补丁改写`CC/CFLAGS/LDFLAGS`且上游含版本间易变注释空行时，改用配方内精确替换。
- 当上游仅含命名`test*`但实为经通配链接的生产代码时，指名文件并切`manual_audit`空命令。
