# keycloak-config-cli

Keycloak Configuration CLI — 读取 JSON/YAML 格式的 realm 配置文件，
通过 Keycloak 管理 REST API 导入/更新 realm（用户、角色、客户端、认证流等）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 6.4.0 | built | 源码编译（Maven），GitHub 下载 |

## 概述

keycloak-config-cli 是 adorsys 出品的 Keycloak 配置导入工具：
- 将 realm 配置（users/roles/clients/authentication flows 等）以 JSON/YAML 文件管理
- 通过 Keycloak Admin REST API 增量导入/更新
- Spring Boot 3.2.9 应用，fat jar 分发（layout=ZIP），运行时自包含零外部依赖

## 构建方式

- **类型**: 源码编译（Maven 3.9.6，上游自带 ./mvnw wrapper）
- **来源**: GitHub (adorsys/keycloak-config-cli tag v6.4.0，带 v 前缀)
- **Java 运行时**: bishengjdk 17.0.13（`-Djava.version=17`，上游 CI 矩阵支持的构建参数）
- **许可证**: Apache-2.0

## 使用

```shell
java -jar libexec/keycloak-config-cli.jar \
    --keycloak.url=http://<keycloak-host>:8080 \
    --keycloak.ssl-verify=true \
    --keycloak.user=admin \
    --keycloak.password=<admin-password> \
    --import.files.locations=./realm-config.json
```

注意（6.4.0 配置模型）：`KeycloakConfigProperties` 无 `realm` 字段
（旧版 `--keycloak.realm` 会触发绑定失败）；必填属性为 `keycloak.url` 与
`keycloak.version`（loginRealm 默认 master，clientId 默认 admin-cli）。

## 测试

- 上游 surefire 单测：90/90 PASS（build() 内运行，41 个 IT 因平台无 Docker 跳过，
  详见 6.4.0/reports/test-report.md）
- test_package 真机消费者验证：10 项断言（fat jar 结构 A1-A8 +
  真实执行 A9/A10 至 Keycloak 连接阶段）
