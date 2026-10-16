# lang-preflight 对"发行包源码嵌套在内层归档"的误判（weka 3.6.14 案例）

> 状态：DRAFT（路径 B 知识库扩展，待评审委员会审核）
> 来源：weka 3.6.14 适配评估 · 2026-10-16 · Agent: li_shuo

## 1. 问题场景

任务：适配 **weka 3.6.14**（Waikato 大学机器学习库）到鸿蒙PC aarch64-linux-ohos。

上游官方发行包为 SourceForge 的 `weka-3-6-14.zip`，解包后顶层：

```
COPYING  README  WekaManual.pdf  changelogs  data/  doc/
documentation.html  remoteExperimentServer.jar  weka.gif  weka.ico
weka.jar  wekaexamples.zip  weka-src.jar   ← 源码在这里
```

顶层**没有任何 .java/.c/.cpp 源文件**，真实源码（1357 个 `.java` + `build.xml`
+ `pom.xml`）嵌套在 `weka-src.jar`（jar 即 zip）内。

对发行包顶层跑 R47 语言预检，输出：

```
"detected_language": "nodejs",
"source_stats": "源文件 1 个（nodejs:1），主体占比 100%"
"build_system": "none"
```

—— 真实语言是 **java**，判定结果是 **nodejs**，纯属噪声：三级判定的前两级
（manifest、构建系统）落空后，源码统计只在顶层找到 1 个被归为 nodejs 的
散落文件，"主体占比 100%" 的统计显著性为零。

## 2. 根因

`lang-preflight` 假定 **解包根 = 源码根**。对"发行包 → 内层源码归档"的两层
打包结构（Java 库 `*-src.jar`、Python sdist 再套壳、tarball 套 tarball 等）
不成立：

1. manifest 级：顶层无 pom.xml/build.gradle（在 jar 里）→ 落空；
2. 构建系统级：无 configure/CMakeLists/Makefile → `none`；
3. 源码统计级：顶层散落 1~2 个非源码脚本被当作主体 → 任意语言噪声。

后果：`env_unsupported` 终态携带**错误的 detected_language**，平台的语言
迁移（lang_hold）分流方向错误；若真实源码是 C/C++ 的库也会被假阴性止损。

## 3. 与同类草稿的关系（similar_to）

| 草稿 | 根因 | 区别 |
|---|---|---|
| `roffit-0.17-lang-preflight-makefile-mixed-false-positive` | 顶层 Makefile 被当作 c manifest 与脚本统计冲突 → mixed | manifest 优先级误判，源码确实在顶层 |
| `kde-app-android-gradle-lang-misjudge` | `src/android/build.gradle` 辅助文件被 gradle 优先匹配 → mixed | manifest 优先级误判，源码确实在顶层 |
| **本条目** | **源码根本不在顶层，藏在 jar/内层压缩包里** | 扫描根定位错误，判定结果为随机噪声而非 mixed |

三条共同构成 lang-preflight 误判家族，但修复动作不同：前两条是"证据复核
覆盖检测器快照"，本条是"先修正扫描根，再预检"。

## 4. 推荐方案：extract-inner-archive-then-repreflight

1. **发行包体检**：顶层若存在 `*.jar`/`*.egg`/`*.whl`/内层 `*.tar.*`/`*.zip`
   且顶层源文件计数≈0，先解包内层归档（jar=zip）：
   ```bash
   python3 -c "import zipfile; zipfile.ZipFile('weka-src.jar').extractall('src-root')"
   ```
2. **对源码根重跑预检**，以第二次判定为准：
   ```bash
   python3 ohc-run.py lang-preflight weka 3.6.14 --src ~/tmp/weka-src
   # → detected_language=java, 1357 .java + build.xml + pom.xml, 证据一致
   ```
3. 两次证据一致（本例：java，构建系统 ant+maven）→ 按真实语言上报
   `env_unsupported` + `detected_language`（R47 激励：lang_hold 挂起等生态，
   非失败）；
4. 若解包后为 C/C++ 源码 → 正常进入适配主流程；
5. **禁止**删除内层归档/伪造 language_evidence 迎合检测器（R8/R10）。

## 5. 验证证据（weka 3.6.14 实测）

| 步骤 | 结果 |
|---|---|
| 顶层预检（错误扫描根） | `nodejs`，source_stats 仅 1 文件 ❌ |
| 解包 weka-src.jar | 1357 个 .java + build.xml + pom.xml |
| 源码根预检 | `java`（gradle/maven 构建系统），终态 `env_unsupported` ✅ |

## 6. 预期收益

- 一类打包形态（发行包嵌套源码归档）的预检误判有了标准处置流程，减少
  每次试错（本案例顶层误判 → 解包复检的排查路径沉淀为条目）；
- `detected_language` 上报质量提升：平台语言迁移不再被 nodejs 这类噪声
  误导；
- 与既有两条 lang-preflight 误判草稿互补，构成完整误判家族知识面。
