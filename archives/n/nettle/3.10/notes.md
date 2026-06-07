# nettle 3.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: failed

## 编译步骤

执行 configure 阶段的命令：
```bash
./configure --prefix=$HOME/usr/local
```

configure 阶段在生成 config.status 时失败，无法创建临时文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang/lld 缺少 libxml2.so.16 运行时依赖 | lld 动态链接了 libxml2 | 已解决：设置 LD_LIBRARY_PATH 环境变量 |
| 2 | config.status 无法创建临时文件 | HMDFS 文件系统 SELinux 权限限制 | 无法解决：平台限制，需要用户交互触发安全弹窗 |

## 源码修改

共生成 47 个补丁文件，但均未能成功应用。补丁内容包括：
- 汇编文件修改（aes-*.asm、chacha-*.asm、ghash-*.asm、sha*.asm 等）
- 配置文件更新（config.guess、config.sub、config.m4、config.make）
- 头文件调整（ecc-*.h、version.h）
- 链接脚本修改（libhogweed.map、libnettle.map）

所有补丁的分类为 `auto`，平台专用 `platform_only: true`，状态为 `pending`。

## 依赖版本

- GMP（可选依赖，用于高性能算术运算）

## 验证结果

编译失败，未能通过 configure 阶段。

```bash
configure: creating ./config.status
./config.status: line 1200: cannot create temp file for here-document: Permission denied
```

关键错误信息显示：
- config.status 脚本在执行 here-document 时无法创建临时文件
- 这是 HMDFS 文件系统的 SELinux 权限限制导致的

## 交付物

无（编译失败未产生交付物）

## 注意事项

### 平台限制说明

本次编译失败的根本原因是 HMDFS 文件系统的 SELinux 安全限制：

1. **HMDFS SELinux 限制**：在 HMDFS 挂载的文件系统上，脚本进程创建临时文件时受到 SELinux 策略限制
2. **权限弹窗机制**：当脚本尝试创建临时文件时，系统会触发安全弹窗，需要用户手动授权
3. **自动化限制**：这种用户交互式的权限授权机制导致自动化编译流程无法继续执行

### 后续建议

- 考虑将源码解压到非 HMDFS 文件系统路径（如 /tmp 或普通 ext4 分区）
- 预先配置 SELinux 策略或禁用相关安全检查
- 手动触发一次编译以获取权限授权后再尝试自动化编译

## 知识沉淀

本归档记录了 OpenHarmony 平台上 autotools 构建系统在 HMDFS 文件系统上的限制，为后续类似项目提供参考。即使编译失败，保留此归档有助于：
- 理解平台限制的影响范围
- 为后续适配提供前置知识
- 积累平台特性与编译系统的兼容性问题库