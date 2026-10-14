# DRAFT-synscan-5.02-conan-cwd-mismatch-makefile-export-header
> Conan 自建配方中 configure 与 make 的 cwd 不一致致 Makefile 落错目录及依赖导出头文件路径复位（自动工具类食谱通用解法）

## 问题特征（真实日志片段/标记）
真机门禁复现的稳定症状 fingerprint 与结构化指标几乎不变（attempt 50974 progress=unchanged），编译阶段失败：


make: *** No rule to make target 'linux'. Stop.


同时构建产物出现依赖头找不到的编译错误：


.../b/build-release/libpcap-stage/pcap.h:115:10: fatal error: 'pcap/funcattrs.h' file not found
1 error generated.


真机能力指纹（供环境口径判断）：`tmpdir=/storage/Users/currentUser/preflight/clients/.../tmp`、`make=/data/service/hnp/bin/make`、`cmake=4.1.2`、`install_shim=true`、`symlink=1`、`hardlink=0`。

## 根因
本条包含两个可泛化的内核：

1. **configure 与 make 的 cwd 不一致（Conan 通类瓶径）**。自建 autotools Conan 配方中，configure 命令未显式指定 cwd，Conan `self.run` 默认在 **build_folder** 执行，生成的 `Makefile`/`config.h` 落到 build_folder；而 `make linux` 使用 `cwd=self.source_folder`（该目录只有 `Makefile.in`，没有 `Makefile`）。make 找不到 Makefile，即报 `No rule to make target 'linux'`。已在空目录复现同款报错，并验证 in-source configure 后 Makefile 含 `linux` 目标且 `make linux` 能进入编译。
2. **依赖导出/暂存头文件落位与消费方 include 路径不符**。依赖（pcap）导出/暂存头文件实际落位与消费方 include 路径不匹配（如 pcap.h 引 `pcap/funcattrs.h` 而该头不在搜索路径），引发 `file not found` 的 compiler_error。

## 修复方案（rec）
编号步骤（HMBS_REPAIR_METHOD，rec_priority=1，方案经真机验证 attempt 50995 gateOutcome=passed）：
1. **对齐 configure 与 make 的 cwd**：在 `conanfile.py` 的 `build()` 中为 configure 命令补 `cwd=self.source_folder`，使其与 `make linux`（`cwd=self.source_folder`）处于同一目录，确保生成的 `Makefile` 落在 make 可见位置。
2. **复位依赖导出头路径**：核对依赖（pcap）导出/暂存头文件的实际落位目录，将其纳入 include 搜索路径（`include_dirs`/`includedir`），使消费方能够解析 `pcap.h` 引用的 `pcap/funcattrs.h`。
3. **真机复跑门禁**：保持更改未提交（HMBS 将在 preflight 通过后提交），复跑直至 `v2:compile:compiler_error` 消失、`remaining=[]` 且 gateOutcome=passed。

修复后 `sslog.c` 以 staged pcap 头成功编译为对象码，头部解析问题完全消除。

## 禁止策略
- 禁止 configure 与 make 使用不同 cwd 且 Makefile 落 build_folder 而 make 在 source_folder 运行——生成物落错目录，make 找不到 Makefile 即整轮构建失败（forbid_1_pattern）。
- 禁止依赖导出/暂存头文件落位与消费方 include 路径不符——include 找不到依赖头导致 compiler_error（forbid_2_pattern）。

## 与相近条目的边界（查重）
- `DRAFT-libb64-2.0.0-upstream-make-test-missing-library-target`：make 缺库目标，与本品 configure/make cwd 漂移为异因。
- `DRAFT-autotools-tmpdir-umask` / `DRAFT-autotools-config-guess-umask`：只读 tmpdir、config.guess/umask 均非本次根因（经验判断已排除），仅命中通用样板与相邻异因。
- 既有 DRAFT 无一涉 Conan cwd/落目录或导出头复位，本类问题现有技能库不覆盖，增量成立。

## 适用判断
适用于自建 autotools 类 Conan 配方中 configure 与 make cwd 不一致、以及依赖导出/暂存头文件落位与消费方 include 路径不符的 C/C++ 库。触发工具 conan|make|autotools，phase build|compile|dependency；severity=3（blocking），匹配关键词 `conan_cwd_mismatch`、`configure_make_source_folder`、`build_folder_makefile`、`staged_exported_header`、`dependency_header_path` 等。已通过真机门禁（attempt 50995 passed），具备入库证据基础。
