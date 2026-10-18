# jasmin-sable 2.5.0 适配笔记

## 打包环境
- **类型**: Java 应用（字节码汇编器）：`jasmin.Main` + 同包附带的 `jas.*` 字节码库
- **打包日期**: 2026-10-08
- **平台**: arm64-ohos（OpenHarmony PC）
- **依赖**: 无 Conan requires；**java-cup** 为编译期与**运行期**依赖 → 从 Maven Central 自取并随包提供
- **状态**: built

## 打包步骤（conan create 全流程）

```bash
conan create archives/j/jasmin-sable/2.5.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码（source()）
Debian orig tarball：`jasmin-sable_2.5.0.orig.tar.xz`（sha256 `14fc8d13…`），`strip_root=True`。
仓库含三处源码：`src/jasmin/`（汇编器本体）、`lib/jas/src/**`（同包附带的 jas 库）、
`generated/scm/**`（自动生成类）。

### 2. 为什么不跑 ant（也不需要重跑代码生成）
`build.xml` 里有 `build_parser`（跑 java_cup 生成 `parser.java`/`sym.java`）与
`autogen_run`（跑 autogen 生成 `generated/scm/**`）两段流程，但：
**这些**生成物**已经随 tarball 提供** —— 因此本配方直接用 `javac` 编译三处源码即可，
不必引入 ant、也不必引入"生成器"角色（java_cup 的**运行时**仍然必需，见下）。

### 3. java-cup：**运行期依赖**，必须随包提供
汇编器源码里有 `import java_cup.*;` 与 `import java_cup.runtime.*;`（`ReservedWords.java`、
`Scanner.java`、`parser.java`）→ 只把 java-cup 当"构建期 jar"会让产物在运行时报
NoClassDefFoundError。制品仓没有 java-cup → 按"构建/测试期依赖自取"口径从 Maven Central 取
`java-cup-11b-20160615-3.jar`（sha256 `b9e6f99a…`）并**放进 `libexec/`**，
`bin/jasmin` 包装脚本的 `-cp` 同时指向两个 jar。

### 4. 多源码集
`src/jasmin/*.java` 里 `import jas.*` → 编译时必须带上 `lib/jas/src`（本包按
`src` + `lib/jas/src` + `generated` 三处收集 `.java`）。

## 上游测试清点（R51）

| 项 | 值 |
|----|----|
| 上游测试 | **无**：`find -name "*Test*.java"` 为空；`lib/jas/tests/all.java` 是示例程序；`build.xml` 无 test 目标 |
| 结论 | 上游通过率记 **N/A**（如实披露，不虚构） |
| 消费者验证 | `test_package/check_jasmin.py` 4 项，含**端到端真跑**：`bin/jasmin Hello.jas` → 生成合法 `Hello.class` → `java Hello` 输出 `JASMIN_OK` |

## 实测结果（本地 conan create，2026-10-08）

```
jasmin-sable/2.5.0: [build] 编译 86 个 .java（src + lib/jas/src + generated）→ jasmin-sable-2.5.0.jar
[ok]   产物齐备：bin/jasmin（可执行）+ libexec/ 下 jasmin jar 与 java-cup jar（运行期依赖随包提供）
[ok]   jasmin jar 内含主类与 jas 包（jasmin/Main.class、jasmin/parser.class、jas/ClassEnv.class）
[ok]   端到端真跑通过：jasmin 汇编出合法 Hello.class 且 java 执行输出 JASMIN_OK
       （同时证明 java-cup 运行期可用、包装脚本 classpath 正确）
[ok]   证据：jasmin-sable-2.5.0.jar = 176202 字节 sha256=1cd6637bda04dd32…
[ok]   证据：java-cup-11b-20160615-3.jar = 124231 字节 sha256=b9e6f99a4c0d1b22…
[ok]   证据：JDK=/storage/Users/currentUser/bishengjdk17
checks=4 fails=0 skips=0
RESULT: PASS
```

- 上游通过率：**N/A**（上游无测试套件，清点证据见上节）
- 消费者校验：**4 项全部通过**（含端到端汇编 + 执行）

### 本轮实际解决的坑（都可复用）

1. **`java-cup` 是"运行期依赖"，不能只当构建期 jar**：源码 `import java_cup.*` / `java_cup.runtime.*`
   （`parser.java` 实现 `java_cup.runtime.Scanner`）→ 不随包提供会在运行时报
   `NoClassDefFoundError`。制品仓没有 java-cup → 从 Maven Central 取（钉 sha256）并放进 `libexec/`。
2. **老 Java 源码可能是 Latin-1（ISO-8859-1）**：实测两处字节 `0xA4`，用 `-encoding UTF-8` 编译报
   `unmappable character (0xA4) for encoding UTF-8` → 必须 `-encoding ISO-8859-1`
   （上游 `build.xml` 未指定 encoding，即依赖 javac 的默认平台编码）。
3. **老 ant 工程可以不跑 ant**：`build_parser`（java_cup 生成 `parser.java`/`sym.java`）与
   `autogen_run`（生成 `generated/scm/**`）的产物**都已随 tarball 提供** → 直接 `javac` 编译三处源码即可。
4. **多源码集要取全**：汇编器 `import jas.*` → 必须同时编译 `lib/jas/src`（本包共编译 86 个 `.java`）。
5. **我方包装脚本的一处 bug（如实记录）**：classpath 的第二个条目起初漏了 `$libexec/` 前缀
   （只剩文件名）→ JVM 找不到 cup 运行时，端到端报 `NoClassDefFoundError: java_cup/runtime/Scanner`；
   而**全量 java-cup jar 里其实有这些类** → 教训是"classpath 每个条目都要写全路径"，
   报错信息指向的"缺依赖"未必是依赖本身缺。

## 复用来源

- Java 包范式（JDK 三级解析 + javac/jar 直编 + jar 落 `libexec/` + `bin/` 包装脚本）沿用本会话的
  `archives/i/infomas-asl/3.0.5`、`archives/j/jakarta-servlet-api/6.1.0`；
- "构建/测试期依赖自取并钉 sha256"沿用 shunit2 / tape / junit 口径；本包进一步区分了
  **"运行期也需要的自取 jar"必须随包提供**这一点。
