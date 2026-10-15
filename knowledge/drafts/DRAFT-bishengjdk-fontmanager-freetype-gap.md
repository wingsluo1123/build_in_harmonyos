# bishengjdk17 libfontmanager 缺 libfreetype.so.6：AWT/字体栈运行必败，消费者走 headless-safe 路径

- **问题类**: 平台运行库 NEEDED 供给缺口（musl 动态链接器解析失败）
- **机理分层**: L1 平台/工具链语义层（musl/libc 与平台库供给差异）
- **severity**: 2
- **状态**: DRAFT（建议编号 Exxx 由知识库主编确认，不自编号）
- **适用**: 任何在 OHOS PC 上触发 Java AWT/字体栈的消费者，与具体被移植库无关

## 现象

任何实例化 `java.awt.Font`、触碰 Swing 菜单/JavaBean 编辑器或间接引用 `sun.font` 的
Java 代码，在 OHOS PC 的 bishengjdk17 下运行即失败：

```
Exception in thread "main" java.lang.UnsatisfiedLinkError: ~/bishengjdk17/lib/libfontmanager.so:
  Error loading shared library libfreetype.so.6: (needed by ~/bishengjdk17/lib/libfontmanager.so)
  at java.base/jdk.internal.loader.NativeLibraries.load(Native Method)
```

失败发生在 `sun.font.SunFontManager` 的静态初始化内时升级为
`ExceptionInInitializerError`；同进程内后续触碰该类的代码全部得到
`NoClassDefFoundError` 连锁（上游测试实测 15 项连锁失败，逐条留档，均同根因）。

## 根因

完整因果机理链，每一环都有工具级证据：

1. **NEEDED 依赖在位**：`llvm-readelf -d ~/bishengjdk17/lib/libfontmanager.so` 列出
   `NEEDED Shared library: [libfreetype.so.6]`（另有 libawt.so、libjava.so、libjvm.so、
   libc++_shared.so、libc.so）。
2. **平台库缺失**：musl 动态链接器按 NEEDED 逐项解析；设备运行库目录
   （/usr/lib、/system/lib64、HNP 目录）均无 libfreetype.so.6。
3. **加载期硬失败**：dlopen libfontmanager.so 失败，JVM 抛 UnsatisfiedLinkError——
   该失败与 Java 代码写法无关，是平台供给事实。
4. **连锁放大**：失败点位于 `sun.font.SunFontManager` 的 `<clinit>` 内 →
   ExceptionInInitializerError → 同进程后续消费者 NoClassDefFoundError。

归类：平台运行库供给缺口，不是移植缺陷，也不是上游依赖问题。诊断价值：Java 测试
大面积 SunFontManager 连锁失败时直接归因设备字体栈，避免误判方向。

## 方案空间

### 推荐：headless-safe 消费路径（rec）

绕开字体栈而非修补它：

1. 类存在性断言一律用三参形式 `Class.forName(name, false, classloader)`——不触发静态
   初始化，避开 SunFontManager `<clinit>` 连锁；
2. 只实例化确认无 GUI/字体依赖的契约类（引擎类、启动器类），运行环境加
   `-Djava.awt.headless=true`；
3. 上游测试中真实触碰 AWT/字体路径的用例如实记录为平台缺口连锁——不修改测试 oracle、
   不预置答案、不整体跳过（逐条带原因留档）。

本范式在 jakarta-jmeter 2.13 的 test_package 全量实证：纯 JDK 反射消费者、
`StandardJMeterEngine` 无 GUI 实例化、NewDriver CLI 入口契约，断言全部通过。

### 退路（fallback，诚实权衡）

自供 libfreetype.so.6 实体并注入加载路径（LD_LIBRARY_PATH 指向自建库目录，或拷入
`~/bishengjdk17/lib/`）。权衡：HNP 无现成 freetype 包，需从源码自行构建；本 run 未验证
该路径；自编译 .so 还须过 ELF 签名门禁（与系统 JDK 同签名体系，见 P017/E083）；且只是
掩盖平台缺口而非修复供给——仅作确需 AWT 路径时的退路，并应向平台方提出库供给诉求。

### 反模式（forbid）

| 模式 | 原因 | 后果 |
|---|---|---|
| 假设平台 JDK 自带字体栈可用，直接实例化 java.awt.Font | NEEDED 缺失是加载期硬失败，与代码写法无关 | 运行期 UnsatisfiedLinkError + 同进程 NoClassDefFoundError 连锁 |
| 用二参 `Class.forName(name)` 做类存在性断言 | 触发静态初始化，把加载期失败放大为 ExceptionInInitializerError | "类是否存在"被误判为"类不可用"，诊断方向被引偏 |

## 自包含验证（设备新 shell 可复现，不依赖任何 run 日志）

```bash
# 1) 工具实现证据：NEEDED 项在位
llvm-readelf -d ~/bishengjdk17/lib/libfontmanager.so | grep NEEDED
#    预期首行: NEEDED Shared library: [libfreetype.so.6]
# 2) 库缺失证据
ls /usr/lib/libfreetype* /system/lib64/libfreetype* 2>/dev/null
#    预期: 无输出
# 3) 加载期定向复现
cd "$HOME" && printf 'public class FTProbe{public static void main(String[] a){System.out.println(new java.awt.Font("SansSerif",0,12).getFamily());}}' > FTProbe.java
~/bishengjdk17/bin/javac FTProbe.java && ~/bishengjdk17/bin/java FTProbe 2>&1 | head -3
#    预期: UnsatisfiedLinkError ... Error loading shared library libfreetype.so.6
# 4) 对照: headless-safe 路径不受影响
cd "$HOME" && printf 'public class OKProbe{public static void main(String[] a){System.out.println("headless ok " + (6*7));}}' > OKProbe.java
~/bishengjdk17/bin/javac OKProbe.java && ~/bishengjdk17/bin/java OKProbe
#    预期输出: headless ok 42
# 5) 清理
rm -f ~/FTProbe.java ~/FTProbe.class ~/OKProbe.java ~/OKProbe.class
```

## 去重说明（复判 6.4 修正口径）

同根因唯一性：`grep -il libfontmanager` 在 knowledge/drafts/*.kv 与 knowledge/graph/*.kv
中**仅本条命中**——"JDK 运行库 NEEDED 缺 libfreetype.so.6" 根因在知识库无同根因条目。
逐项命中清单（复判会话独立复跑，Builder 本轮再验一致）：

1. graph index.tsv：`freetype|fontmanager` **0 命中**；`font` 命中 E255/E305（字体
   **资源数据包**适配方法：资源数据打包/字体文件安装与校验）与 E471（GUI/display
   测试分类：gtk_init/Failed to open display/FONTCONFIG_FILE），均非同根因。
2. drafts：`freetype` 字样命中 **20 个 .kv（含本条自身）**——其中
   DRAFT-freetype-2.14.3.2.1-hmdfs-script-exec 根因为 HMDFS 拒绝脚本直接 exec
   （构建期 autotools 场景的 freetype 库移植），与 JDK 运行库 NEEDED 无关；其余为
   freetype.pc/config 脚本类字样命中。
3. 经验仓：`grep -rli freetype` **0 命中**。
4. 表面相似条目差异：E083 同为 UnsatisfiedLinkError 表面，但根因是 ELF 签名/权限
   （自签名 .so 在系统 JDK 下 Permission denied），本条是 NEEDED 缺失（Error loading
   shared library）；E316 同属动态链接器按 NEEDED/SONAME 解析失败族，但场景是 Conan
   包移动后自带库的 SONAME 实体缺失，本条是平台级 JDK 运行库缺口，消费侧无法通过
   打包修复。

本条为首条记录 bishengjdk17 运行库 NEEDED 缺口机理 + 自包含探针的条目。

## 已验证 / 未验证边界

- 已验证：探针 1-5 在真机新 shell 实跑通过；15 项连锁失败与单根因的对应关系经逐条
  复核；headless-safe 消费范式经 test_package 全量实证。
- 未验证：fallback 自供 freetype 路径（未构建、未过签名门禁）；图形栈经 XWayland 等
  远程显示方案下 libfreetype 是否仍必需（本 run 无显示环境，未测）。

## 关联

- principles: P017（ELF 签名必须与运行环境匹配——musl 动态链接器与 BiSheng JDK .so 加载）、P013（平台限制必须降级而非绕过）
- similar_to: E083、E316
- doc: drafts/DRAFT-bishengjdk-fontmanager-freetype-gap.kv（同目录成对）
