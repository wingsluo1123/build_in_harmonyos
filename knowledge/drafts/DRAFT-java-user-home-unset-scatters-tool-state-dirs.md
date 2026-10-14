# 构建子进程 user.home 回退 '?' 时本地状态目录散射进构建目录：显式 HOME + 工具原生仓库旗标钉绝对路径（Maven .m2，zt-exec 1.12 案例）

> 草稿（DRAFT）— 与 `.kv` 同 stem 配对，字段对齐 `knowledge/graph/_template.kv`。
> 修订自 DRAFT-14402-bishengjdk-user-home-qmark-maven-repo：按 Curator 审计去
> 库名-版本化命名、补 affected_scope/fallback_*/forbid_* 全字段、verification
> 改自包含探针、principles 挂钩、related 改挂实存图谱条目。

## 问题（规则陈述）

构建子进程取不到 `HOME` 且设备 uid 无 passwd 条目时，OpenJDK 系 JVM 的
`user.home` 回退为**字面字符串 `?`**；一切按 `${user.home}`/`~` 推导状态目录
的工具（Maven 的 `~/.m2/repository`、Gradle 的 `~/.gradle`）会把整个仓库建进
`<cwd>/?/` 下——随构建目录生灭、路径不可预测。外层编排进程（conan 等）的
`HOME` 通常正常，两侧认知不一致 → "构建全绿但产物回收报 not found"。

## 案例事实（zt-exec 1.12，run4）

- 症状：`package()` 报 `slf4j-api jar not found in local Maven repo:
  /storage/Users/currentUser/.m2/repository/...`，jar 实际落在
  `.conan2/p/b/<pkg>/b/?/.m2/repository/org/slf4j/slf4j-api/1.7.2/`。
- `mvn -B clean package` 全绿（96 上游测试 + BUILD SUCCESS），失败只在回收侧。

## 自包含验证探针（离开 run 可复现）

```sh
env -u HOME ~/bishengjdk17/bin/java -XshowSettings:properties -version 2>&1 | grep user.home
# 期望: user.home = ?
```

## 可复用修复范式

```python
home = os.path.expanduser("~")          # conan 进程侧真实 HOME
os.environ["HOME"] = home               # 子进程显式继承
maven_repo = os.path.join(home, ".m2", "repository")
self.run('bash -c "cd {src} && sh {maven}/bin/mvn -B clean package '
         '-Dmaven.repo.local={maven_repo}"', env="conanbuild")
```

要点：
1. `-Dmaven.repo.local` 绝对路径是关键——即使 `user.home` 仍解析成 `?`，仓库
   位置也被钉死；Gradle 同理用 `--gradle-user-home`/`GRADLE_USER_HOME`。
2. 产物收集用同一 Python/脚本常量路径，**不依赖 `~` 在子进程环境成立**。
3. 次选（救急）：构建后从 `<build_dir>` 扫描 `*/?/.m2/repository` 整体拷回——
   路径含字面 `?` 且随构建目录生灭，不可靠。

## 禁止

- 真机/净化 CI 上运行不带 `-Dmaven.repo.local` 的 `mvn -B ...`（属未定义行为）。

## principles

- **P-ENV-001（principles.kv id P014）**：环境变量与构建系统语义冲突——优先
  工具原生机制（`-Dmaven.repo.local`）钉路径，不赌环境变量在子进程可见。

## 关系

- 同族：**E184**（Java 构建工具链缺失与自举：ant/maven/gradle command not found）。
- similar_to：**E083**（BiSheng JDK 厂商特有行为）、**E084**（Java 无
  ant/maven 手工构建）。
- 姊妹稿：`DRAFT-jdk-vendor-version-string-breaks-upstream-test-assertions`
  （同 run 另一独立 FAIL→PASS 面）。
- 原稿：DRAFT-14402-bishengjdk-user-home-qmark-maven-repo（本稿去版本化修订版）。

## 适用面与反例

- 适用：所有 OHOS 真机/净化 CI 构建子进程内按 `${user.home}` 落状态的 JVM
  生态工具；不限库与语言。
- 反例：宿主 Linux CI（有 passwd 条目、HOME 恒正常）不会命中——探针输出
  `user.home = /home/xxx` 即不适用。

## 证据（run 内）

- run4 FAIL：`runs/zt-exec-1.12/logs/ci-run4.log`（package() Invalid
  configuration: slf4j-api jar not found；`find` 实证 `?/.m2` 散射路径）。
- run5 PASS：`runs/zt-exec-1.12/logs/ci-run5.log`（-Dmaven.repo.local 钉死后
  slf4j-api-1.7.2.jar 成功收集进 libexec 并被 test_package 加载）。
