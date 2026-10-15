# kamailio-websocket 6.0.6 适配笔记

## 编译环境
- 构建系统: makefile（kamailio 经典 Makefile 体系，src/Makefile + Makefile.defs）
- 编译日期: 2026-10-09
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，/data/service/hnp/bin/clang）
- 状态: built

## 任务身份
- task_id: kamailio-websocket-6.0.6-r01-pc3-4-20261009T094353Z
- executor: pc3-4
- source_branch: feat/kamailio-websocket-6.0.6
- worktree: /storage/Users/currentUser/worktrees/pc3-4-kamailio-websocket-6.0.6
- HEAD: 69a0f2f5c5697b72d3089c6d013d75e5eb4d59a7（创建自可审计 origin/main）

## 编译步骤

```bash
# 1) 实体化依赖（openssl + libunistring，OHOS aarch64 profile）
conan install --requires=openssl/3.5.7 --requires=libunistring/1.0 \
    -pr:h=<worktree>/ci/conan/profiles/ohos-aarch64 \
    -pr:b=<worktree>/ci/conan/profiles/ohos-aarch64 --build=missing

# 2) make cfg 生成 src/config.mak（探测 aarch64-unknown-linux-ohos 三元组）
make cfg include_modules=websocket SSL_BUILDER= CRYPTO_BUILDER= LOCALBASE=<openssl pkg> \
    extra_defs='-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD \
    -DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H -DHAVE_TIMEGM \
    -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN'

# 3) 编译 websocket 模块（CPATH/LIBRARY_PATH 注入 openssl+libunistring 头/库路径）
make modules modules=modules/websocket -j1 SSL_BUILDER= CRYPTO_BUILDER= \
    LOCALBASE=<openssl pkg> CPATH=<openssl include>:<unistr include> \
    LIBRARY_PATH=<openssl lib>:<unistr lib> extra_defs='<同上>'
```

产物：`src/modules/websocket/websocket.so`（约 4.8MB，aarch64 ET_DYN，NEEDED 仅 libc.so，
OpenSSL 与 libunistring 静态链入）。探索阶段验证：`file` 确认 aarch64 + 共享对象。

## 历史先例核验（W0b）

同版本 kamailio 6.0.6 模块级适配已有多个先例（分支 feat/kamailio-tls-6.0.6、
feat/kamailio-xml-6.0.6、feat/kamailio-unixodbc-6.0.6、feat/kamailio-snmpstats-6.0.6），
核心编译基础设施（make cfg 探测 aarch64-unknown-linux-ohos、LOCALBASE 钉死手法、
extra_defs 平台宏集、CI 绿）已趟通。本次环境语义与先例一致（同一 SDK/同一交叉编译器），
先例经验可迁移。websocket 与 tls 的差异：websocket 额外依赖 libunistring
（EMBEDDED_UTF8_DECODE=0 上游默认走 -lunistring），本配方经 CPATH/LIBRARY_PATH 注入
conan libunistring 包目录解决。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | resolve.h #error "neither gethostbyname2 or getipnodebyname present"；sched_yield.h 走 fake sched_yield(sleep(0)) 宏与 sched.h 声明冲突 | Makefile.defs 只有 linux/solaris/freebsd/darwin 等分支；OS=harmonyos 不注入任何 HAVE_* 探测宏 | make 命令行 extra_defs 注入 linux 分支等价宏集（见编译步骤）。每个宏先对照 SDK sysroot 头文件实证：gethostbyname2 (netdb.h:135, _GNU_SOURCE 守卫内)、sched_yield/sched_setscheduler (sched.h)、MSG_NOSIGNAL/msg_control (sys/socket.h)、timegm (time.h)、ip_mreqn (netinet/in.h)、alloca.h 存在 |
| 2 | websocket 模块链接 -lunistring 但系统无该库 | 上游默认 EMBEDDED_UTF8_DECODE=0 时 DEFS += -I$(LOCALBASE)/include、LIBS += -L$(LOCALBASE)/lib -lunistring | conan 制品仓 libunistring/1.0 已发布，经 CPATH/LIBRARY_PATH 注入包目录；LOCALBASE 指向 openssl 包满足 SSL 回退分支 |
| 3 | tls 先例用合并 prefix 目录，websocket 可用更简注入 | 单一 LOCALBASE 变量同时被 SSL 与 unistring 分支使用 | 方案对比后选用 CPATH/LIBRARY_PATH 双注入 + LOCALBASE=openssl（SSL_BUILDER=/CRYPTO_BUILDER= 钉死回退分支），make 命令行变量优先于 Makefile 内部赋值；验证产物 NEEDED 仅 libc.so |
| 4 | HAVE_UNION_SEMUN 取舍 | musl sys/sem.h 不导出 union semun 类型 | 不注入该宏：core lock_ops.h:160 在宏未定义时自带条件定义（实测编译通过），注入反而可能与 core 兜底定义冲突 |

## 源码修改

无。平台探测宏全部经 make 命令行 extra_defs 注入，未改任何源文件，0 补丁。

## 依赖版本

- openssl/3.5.7（conan 制品仓已发布，`conan download openssl/3.5.7 -r=ohpcd` 实测通过，
  二进制经 `conan install --profile=ci/conan/profiles/ohos-aarch64 --build=missing` 实体化）
- libunistring/1.0（conan 制品仓已发布，同样实体化）

## 上游测试清点（R51 三步法）

- 顶层无 test/ 目录；utils/kamctl/dbtextdb/tests/ 是 kamctl 工具的 Python 测试数据，与 websocket 模块无关
- src/modules/websocket/ 内仅源码 + doc/（config.c/websocket.c/ws_conn.c/ws_frame.c/ws_handshake.c
  + utf8_decode.h + README + doc/websocket_admin.xml），无测试源文件
- src/modules/websocket/CMakeLists.txt 无 add_test/enable_testing；顶层与 src/Makefile 均无 check 目标
- 上游 CI（GitHub Actions）走 pkg/kamailio 的 Smoketest（需运行中的 SIP 场景），非源码内自动化套件

结论：上游无 websocket 模块自动化测试套件（源码声明独立用例数 0）。适配侧测试为
test_package/check_websocket.py 产物结构校验（13 项断言：ELF aarch64/ET_DYN、
OpenSSL 静态链入符号证据、NEEDED 无 libssl/libcrypto/libunistring、u8_check 静态链入、
mod_register 模块入口、COPYING 随包、无 RPATH/RUNPATH 泄漏）。

## 验证结果

```bash
$ file src/modules/websocket/websocket.so
ELF shared object, 64-bit LSB arm64, not stripped
$ llvm-readelf -d websocket.so | grep NEEDED
Shared library: [libc.so]     # OpenSSL + libunistring 已静态链入
```

conan create 全量验证见 .ci-result.json（finish 自动写入）。

## 知识候选台账（knowledge_candidate_ledger）

| # | 候选（真实错误） | 根因 | 修复/方案 | 验证 | 适用范围 | 四范围查重结果 |
|---|---|---|---|---|---|---|
| C1 | `core/resolve.h:290 neither gethostbyname2...`；`sched_yield.h` 冲突 | OS=harmonyos 不在 Makefile.defs 的 linux/solaris/freebsd/darwin 任一分支，平台探测宏全部缺失 | make 命令行 `extra_defs` 注入 linux 分支等价宏集（-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD -DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H -DHAVE_TIMEGM -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN；不注入 HAVE_UNION_SEMUN） | 编译通过；宏符号逐一对照 OHOS SDK sysroot 实证 | 所有 kamailio 经典 Makefile 模块（同族 tls/xml 先例同法） | 正式 doc/ 0 命中；graph/index.tsv 0 命中；drafts 命中 DRAFT-12718（同机制二）、DRAFT-11941（探测链钉死）——部分覆盖，本轮无新增差异 |
| C2 | `cannot find -lunistring`；`unistr.h` No such file | websocket 模块 Makefile 上游默认 `EMBEDDED_UTF8_DECODE=0` 走 `-I$(LOCALBASE)/include -L$(LOCALBASE)/lib -lunistring`；单值 LOCALBASE 已指向 openssl，libunistring 无路径 | 主依赖 openssl 继续 LOCALBASE + SSL_BUILDER=/CRYPTO_BUILDER= 钉死回退；可选依赖 libunistring 经 CPATH/LIBRARY_PATH 注入（不采用 EMBEDDED_UTF8_DECODE=1，保持上游默认 RFC 6455 全量 UTF-8 校验） | conan create 13 项产物断言全绿；NEEDED 仅 libc.so；u8_check 符号存在 | kamailio websocket 模块及任何含可选依赖开关 + 单值 LOCALBASE 兜底的经典 Makefile 工程 | 正式 doc/ 0 命中；graph/index.tsv 0 命中；drafts 命中 DRAFT-12718（solution_overlap：同 CPATH/LIBRARY_PATH 注入族）、DRAFT-11941（同 trigger）——部分覆盖且存在新增差异（EMBEDDED_UTF8_DECODE 可选依赖取舍 + LOCALBASE=主依赖目录即可的变体），已验证可跨库复用 → 建立 DRAFT-12719 |
| C3 | 产物 NEEDED 仅 libc.so（openssl/libunistring 静态链入） | conan openssl/libunistring 包为静态库布局 | 无（自然结果）；test_package 以 NEEDED 集合 + u8_check 符号断言依赖形态 | readelf -d 实证 | 消费者测试断言依赖形态时不得要求运行时 .so 存在 | drafts DRAFT-11941 已记载同法（DT_NEEDED 核验）——完整覆盖，复用 |

### 七轴查重结论（C2 → DRAFT-12719）

- exact_duplicate: false（无同主题条目）
- causal_duplicate: false
- trigger_overlap: true（与 DRAFT-12718 同触发面：多依赖模块 + OS=harmonyos 宏缺失）
- solution_overlap: true（与 DRAFT-12718 同 CPATH/LIBRARY_PATH 注入族）
- combination_novelty: true（openssl+libunistring 双依赖 + EMBEDDED_UTF8_DECODE 可选依赖开关首次组合）
- boundary_novelty: true（LOCALBASE=主依赖目录即可、无需"不存在目录"技巧；可选依赖开关取舍边界）
- test_migration_novelty: false

### 路径决定

- knowledge_candidate: new_draft（DRAFT-12719-kamailio-websocket-6.0.6-embed-utf8-libunistring-dep-injection，.md/.kv 配对）
- relationship: similar_to=[DRAFT-12718, DRAFT-11941]；caused_by=[]；prerequisite_of=[]；conflicts_with=[]
- task_type=高难度挑战（路径 C）：PR 前缀保留【高难度挑战】；new_draft 配对通过不改变前缀
- reuse_existing: false（C1/C3 复用既有知识；C2 需新草稿）

---

**编译结束**: 2026-10-09 18:10
**最终状态**: built
