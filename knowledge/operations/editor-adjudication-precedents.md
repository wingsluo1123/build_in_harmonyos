# 主编裁定特征库（灰区裁定先例集）

> 来源：主编 25 批（2026-10-16~18）2970 接纳 / 676 拒绝中的 ~120 条人工灰区裁定。
> 用途：① 主编会话裁定参考；② 反哺 draft-review 的分类特征（后续可将本表
> 规则化为相似度分类器的豁免/加重项）。

## 推翻误判（工具判 dup 但实为不同问题 → 接纳）

| 模式 | 判定要点 | 实例 |
|------|---------|------|
| 不同头文件 | `byteswap.h` ≠ `argp.h`（各自库的 API 缺失，签名前缀相同但库上下文不同） | E581-BD15 vs E169 |
| 不同函数/符号 | `setcancelstate` ≠ `cancel`；`strlcat` ≠ `getpass`；`__fd_chk` ≠ `libc++_shared` | E591-4BC5, E1783, E2282 |
| 编译期 vs 运行期 | `implicit declaration`（编译）≠ `undefined symbol`（链接/运行） | E1574 |
| 平台识别 vs conftest 运行 | `config.guess unable to guess` ≠ `cannot run C compiled programs` | E1044, E3596 |
| 工具层不同 | `cmake_symlink_library` ≠ shell `ln -s`；链接期 `-l` ≠ 运行期加载 | E2609, E1321 |
| 跨域误匹配 | keyutils Python 模块 ≠ qsb；JAR ≠ C 头文件；GL ≠ l64a | E1449~E1453 |
| 结构体/宏不同 | `prctl_mm_map` ≠ `sockaddr_storage` 重定义；`LIBDIR` ≠ `VERSION` 宏 | E2468, E2913 |
| 工具 vs 模块缺失 | intltool 脚本 ≠ XML::Parser Perl 模块 | E3636 |

## 泛型补集（特定条目已存在，但泛型场景有独立价值 → 接纳）

| 模式 | 判定要点 | 实例 |
|------|---------|------|
| 泛型 so EPERM | `Error loading shared library <lib>` 泛型 vs libdconf 特定 | E2444 |
| 泛型 glibc 符号 | `(undeclared\|implicit).*symbol` 泛型 vs `secure_getenv` 特定 | E2127 |
| 泛型 version_conflict | `Conflict between .*/.* and .*/.*` vs zlib 特定 | E2746 |
| 泛型 Error 127 | `inaccessible or not found` 泛型 vs cmake 特定 | E1095 |
| 泛型 tr1/ 头 | `tr1/[a-z_]+\.h` vs `tr1/memory` 特定 | E2790 |
| 泛型目录式头 | `[a-z0-9_-]+/[A-Za-z0-9_.-]+\.h` vs libnova 特定 | E2941 |

## 确认重复（维持拒绝）

| 模式 | 判定要点 |
|------|---------|
| 同族 API 全变体 | std::ranges 各算法（all_of/find_if/format）判一族 |
| SIGSYS/SIGSEGV 泛型 | 泛型崩溃签名无诊断增量 |
| config.guess/cannot guess | 平台识别族已充分覆盖 |
| /tmp 只读族 | E002/E1190 已覆盖各文件形态 |
| 完全一致签名 | `register storage class` 等 jaccard≈1.0 |

## 裁定操作要点

1. 对比双方 `error_signature` 全文（不只前缀）——前缀相同但**实体名/阶段/工具层**不同 → 推翻
2. 工具 score < 0.7 的 merge-into 判定必须人工比对（批次 5-25 误判率约 30%）
3. "泛型 vs 特定"：特定条目存在时泛型仍可接纳（匹配面更广），但**泛型无诊断增量的崩溃类**除外
