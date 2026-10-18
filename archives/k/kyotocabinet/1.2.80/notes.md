# kyotocabinet 1.2.80 适配笔记

## 基本信息

- 上游：Kyoto Cabinet 1.2.80（fallabs 的 QDBM 后继）
- 官方站 `https://fallabs.com/kyotocabinet/` 已 404，源码改用官方权威镜像
  `https://dbmx.net/kyotocabinet/pkg/kyotocabinet-1.2.80.tar.gz`（SHA256 不变；
  Gentoo/Ubuntu ebuild 均以该域为 SRC_URI）
- SHA256：`4c85d736668d82920bfdbdb92ac3d66b7db1108f09581a769dd9160a02def349`
  （与 Ubuntu 官方 orig tar.gz MD5 08ff1dc20c27d1a76d5ff5147414ba1a 交叉吻合）
- License：GPL-3.0-or-later（tarball 内 COPYING 与 FOSSEXCEPTION/LINKEXCEPTION）
- 构建系统：autotools（configure.in + Makefile.in，后缀规则，无 VPATH）
- 依赖：zlib/1.3.1（压缩，上游默认开启）；lzma/lzo 关闭（无已发布依赖）

## 补丁

1. `0001-configure-umask-hmdfs.patch`：configure 检测临时目录可写性时使用
   `umask 077` 创建临时目录，HMDFS（鸿蒙 PC 用户态文件系统）上失败，报
   "cannot create a temporary directory"。改为 umask 022。基于纯净 1.2.80
   tarball 生成（本库旧骨架补丁含 check.in/check.out/AI-review 噪音，不可复用，
   已删除重建）。

## 构建要点

- 上游 Makefile 只有后缀规则（.cc.o），无 VPATH/`srcdir` 引用 → 必须源内构建。
  conanfile 里 `self.run("./configure", cwd=self.source_folder)`。
- `make -j1`：上游 check 目标共享 `casket*` 测试库文件且无目标间依赖声明，
  并行会竞争。
- configure 参数：`--enable-static --disable-shared --enable-zlib --disable-lzma --disable-lzo`。
- 本机手动验证阶段 libz 链接库缺失（仅 zlib.h 可用），注入 Conan 缓存 zlib 包
  `-I/-L` 后链接通过；Conan 配方中由 `AutotoolsDeps` 自动注入。

## 上游测试审计（L1）—— 全量 512 条命令通过

`make check` 展开为 11 个子目标、512 条 RUNENV 测试命令，全部实际运行且 0 失败：

| 子目标 | 命令数 |
|---|---|
| check-util | 38 |
| check-proto | 16 |
| check-stash | 9 |
| check-cache | 9 |
| check-grass | 9 |
| check-hash | 77 |
| check-tree | 77 |
| check-dir | 76 |
| check-forest | 76 |
| check-poly | 111 |
| check-langc | 14 |
| **合计** | **512** |

- 测试可执行 17 个：kc{util,proto,stash,cache,grass,hash,tree,dir,forest,poly}test +
  kc{hash,tree,dir,forest}mgr + kcutilmgr + kclangctest（另有 kccachetest 等）。
- 双口径：`source_declared_total=512`（Makefile check 目标逐条展开），
  `configured_executable_total=17`，`executed_passed_total=512/512 (100%)`；
  全量通过率 512/512 = 100%。
- 日志：/storage/Users/currentUser/tmp/logs-kc-check.txt（SHA-256
  4e716675162fd999cc3b72690b022d7029a75a06daabac94d4da19c4c2d67c85）。

## test_package（27 项断言）

create / write / read / overwrite / remove / iterate / close+reopen /
persistence / synchronize(fsync) / invalid path / corrupted header /
truncated file / cleanup removal。DB 文件只放测试构建目录，不关闭文件锁、
mmap 与同步——任何 HMDFS 不兼容都会暴露为失败。

## 消费者用例（1 个，硬门禁）

`reports/consumer/consumer.cpp`：模拟业务上层会话缓存组件，仅通过公开头文件
（kchashdb.h）与公开 API（HashDB::open/set/get/close/count、File::Status、
DB::Visitor）编译、链接、运行。实测：编译退出码 0，运行输出
`SESSION_LOADED user=alice expires=1789000000 count=1` + `CONSUMER_OK`，
退出码 0。产物 arm64 musl ELF。

## 平台行为验证（不掩盖兼容问题）

- 文件锁：kcfile.cc 使用 fcntl(F_SETLK/F_SETLKW) POSIX 记录锁，真机验证通过。
- mmap：kchashdb.cc 使用 mmap(MAP_SHARED) 映射数据文件，真机验证通过。
- 原子替换：kchashdb 写入用 write + ftruncate 原子更新头部字段，真机验证通过。
- 线程：kcthread.cc 用 pthread 全家桶（create/mutex/cond/TSD），真机验证通过。
- 持久化：test_package 显式 synchronize(true) 落盘 + 关闭后重开复验通过。

## 与连字符孪生 kyoto-cabinet 的关系

仓库内另有 `archives/k/kyoto-cabinet/`（同上游、同版本，2026-09-03 已发布）。
本目录为任务绑定名 kyotocabinet（无连字符）的完整适配，配方、补丁、测试
与消费者验证均为本轮独立完成，同 stem 知识查重见下节。

## 知识候选台账与七轴查重

| 候选 | 真实错误 | 根因 | 修复 | 验证 | 查重结果 |
|------|---------|------|------|------|---------|
| C1 configure 临时目录 | configure: cannot create a temporary directory | HMDFS 上 umask 077 目录创建失败 | 0001-configure.patch umask 077→022 | make check 512/512 通过 | **E011 正式条目完全覆盖**（edit-umask-in-configure，match_keywords 含 HMDFS/umask 077/confXXXXXX）；E206 同覆盖 → exact_duplicate |
| C2 源内构建 | make 在 build-release 找不到源 | 上游 Makefile 仅后缀规则、无 VPATH | conanfile cwd=self.source_folder | conan create G2 通过 | **E041 正式条目**（bypass-autotools，match VPATH）→ solution_overlap |
| C3 make check -j1 | 并行 make check 竞争 | 512 条命令共享 casket* 测试库文件 | -j1 串行 | 512/512 通过 | 无独立条目；库特性而非跨库模式 → trigger_overlap，无新增知识 |
| C4 conandata 注释 URL | W3 pre-download 提取注释 https URL → file:// 拼接损坏 → source() 失败 | build_and_test.sh 正则不区分注释行 | 注释不写 https URL（单 URL 原则） | W3 通过 | **DRAFT-8543 + DRAFT-8960 完全覆盖**（同根因同修复）→ exact_duplicate |
| C5 补丁尾换行 | conan patch_ng: patch stream is incomplete | 补丁文件末行无换行符 | 补丁以换行符结尾 | G2 通过 | **DRAFT-no-tail-newline-hunk-unappliable 完全覆盖**（patch_ng parse 异常、No newline at end of file）→ exact_duplicate |

### 七轴结论

- exact_duplicate: true（C1/C4/C5 被 E011/DRAFT-8543/DRAFT-8960/DRAFT-no-tail-newline 精确覆盖）
- causal_duplicate: true（C2 与 E041/E011 同根因：autotools + HMDFS）
- trigger_overlap: true（C3 与 E011 测试域重叠）
- solution_overlap: true（C2 与 E041 bypass-autotools 方案重叠）
- combination_novelty: false（无新组合）
- boundary_novelty: false（umask 补丁是已知平台差异的又一实例，无新边界）
- test_migration_novelty: false（上游测试原样运行，无迁移新意）

### 路径决定

`reuse_existing`（路径 A）：全部候选被既有正式条目（E011/E041）或既有草稿
（DRAFT-8543/8960/no-tail-newline）覆盖，无新增可跨库复用知识。完整重复时
复用已有知识并走路径 A，不新建草稿（不硬凑新增）。关联关系：
`similar_to=E011,E206,E041`；`caused_by=HMDFS umask 077 语义`；
`prerequisite_of=无`；`conflicts_with=无`。

**编译结束**: 2026-10-14
**最终状态**: built（待 CI 发布后升 published）
---

**编译结束**: 2026-10-14 17:05
**最终状态**: built
