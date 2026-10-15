# E432 — import.files.locations 隐藏目录排除（Spring glob 解析）

## 错误特征

`java -jar keycloak-config-cli.jar --import.files.locations=<存在的文件>` 报：

```
de.adorsys.keycloak.config.exceptions.InvalidImportException: No files matching '<path>'!
```

文件实际存在、路径正确——只因路径链中某层是 dot 目录（如 `/…/.atomcode/skills/…`）。

## 触发条件

- keycloak-config-cli 默认 `import.files.include-hidden-files=false`
- location 路径的任一祖先目录名以 `.` 开头（CI 工作区在隐藏目录下、skill 归档目录等）

## 根因分析

`KeycloakImportProvider.readFromLocations` 用 Spring `PathMatchingResourcePatternResolver`
解析 location（支持 glob），随后 `filterExcludedResources` 过滤：`isIncludeHiddenFiles()==false`
（默认）时，`file.isHidden()` 或 `FileUtils.hasHiddenAncestorDirectory(file)` 为真的资源被
整体排除 → 过滤后 0 资源 → 抛 InvalidImportException。注意区分另一分支：路径完全不存在时
是 UrlResource 直读 → FileNotFoundException（签名不同）。

## 解决方案

### 推荐方案

调用追加 `--import.files.include-hidden-files=true`（Spring relaxed binding）。

### 禁止做法

- ❌ 误判为"文件丢失"而重新复制/重建配置（文件一直在，只是被过滤）

## 验证

```bash
# 同一文件对比两次运行
java -jar app.jar … --import.files.locations=$CFG                    # → No files matching
java -jar app.jar … --import.files.include-hidden-files=true \
     --import.files.locations=$CFG                                   # → 进入连接阶段
```

## 关联条目

- 相关: E431（6.4.0 配置模型）

## 来源

- 草稿: E432-draft-FBA0
- 事件: keycloak-config-cli 6.4.0 test_package A10 迭代（fixture 在 .atomcode 下）
