# E434 — Spring Boot fat jar MANIFEST 真实值（ZIP layout → PropertiesLauncher）

## 错误特征

test_package 结构断言写 `Main-Class: org.springframework.boot.loader.launch.JarLauncher` 时误报：

```
ERROR: MANIFEST Main-Class/Start-Class mismatch
Main-Class: org.springframework.boot.loader.launch.PropertiesLauncher
Start-Class: de.adorsys.keycloak.config.KeycloakConfigApplication
```

## 触发条件

- 配方 pom 用 spring-boot-maven-plugin `layout=ZIP`（支持 `-Dloader.path`）
- 断言凭经验写成 JarLauncher（JAR layout 的启动器）

## 根因分析

layout 决定启动器：JAR→JarLauncher，ZIP→PropertiesLauncher，WAR→WarLauncher。
Spring Boot 3.x loader 包为 `org.springframework.boot.loader.launch.*`（2.x 为
`org.springframework.boot.loader.*`）。应用主类在 `Start-Class` 头（本包为
KeycloakConfigApplication，不是直觉的 Main）。pom `<finalName>${project.artifactId}</finalName>`
使产物 jar 名不带版本号。

## 解决方案

### 推荐方案

断言以实测 MANIFEST 为准：Main-Class 断言到具体 loader 全类名 + Start-Class 断言到应用主类。

### 禁止做法

- ❌ 凭 Spring Boot 版本经验猜 loader 类名/主类名

## 验证

```bash
unzip -p libexec/<app>.jar META-INF/MANIFEST.MF | grep -E "^Main-Class:|^Start-Class:"
```

## 关联条目

- 相关: E431（真实执行断言 A9/A10 同属消费者视角验证）

## 来源

- 草稿: E434-draft-E329
- 事件: keycloak-config-cli 6.4.0 test_package A8 迭代
