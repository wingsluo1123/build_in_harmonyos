# draft-conandata-build-tools-pinned-self-supply

设备缺失构建工具时应以 conandata `build_tools.*` 钉源自供给（先探测复用、后下载校验），勿依赖预装或人工安装。

申报域：工具链行为（构建工具供给；跨构建系统语义）｜分层：L2（配方树 9 处同模式在库先例）

## 症状

目标执行环境（OHOS 真机 / 权威 CI worker）没有可供 CI 使用的构建工具，上游 tarball 又不携带
wrapper 时，配方在工具探测/构建启动阶段失败：

```
# 平台事实探针（新 zsh 登录 shell 可复跑）：
$ command -v mvn || echo NO_MAVEN
NO_MAVEN
$ command -v java || echo NO_JAVA
NO_JAVA

# 权威 CI 失败→钉源自供给→校验成功的完整链条（同一次 run 的 ci-run1.log，grep -n 实测锚点）：
$ grep -n "No usable Maven" logs/ci-run1.log
194:jheaps/0.14: No usable Maven 3.8+ was found; downloading the pinned Apache Maven 3.8.6 binary distribution
$ grep -n "Using verified Apache Maven" logs/ci-run1.log
197:jheaps/0.14: Using verified Apache Maven 3.8.6 home /storage/.../build-release/apache-maven-3.8.6
```

既有的失败面签名是 `mvn.*command not found`（E184），但 E184 的方案止步于
`rec_approach=manual-install-ant, rec_impl=manual, rec_auto_fix=false`——把工具供给留在人工
步骤，每台 worker、每轮环境都要重复人工动作，CI 可复现性差。

## 根因（含环境作用域机理澄清）

1. **工具缺失面**：E184 已收录——鸿蒙平台未预装 Java 构建工具，cmd-pkgs 无预编译包，且无
   apt/yum/brew 可用。
2. **wrapper 缺失面**：部分上游（如本 run 的纯 Java/Maven 库）tarball 不含
   `mvnw`/`.mvn/wrapper`，jline3 的"上游自带 wrapper 直接起构建"路线不可照搬。
3. **环境作用域机理澄清（重要，勿写成"设备无 curl"）**：权威 CI 执行环境**PATH 不解析
   curl** 且其 **python3 无 CA bundle**——`/usr/bin/curl` 本体在设备上存在且可执行
   （8.8.0-DEV, aarch64-linux-ohos）。实证：本 run 权威 CI 预下载段对三类钉源产物（源码、
   BiSheng JDK、Maven）全部报 `FileNotFoundError: 'curl'`（ci-run1.log L85-116，grep -n
   命中 15 处），随后由 conan 内部下载器接管完成全部下载。结论：**任何"配方外先手工下载
   好"或"shell 单通道下载"都依赖执行环境 PATH/CA 状态，不可依赖**；conan 内部下载器
   与这两项环境状态无关，这正是声明式钉源方案的机理优势。

## 修复：conandata `build_tools.*` 声明式钉源自供给（四段式）

### ① conandata.yml 声明式钉源（url+filename+sha256+version 四元组）

```yaml
build_tools:
  bisheng_jdk:
    url: "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/bishengjdk-17.0.13-ohos-aarch64.tar.gz"
    filename: "bishengjdk-17.0.13-ohos-aarch64.tar.gz"
    sha256: "ce074909ff5c13e7e7675eb243ee15424f0343610312c526552a1a08d199e28f"
    version: "17.0.13"
  maven:
    url: "https://repo1.maven.org/maven2/org/apache/maven/apache-maven/3.8.6/apache-maven-3.8.6-bin.tar.gz"
    filename: "apache-maven-3.8.6-bin.tar.gz"
    sha256: "c7047a48deb626abf26f71ab3643d296db9b1e67f1faa7d988637deac876b5a9"
    version: "3.8.6"
```

钉源值须交叉验证：下载后同时核对发布方公布的多种摘要（例：Maven 3.8.6 的 sha1 对
repo1 发布 `.sha1`、sha512 对 archive.apache.org 官方 `.sha512`，位级一致后才写入）。

### ② 配方内先探测复用（环境变量 → 常见安装位 → PATH，逐候选实测）

```python
def _find_maven_home(self, java_home):
    candidates = []
    for variable in ("MAVEN_HOME", "M2_HOME"):
        configured = os.environ.get(variable, "")
        if configured:
            candidates.append(configured)
    mvn_on_path = shutil.which("mvn")
    if mvn_on_path:
        candidates.append(os.path.dirname(os.path.dirname(os.path.realpath(mvn_on_path))))
    # …逐候选 _validate_maven_home（mvn -v 实测解析版本），拒绝品进 rejected 清单
```

预置命中免下载、缓存友好；`mvn -v` 在候选 JDK 的 JAVA_HOME 环境下实测执行，版本
不符（如 <3.8）即拒绝并累计 rejected 清单——失败信息携带全量清单，诊断一步到位。

### ③ 全部缺失时用 conan 内部下载器按钉源下载

```python
tool = self.conan_data["build_tools"]["maven"]
installed = os.path.join(self.build_folder, "apache-maven-{}".format(tool["version"]))
get(self, url=tool["url"], filename=tool["filename"], sha256=tool["sha256"],
    destination=installed, strip_root=True, keep_permissions=True)
```

`get()` 走 conan 内部下载器：不依赖执行环境 PATH（curl 缺失无关）、不依赖 python3 用户
侧 CA 配置（conan 自带证书链）、sha256 钉校验兜底完整性。

### ④ 下载后版本实测校验，失败报错携带 rejected 全量清单

下载不等于可用：对下载产物再跑一次 `mvn -v` 实测（同②的校验函数），不符即
`raise ConanException("Pinned Apache Maven {} could not be used: … Rejected preinstalled
candidates: …")`——把"哪个候选因为什么被拒、钉源产物为什么不能用"一次讲清。

## 模式在库实例（L2 证据，≥3 门槛远超）

`grep -rl "build_tools:" archives --include=conandata.yml` = 恰 **9 处**：

| 配方 | 钉源工具 |
|---|---|
| archives/j/jline3/3.3.1 | bisheng_jdk |
| archives/j/jackson-jr/2.14.0 | bisheng_jdk |
| archives/j/jheaps/0.14 | bisheng_jdk + maven（双工具） |
| archives/s/servlet-api/4.0.1 | bisheng_jdk |
| archives/v/vecmath/1.5.2 | bisheng_jdk |
| archives/q/qtxdg/3.12.0 | lxqt_build_tools（同模式异键名） |
| archives/s/skia/2.88.9 | gn |
| archives/r/radlib/2.12.0 | automake（多镜像） |
| archives/l/libcamera/0.7.2 | ply |

横跨 ≥5 类工具、Java 与 C/C++ 双域——证明是仓级通用模式而非 Java 专属。消费侧同构：
jline3 与 jheaps 的 conanfile.py 均以 `self.conan_data["build_tools"][…]` 消费。

## verification_cmd（自包含，任何新 shell 可复跑）

```bash
# 平台事实探针（不依赖任何 run 日志）：
command -v mvn || echo NO_MAVEN; command -v java || echo NO_JAVA

# 权威实证（指向任一新 run 的日志即可，勿独占本 run 路径）：
grep -n "No usable Maven" <任一新run>/logs/ci-run1.log          # 失败信号→钉源下载触发
grep -n "Using verified Apache Maven" <同run>/logs/ci-run1.log  # 下载后版本实测校验成功

# 模式实例与在库计数：
sed -n '/^build_tools:/,/^[a-z_]*:/p' <repo>/archives/j/jline3/3.3.1/conandata.yml
grep -rl "build_tools:" <repo>/archives --include=conandata.yml | wc -l   # 实测 9
```

## 回退方案

1. **预置 tarball 供探测命中**：把工具 tarball 预置到 `~/` 等探测位，让②的探测链命中
   （免下载；注意权威 CI 八门禁重跑会清环境，不可作唯一依赖）。
2. **人工手动安装**（E184 既有退路，`rec_impl=manual`）。
3. **官方预构建 jar**（E184 `fallback_approach`）：无源码构建诉求时直接消费官方二进制。

## 禁止策略

| 禁止 | 原因 | 后果 |
|---|---|---|
| 配方内 shell 单通道外部下载（裸 `self.run("curl …")`/`wget`） | 依赖执行环境 PATH/CA 状态：权威 CI 执行环境 PATH 不解析 curl（本 run L85-116 实证）+ python3 无 CA bundle；DRAFT-12609 forbid_1 同源，本条为其声明式上位替代 | `FileNotFoundError: 'curl'` 或 `CERTIFICATE_VERIFY_FAILED`，下载阶段失败且随 worker 漂移 |
| 提交镜像 URL 进 conandata（gh-proxy/ghfast 等） | 违反官方 URL 纪律（R39）；镜像加速是 CI 侧 mirror-fallback 的运行时职责 | R39 门禁拦截 / 上游身份漂移 |
| 无校验和裸下载（`get()` 缺 sha256） | sha256 钉校验是钉源自供给的完整性前提 | 损坏/被篡改工具进入构建，失败形态不可诊断 |

## 查重与差异化（证据段，声明检索口径）

- **检索口径**：`grep -rliE "build_tools"`（**大小写不敏感**，`-l` 文件级），范围
  knowledge/graph/ 与 knowledge/drafts/，2026-10-14 于 feat/jheaps-0.14 worktree 实测。
  小写敏感 grep 会漏报下述部分命中，故统一用大小写不敏感口径。
- **graph 命中（1 文件，无关）**：E476.kv——匹配行为 verification_cmd 中 cmake 选项
  `-DFOONATHAN_MEMORY_BUILD_TOOLS=ON`。
- **drafts 命中（8 文件，全部无关）**：DRAFT-darts-0.32-hmdfs-getcwd-tmpdir-pwd-fallback.md
  （`HMBS_BUILD_TOOLS` 计数器）、DRAFT-expat-2.8.4-cmake-getrandom-default-auto-6371.kv
  （`EXPAT_BUILD_TOOLS` cmake 选项）、DRAFT-inspircd-4.7.0-timeout-env-shell-test-command.md
  （`BUILD_TOOLS` 通用行提及）、DRAFT-libncursesw-6.6-build-path-archiver.kv 与 .md
  （`OHOS_BUILD_TOOLS=8/8` 预检计数器）、DRAFT-minia-3.2.6-preset-system-name-false-cross.md
  （`HDF5_BUILD_TOOLS` cmake 选项）、DRAFT-uhttpmock-0.11.0-meson-supply-native-rewrite-
  dual-includedirs.md（`HMBS_BUILD_TOOLS` 计数器）、E546-draft-B37A.kv（evidence 字段函数名
  `_stage_glib_build_tools`）。全部为同名子串的 cmake 选项/预检计数器/函数名。
- **结论**：conandata `build_tools.*` 声明式钉源自供给模式在 graph+drafts 零覆盖。
- **与 E184 的差异化**：E184 是本失败面的既有签名与人工退路（manual-install、
  rec_auto_fix=false）；本条把同一失败面升级为配方内声明式自动自供给——范式升级而非重复，
  fallback 链显式衔接 E184 人工路线。
- **与 DRAFT-12609 的差异化**：该条是**命令式坑修复**（rec_command 为 curl 失败→python3
  urllib 免证书回退的双通道命令串，外加 sh mvn 绕 shebang、asciidoctor.skip），作用于
  "下载器怎么写"；本条是**声明式供给范式**（build_tools.* 钉源 + 探测复用 + conan 内部
  下载器 + 版本校验 + rejected 清单），作用于"工具从哪来、失败怎么诊断"。conan 内部
  下载器天然规避 DRAFT-12609 的 curl 单通道与 CA bundle 两坑（本 run L85-116 预下载全挂、
  L194-197 接管成功即实证），两条相邻、不矛盾、互为引证。

## 相邻条目第二实例注记（DRAFT-12611，不另立条目）

本 run 触发库命中的 felix maven-bundle-plugin 4.2.1 JDK 9+ ConcurrentModificationException
问题类，经查重命中既有草稿 **DRAFT-12611-jdk17-patch-build-plugin-compat**（同 trigger_tool=
mvn、同 phase=build、同 error_signature 族、同修复线、同补丁形态），jheaps 为**第二实例**：

- 修复线同为插件就地升 **5.1.9** + conandata **portability patch**（本 run 为单属性
  `maven-bundle-plugin.version 4.2.1→5.1.9`，属性式 pom 走属性升级即可——对 DRAFT-12611
  "必须在声明处改版本"结论的补强：属性管理的 pom 改属性即可）。
- 机理补齐：felix 4.2.1 内嵌 **bnd 5.2**（非 4.x），`aQute.bnd.osgi.Jar.putResource` 在
  `TreeMap.computeIfAbsent` 映射函数内自变更 map，JDK 9+ 专用实现（**JDK-8176894**）检测
  后抛 ConcurrentModificationException——修复线与官方 FELIX-6259 一致；并实测同域排除
  （compiler 3.8.1 / surefire 3.0.0-M5 / jacoco 0.8.5 在 JDK 17 下无需升级）。
- **证据出处如实标注**：第一手 CME 堆栈仅存于本 run `notes.md` 的**开发期记述**（首次上游
  构建实测命中：`TreeMap.callMappingFunctionWithCheck → Jar.putResource` 完整堆栈）；权威
  CI 日志（ci-run1.log L192）只有补丁应用记录、无 CME 堆栈——补丁先于构建生效，属"开发期
  构建观察 + 配方补丁"级证据，**非 CI 日志可查**。
- 该实例注记应随 DRAFT-12611 一并交主编 promote；本文件不改写对方草稿（写入边界=新增
  DRAFT-*，不覆盖他 run 草稿；维护者侧的并入走 B Issue 文本）。

## 本 run 已知边界（披露位置如实记录）

上游 jacoco 0.75 覆盖率门（verify 绑定）不在测试口径内的取舍，披露位置为：
配方 notes.md 两节（测试口径与门禁 + 已知非目标）与 conanfile.py `_maven_command` 内联
注释，共 3 处；test_package/MANIFEST.yml 现以 `scope_disclosures` 补一行口径声明（本次
path-update 补记）。

## 经验

- 构建工具缺失先写 conandata 钉源 + 探测复用 + conan 下载器 + 版本校验四段式，别把人工
  安装写进构建文档——预置 tarball 只是回退，不是方案。
- sha256 之外补一次"下载后版本实测"：钉源保证完整性，实测保证可用性（解压布局、脚本
  shebang、JDK 匹配都只有实测能兜住）。
- 环境类表述写"执行环境 PATH/CA 状态"，勿写"设备没有 X"——工具本体在不在和执行环境
  解析不到是两回事，混写会让后来者在真机 shell 里复现不出 CI 失败而误判知识失真。
