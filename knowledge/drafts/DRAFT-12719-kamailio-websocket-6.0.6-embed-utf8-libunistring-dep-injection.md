# DRAFT-12719-kamailio-websocket-6.0.6-embed-utf8-libunistring-dep-injection — websocket 模块双依赖（openssl + libunistring）的依赖注入与 UTF-8 解码依赖取舍

> **Contributor**: pc3-4 | **Status**: DRAFT | **Updated**: 2026-10-09
> **Severity**: 🟡 warning | **Category**: build-system / cross-compile / ohos / toolchain / linking
> **Source**: 平台任务 kamailio-websocket-6.0.6-r01-pc3-4-20261009T094353Z（高难度挑战）
> **对应**: `knowledge/drafts/DRAFT-12719-kamailio-websocket-6.0.6-embed-utf8-libunistring-dep-injection.kv`
> **证据来源**: kamailio 6.0.6 官方源码包（源码级事实）+ HarmonyOS PC 真机（OHOS clang 15.0.4 / aarch64，Conan 2.29.1）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条目增量（差异化） |
|---|---|---|---|
| **DRAFT-12718** | 草稿 | 单值兜底变量 `$(LOCALBASE)` 在多依赖模块上结构性失配（lost 的 libxml2 + curl），方案是 LOCALBASE 指向不存在目录 + CPATH/LIBRARY_PATH 逐依赖注入 + 两阶段 OS=linux | 同属「多依赖模块」问题面，但本轮给出**变体实证**：LOCALBASE 可继续指向**主依赖**（openssl）包目录，第二依赖（libunistring）经 CPATH/LIBRARY_PATH 注入即可——不需要「不存在目录」技巧；且暴露**新依赖维度**：websocket 模块的 UTF-8 解码依赖是**可选项**（EMBEDDED_UTF8_DECODE 开关），上游默认 0 走 libunistring，这是 lost 没有的机制 |
| **DRAFT-11941** | 草稿 | kamailio 模块探测链（XML2CFG/BUILDER）被宿主工具链劫持，需命令行置空钉死回退分支 | 本条目沿用其「命令行变量置空钉死」手法（SSL_BUILDER=/CRYPTO_BUILDER=），但针对的探测入口不同（pkg-config libssl/libcrypto vs xml2-config），且叠加 EMBEDDED_UTF8_DECODE 分支选择 |
| **E090** | 正式 | meson 平台判决失效 | 不同载体（Makefile OS 分支），不重复 |
| kamailio 同族先例 tls/xml/unixodbc 的 manifest knowledge_gained | 已随各自 PR 记载 | 单依赖模块的 LOCALBASE 手法 | 单依赖手法在 websocket（双依赖）上不成立，本条目给出双依赖正解 |

> **查重（2026-10-09）**：`websocket` / `EMBEDDED_UTF8_DECODE` / `libunistring` / `u8_check` / `unistr.h` 在 `knowledge/graph/E*.kv` + `knowledge/drafts/**` + `knowledge/doc/**` 全文检索命中 0 —— EMBEDDED_UTF8_DECODE 与 libunistring 依赖注入此前无任何条目。
> 七轴：exact_duplicate=false（无同主题条目）；causal_duplicate=false（无同根因同解法条目）；trigger_overlap=true（与 DRAFT-12718 同触发面：多依赖模块 + OS=harmonyos 宏缺失）；solution_overlap=true（与 DRAFT-12718 同用 CPATH/LIBRARY_PATH 注入族）；combination_novelty=true（openssl+libunistring 双依赖 + EMBEDDED_UTF8_DECODE 可选依赖首次组合）；boundary_novelty=true（LOCALBASE=主依赖目录即可、无需不存在目录；可选项依赖取舍边界）；test_migration_novelty=false。

## Scope（何时用）

**适用**
- kamailio 6.0.6 websocket 模块（以及任何模块 Makefile 含 `EMBEDDED_UTF8_DECODE` 类**可选依赖开关** + 主依赖经 LOCALBASE 兜底的经典 Makefile 工程）；
- 更一般地：多依赖模块但**其中一依赖是可选开关**时，主依赖继续用 LOCALBASE 指向其包目录、可选依赖经 CPATH/LIBRARY_PATH 注入。

**不适用（反例）**
- 单依赖模块（kamailio-tls/slack/snmpstats）——LOCALBASE 兜底直接成立；
- 依赖全部必须且 ≥2 时，DRAFT-12718 的「LOCALBASE 指向不存在目录 + 全量 CPATH/LIBRARY_PATH」更稳妥；
- 依赖未发布（L0i/R36 层面）——前提是依赖已发布、包目录存在。

## 现象与稳定错误签名

| # | 报错（原文） | 暴露阶段 | 真实原因 |
|---|---|---|---|
| 1 | `core/resolve.h:290:2: error: neither gethostbyname2 or getipnodebyname present` | 编译 | `$(OS)=harmonyos` 不匹配任何 OS 分支 → 平台能力宏整体缺失（同 DRAFT-12718 机制二） |
| 2 | `cannot find -lunistring` / 头文件 `unistr.h` not found | 链接/编译 | 上游默认 `EMBEDDED_UTF8_DECODE=0` 走 `-I$(LOCALBASE)/include -L$(LOCALBASE)/lib -lunistring`，LOCALBASE 已指向 openssl 包目录，libunistring 头/库无路径 |

```text
error_signature: neither gethostbyname2 or getipnodebyname present|cannot find -lunistring|unistr.h: No such file
```

## 根因

`src/modules/websocket/Makefile` 上游原文（关键结构）：

```make
ifeq ($(EMBEDDED_UTF8_DECODE),0)      # ← 上游默认 0
	DEFS += -I$(LOCALBASE)/include
	LIBS += -L$(LOCALBASE)/lib -lunistring
else
	DEFS += -DEMBEDDED_UTF8_DECODE      # ← 内置 utf8_decode.h，无需外部库
endif
```

- 单值 `$(LOCALBASE)` 已用于 SSL 回退分支（`-I$(LOCALBASE)/ssl/include -L$(LOCALBASE)/lib -lssl -lcrypto`），同一变量无法同时承载 openssl 与 libunistring 两个包目录；
- 与 lost 不同，websocket 的 libunistring 依赖是**可选**的：设 `EMBEDDED_UTF8_DECODE=1` 可完全避开外部依赖（模块自带 `utf8_decode.h`）。

## 最终方案（本配方采纳）

1. **主依赖走 LOCALBASE，可选依赖走环境注入**：`LOCALBASE=<openssl 包目录>` 满足 SSL 回退分支；`CPATH=<openssl>/include:<libunistring>/include`、`LIBRARY_PATH=<openssl>/lib:<libunistring>/lib` 让 libunistring 头/库可寻址。不采用 EMBEDDED_UTF8_DECODE=1：保持上游默认行为（RFC 6455 全量 UTF-8 校验走 libunistring 的成熟实现），外部依赖已在制品仓发布，注入成本低。
2. **平台宏缺失沿用同族先例**：`SSL_BUILDER= CRYPTO_BUILDER=`（命令行置空钉死 pkg-config 探测）+ `extra_defs` 注入 linux 分支等价宏集（-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 ...，宏集与 kamailio-tls/xml 一致，逐宏对照 OHOS SDK sysroot 实证）。
3. **产物核验**：`readelf -d websocket.so` 断言 NEEDED 仅 libc.so（openssl+libunistring 均静态链入），无 RPATH/RUNPATH；`u8_check` 符号存在即 libunistring 静态链入证据。

## 真实验证

- 真机 `conan create`（两次独立运行）13 项产物结构断言全绿（readelf 存在时）（ELF aarch64/ET_DYN、SHA1/EVP_sha1/OPENSSL_init_crypto/OPENSSL_cleanup/mod_register/u8_check 符号、NEEDED 仅 libc.so、licenses/COPYING、无 RPATH/RUNPATH）。
- 产物指纹：`src/modules/websocket/websocket.so`（约 4.8MB，aarch64 ET_DYN，not stripped）。
- 上游测试：官方源码包唯一自包含测试 `utils/kamctl/dbtextdb/dbtextdb_test.py`（3 个 unittest 用例）实跑通过；websocket 模块自身无测试源、无 check/ctest 目标注册（notes.md 如实登记）。

## 交付关联

- 适配 PR：`feat/kamailio-websocket-6.0.6`（高难度挑战）
- 知识草稿：`knowledge/drafts/DRAFT-12719-kamailio-websocket-6.0.6-embed-utf8-libunistring-dep-injection.{kv,md}`
- 关系字段：similar_to=[DRAFT-12718, DRAFT-11941]；caused_by=[]；prerequisite_of=[]；conflicts_with=[]
- 完整台账：`archives/k/kamailio-websocket/6.0.6/notes.md`
