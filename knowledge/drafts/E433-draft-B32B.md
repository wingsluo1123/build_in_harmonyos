# E433 — OHOS 无 Docker：failsafe IT 跳过 + Mockito 5 需 -javaagent

## 错误特征

两种（常在同一构建叠加出现）：

```
# (1) failsafe IT（testcontainers）
Could not find a valid Docker environment.
… /var/run/docker.sock: no such file …

# (2) surefire 单测（Mockito 5 inline）
… ByteBuddyAgent … attach … failed …
```

## 触发条件

- (1) 构建含基于 Testcontainers 的 `*IT` 集成测试，且 OHOS 真机未安装 Docker（`which docker` rc=1）
- (2) 依赖 Mockito 5+（默认 inline mock maker，经 JVM Attach API 动态挂载 byte-buddy-agent），OHOS attach 机制不可用

## 根因分析

(1) testcontainers 经 Docker Engine API 拉起容器，平台无 Docker daemon 时必然失败——平台差异，
用上游支持的 `-DskipITs` 跳过（上游 CI 有 Docker，IT 仍可运行，需在 notes/R51 申报）。
(2) Mockito 5 inline 的 `ByteBuddyAgent.install()` 动态 attach 在 OHOS 失败——在 surefire
argLine 显式 `-javaagent:<byte-buddy-agent.jar>` 预装载即解决（keycloak-metrics 7.0.0 同源验证）。

## 解决方案

### 推荐方案

```bash
./mvnw -B -ntp clean verify -Djava.version=17 -DskipITs \
  -DargLine="-javaagent:$HOME/.m2/repository/net/bytebuddy/byte-buddy-agent/<ver>/byte-buddy-agent-<ver>.jar"
```

（byte-buddy-agent 版本从 `mvn dependency:tree` 的 mockito 依赖解析；配方内用 glob 定位。）

### 禁止做法

- ❌ 删除/注释 IT 测试类来"修复"（必须用 -DskipITs 保留上游测试集完整性并在 R51 申报）

## 验证

```bash
which docker                    # rc=1 即平台无 Docker
grep "Tests run:" target/surefire-reports/*.txt   # 单测全绿
ls target/failsafe-reports 2>/dev/null | wc -l    # 0（IT 已跳过）
```

## 关联条目

- 相关: keycloak-metrics 7.0.0 适配记录（Mockito 5 -javaagent 同源根因）

## 来源

- 草稿: E433-draft-B32B
- 事件: keycloak-config-cli 6.4.0 Run A（90 单测全绿 + 41 IT 申报）
