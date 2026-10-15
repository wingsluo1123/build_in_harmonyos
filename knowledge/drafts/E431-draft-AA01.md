# E431 — keycloak-config-cli 6.4.0 配置模型（无 realm 字段）

## 错误特征

`java -jar keycloak-config-cli.jar --keycloak.realm=master …` 启动即失败：

```
Binding to target [...KeycloakConfigProperties...] failed:
    Property: keycloak.realm
    Value: "master"
    Origin: "keycloak.realm" from property source "commandLineArgs"
    Reason: The elements [keycloak.realm] were left unbound.
```

## 触发条件

- keycloak-config-cli 6.x（KeycloakConfigProperties 构造器绑定，`ignoreUnknownFields=false`）
- 调用传入旧版参数 `--keycloak.realm`（6.4.0 字段集中无 realm）

## 根因分析

6.4.0 字段集：loginRealm(默认 master)/clientId(默认 admin-cli)/version(@NotNull 无默认)/
url(@NotNull)/user(默认 admin)/password/clientSecret/grantType(默认 password)/sslVerify(默认
true)/httpProxy/connectTimeout/readTimeout/availabilityCheck。realm 概念已移入每个 import
配置文件的 `"realm"` 字段。ignoreUnknownFields=false 使 unknown 属性直接失败。

## 解决方案

### 推荐方案

删除 `--keycloak.realm`；补必填 `--keycloak.version`：

```bash
java -jar keycloak-config-cli.jar \
  --keycloak.url=$URL --keycloak.version=$KC_VERSION \
  --keycloak.user=admin --keycloak.password=$PASS \
  --import.files.locations=$CFG
```

### 禁止做法

- ❌ 为消除绑定失败而给配方/脚本加 `--spring.config.activate` 之类 hack 去放宽绑定校验

## 验证

```bash
java -jar keycloak-config-cli.jar --keycloak.url=http://127.0.0.1:<封闭端口> \
  --keycloak.version=26.1.0 --keycloak.user=admin --keycloak.password=x \
  --import.files.locations=<有效文件>
# 预期：越过绑定阶段，进入 Keycloak 连接（Connection refused 签名）
```

## 关联条目

- 相关: E432（import.files.locations 的 glob/隐藏目录解析）

## 来源

- 草稿: E431-draft-AA01
- 事件: keycloak-config-cli 6.4.0 test_package A10 首版绑定失败
