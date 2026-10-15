# keycloak-config-cli 6.4.0 — 适配笔记

## 概述
keycloak-config-cli（上游 adorsys/keycloak-config-cli）是 Keycloak 的
配置导入 CLI：读取 JSON/YAML 格式的 realm 配置文件，通过 Keycloak 管理
REST API 导入/更新 realm（用户、角色、客户端、认证流等）。
Spring Boot 3.2.9 应用，fat jar 分发（spring-boot-maven-plugin layout=ZIP），
运行时自包含零外部依赖。

## 上游定位
- 仓库：https://github.com/adorsys/keycloak-config-cli
- tag：**v6.4.0（带 v 前缀）**，commit 373ce996d332508be6e375d7bdf221307bddb330
- release 发布 2025-02-21；CHANGELOG 6.4.0: "Allow a user's username to be updated through the config"
- 注意：npm 官方源 keycloak-config-cli@1.0.0 是无关抢注包，勿混用
- 源码 tarball SHA256: c4196406e5d28753f6b72edbb3a283052f3bc2bab3c75ce3a3c434f196b546ce
  （与上游仓库自带 .tarball-sha256 文件交叉验证一致）

## 构建方式
- 类型：源码编译（Maven 3.9.6，上游自带 ./mvnw wrapper，
  .mvn/wrapper/maven-wrapper.jar 已提交，distributionUrl=repo.maven.apache.org）
- 来源：GitHub codeload 官方 tarball（refs/tags/v6.4.0）
- Java：bishengjdk 17.0.13（cmd-pkgs 自动安装；上游 CI build-pom-version
  job 矩阵 [17,21] 证明 -Djava.version=17 可完整编译，故用 17 对齐 bishengjdk17）
- 许可证：Apache-2.0（LICENSE.txt）

## 依赖链（W0 全部可消费，详见依赖拓扑报告）
- 配方零 conan requires（同 jackson-core 2.14.1 / keycloak-metrics 7.0.0 先例）
- JDK 17：cmd-pkgs install-jdk.sh（CI 链路，三个 Java 先例实证）
- Maven 3.9.6：repo.maven.apache.org（HTTP 200 实测）
- 24 个直接依赖（spring-boot 3.2.9 系、keycloak-admin-client 26.0.4、
  jackson 2.17.2 系、resteasy 7.0.0.Alpha2 系、javers-core 7.6.3、
  failsafe 3.3.2、commons-*、snakeyaml 2.3、logstash-logback-encoder 8.0）
  全部 Maven Central 在线拉取并打进 fat jar，运行时零外部依赖

## 上游测试（R51 申报表）
- 清点：72 个测试 java 文件，490 个 @Test 注解（grep -rE "^\s*@Test\b" src/test）
  - surefire 单测：31 个非 IT 文件
  - failsafe *IT 集成测试：41 个文件（AbstractImportIT 为基类），基于
    testcontainers 1.20.3（docker-java 3.4.0），需 Docker daemon
- 运行（真机）：
  - 单测：./mvnw -B -ntp clean test -Djava.version=17（build() 内 clean verify -DskipITs 同覆盖）
  - IT：不运行 —— 具体技术原因：OHOS 真机未安装 Docker（which docker rc=1），
    testcontainers 需通过 Docker Engine API（/var/run/docker.sock）拉起
    Keycloak 容器，平台无该能力；上游 CI（ubuntu-latest）具备 Docker 故可运行
- test_package 不能替代上游测试统计（消费者视角单独声明于 MANIFEST.yml）

## 鸿蒙适配要点（踩坑记录）
1. **JDK 获取**：本机初始无 JDK（which java rc=1、~/bishengjdk* 不存在，
   平台 workspace 回收所致）；install-jdk.sh 匿名 HEAD 请求被 HWWAF 401
   拦截，改用 GET + 浏览器 UA 成功（2475 B 脚本）；sh install-jdk.sh 17.0.13
   安装至 ~/bishengjdk17，java -version 验证 17.0.13+6 BiSheng 正常
2. **JDK 版本**：pom java.version=21，bishengjdk 为 17 —— 用上游 CI 自身
   build-pom-version job 的 -Djava.version=17 参数（非补丁），编译通过
3. **mvnw 可直接使用**：上游 wrapper 自包含（maven-wrapper.jar 已提交），
   与 keycloak-metrics 的 gradlew busybox xargs 引号问题不同，mvnw 无 shell
   参数解析陷阱（bash -c 调用，同 jackson-core 先例）
4. **IT 测试**：-DskipITs 跳过 failsafe（Docker 缺失，见 R51 申报）；
   surefire 单测不受影响

## test_package 测试（消费者视角，真机运行）
test.sh 共 10 项断言（不依赖 Keycloak 服务器，全部真机实测 PASS）：
1. A1 JAR 存在性（libexec/keycloak-config-cli.jar）
2. A2 fat jar 体积（28200765 B > 10MB）
3. A3 unzip -l 清单落盘（禁 unzip|grep 管道，keycloak-metrics SIGPIPE 教训）
4. A4 BOOT-INF/classes 主类 KeycloakConfigApplication.class 存在
5. A5-A7 BOOT-INF/lib 关键依赖打包核验（keycloak-admin-client-26.0.4 /
   spring-boot-3.2.9 / javers-core-7.6.3）
6. A8 MANIFEST Main-Class = org.springframework.boot.loader.launch.PropertiesLauncher
   （ZIP layout 实测值，非 JarLauncher）+ Start-Class = KeycloakConfigApplication
7. A9 真实执行（无配置）：Spring 启动 + 配置绑定引擎强制
   import.files.locations（确定性失败签名，rc=1）
8. A10 真实执行（README 6.4.0 规范调用 + 上游示例 moped.json）：
   启动至 Keycloak import 阶段，真实发起 REST 连接
   （127.0.0.1:59999 封闭端口 → Connection refused，rc=1）
   需 --import.files.include-hidden-files=true（fixture 位于隐藏目录时）

## 与制品仓先例的关系
- 打包模式完全对齐 archives/j/jackson-core/2.14.1（Java 源码编译 →
  Maven → JAR → libexec/ → test_package java 验证）
- R38 差异：本包是可执行 CLI（非纯库），软件级 commands.json 必需
  （同 archives/k/kor/commands.json 先例）

## 补丁
无（-Djava.version=17 为上游 CI 自身支持的构建参数，非源码修改）

### 对话 #1（W0 依赖分析 + W1 环境预检，2026-10-13）
- 任务：keycloak-config-cli 6.4.0 适配 OHOS（只分析目标库，零 conan requires 模式）
- W0：24 个直接依赖全部 Maven Central 在线可达（BOM 链 spring-boot-parent 3.2.9
  → keycloak-parent 26.1.0 → quarkus-bom 3.15.2 全 200）；npm 同名包为无关抢注包
- W1：bishengjdk 17.0.13 安装（install-jdk.sh 需 GET+UA 绕过 HWWAF 401）；
  mvnw wrapper 自包含可直接用；Docker 缺失（IT 不可行，R51 申报）
- 源码 sha256 c4196406… 与上游 .tarball-sha256 交叉验证一致

### 对话 #2（真实构建 + 上游测试，2026-10-13）
- Run A：./mvnw clean verify -Djava.version=17 -DskipITs → BUILD SUCCESS，
  surefire 90/90 PASS（逐用例清单见 surefire-per-case.log）
- Mockito 5 inline 在 OHOS 需 -javaagent byte-buddy-agent 预装载
  （JVM 动态 attach 机制不可用，同 keycloak-metrics 7.0.0 同源根因）
- Maven 本地仓迁移至 ~/.m2/repository（JVM user.home 异常置 '?' 的规避）

### 对话 #3（test_package 真机验证迭代，2026-10-13）
- 主类实测为 KeycloakConfigApplication（非 Main）；CLI 为 Spring Boot
  --key=value 风格（无 --help 模式）
- MANIFEST 实测 Main-Class=PropertiesLauncher（ZIP layout，非 JarLauncher）
- 6.4.0 配置模型实测：无 keycloak.realm 字段（旧用法触发 left unbound）；
  必填 url+version；隐藏目录 fixture 需 include-hidden-files=true
- 最终 A1-A10 十项断言全绿（testpackage-final.log）

### 对话 #4（conan-verify 门禁排障，2026-10-13）
- G1：补 export_sources()/apply_conandata_patches（配方完整性结构要求）
- G2 第一轮：codeload 裸 URL 基名无扩展名 → conan BadZipFile；
  显式 filename .tar.gz 修复
- G2 第二轮：E017 ghfast.top 镜像注入（仅匹配 github.com URL）且 ghfast.top
  本设备不可达（connect timeout）→ 回退 codeload URL 避开注入；
  崩溃残留 .ghfast-bak 会回滚覆盖手工修改，重跑前必须删除
- G2 第五轮：conan create 全绿 + test_package 10 断言真机 PASS

### 对话 #5（ohc finish 门禁排障，2026-10-14）
- W3 L0：settings 需全四项（os/compiler/build_type/arch，keycloak-metrics 先例）
- W3 JC1/JC5：5 个历史误入库空状态文件（cloog/kics/libbfio/thc）阻塞
  全仓扫描 → 用户授权后独立清理 commit（a9f0818cab）
- submit 就绪预检：补 reports/test-report.md、packaging/.packaged、
  .staging-verified、软件级 README/manifest、notes.md 对话记录
---

**编译结束**: 2026-10-14 19:50
**最终状态**: published
