# jasmin-sable

## 软件描述
`jasmin-sable` 是 **Jasmin**：Java 字节码汇编器 —— 把人类可读的 `.j`/`.jas` 汇编文本编译成 JVM `.class` 文件。随包还带有同源的 **jas** 字节码库（`lib/jas/src`，被汇编器 `import jas.*` 使用）。GPL-2.0-or-later。

## 功能概述
| 产物 / 组件 | 作用 |
|---|---|
| `bin/jasmin` | 命令行入口（包装脚本）：`jasmin <file.jas>` → 生成 `file.class` |
| `libexec/jasmin-sable-2.5.0.jar` | 汇编器本体（`jasmin.Main`、`jasmin.parser` 等）+ 一并编译进来的 `jas.*` 库 |
| `libexec/java-cup-11b-20160615-3.jar` | **运行期依赖**（解析器运行时 `java_cup.runtime.*`），随包提供 |

## OHOS 适配

### 打包方式
- **不跑 ant**：上游 `build.xml` 的 `build_parser`（java_cup 生成）与 `autogen_run`（autogen 生成）两段产物**已随 tarball 提供** → 直接用 JDK 的 `javac` + `jar` 编译打包
- **多源码集**：`src/jasmin` + `lib/jas/src` + `generated/scm` 一起编译（汇编器 `import jas.*`）
- **java-cup 随包提供**：源码 `import java_cup.*` → 运行期必需；制品仓没有 → 从 Maven Central 取（钉 sha256）
- 产物落 `libexec/`（jar）+ `bin/`（包装脚本，自带 classpath）

### 关键攻坚点
1. **区分"构建期自取"与"运行期自取"**：java-cup 不只是构建依赖——不随包提供则运行时报 NoClassDefFoundError
2. **自动生成源码已在 tarball 里** → 不必引入 ant/cup/autogen 三段流程，javac 直编即可
3. **源码集要按 import 关系取全**：漏掉 `lib/jas/src` 会缺 `jas.*`
4. **上游无测试**：如实记 N/A；验证改为端到端真跑（汇编 + 执行生成的类 + 断言输出）

### 与 Linux 的差异
- 纯 Java 字节码，跨平台无差异；差异集中在**打包形态**（不跑 ant、jar + 运行期依赖一起提供）与**校验方式**（端到端汇编+执行）

## 依赖关系
- **Conan requires**：无
- **运行期依赖**：`java-cup`（`java-cup-11b-20160615-3.jar`，随包提供）+ JRE
- **构建期**：JDK（bishengjdk17）+ java-cup jar（同时用于编译 classpath）

## 版本记录
| 版本 | 状态 | 打包日期 | 备注 |
|------|------|---------|------|
| 2.5.0 | built | 2026-10-08 | 不跑 ant（生成物已随源码）；javac 直编三处源码；java-cup 随包提供；端到端真跑 |

## 参考资料
- 上游（Sable/soot 内的 jasmin）: https://github.com/Sable/soot/tree/develop/jasmin
- Debian 包页: https://tracker.debian.org/pkg/jasmin-sable
