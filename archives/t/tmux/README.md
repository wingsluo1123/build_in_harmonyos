# tmux

**Terminal Multiplexer**

tmux is a terminal multiplexer: it enables a number of terminals to be created, accessed, and controlled from a single screen. tmux may be detached from a screen and continue running in the background, then later reattached.

## 版本列表

| 版本 | 状态 | 编译日期 | 补丁数 | 预编译包 |
|------|------|---------|--------|---------|
| 3.4 | published | 2026-05-27 | 4 | ✅ tmux-3.4-ohos-aarch64.tar.gz |

## 编译特性

- **静态链接**：无动态库依赖，解决 HarmonyOS 动态库加载限制
- **依赖**：ncurses 6.4, libevent 2.1.12

## HarmonyOS 平台适配

### 已解决的问题

1. **HMDFS 临时文件限制**：configure/config.status 无法在当前目录创建临时目录，修改为使用绝对路径 `/storage/Users/currentUser/tmp/confXXXXXX`
2. **系统识别**：config.guess 不识别 HarmonyOS，添加 `*:HarmonyOS:*:*` 分支
3. **三元组支持**：config.sub 不接受 `linux-ohos` 组合，添加 `linux-ohos*` 支持
4. **静态链接**：强制静态链接 libevent 和 ncurses，避免动态库加载问题

### 补丁文件

- `0001-cmd-parse.c.patch` - Bison 3.8.2 生成的解析器（替换 cmd-parse.c）
- `0002-compat.h.patch` - 添加 `__OHOS__` 守卫，使用系统 forkpty
- `0003-compat-forkpty-linux.c.patch` - 空实现（OHOS 系统提供 forkpty）
- `0004-configure.patch` - 修改临时目录路径为 $TMPDIR（解决 HMDFS 权限问题）
- `0005-etc-config.guess.patch` - HarmonyOS 系统识别
- `0006-etc-config.sub.patch` - linux-ohos 三元组支持

## 功能验证

```bash
$ tmux -V
tmux 3.4
```

## 相关链接

- 官方网站：https://tmux.github.io/
- 源码仓库：https://github.com/tmux/tmux