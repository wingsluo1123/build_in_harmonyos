# tmux 3.4 适配笔记

## 构建方式

- 构建系统：Autotools
- 编译器与目标参数：由 Conan profile 和 `AutotoolsToolchain` 注入
- 依赖：Conan `libevent/2.1.12`、Worker 系统静态 ncurses
- 链接方式：tmux `--enable-static`，链接阶段使用 `-static`

标准构建入口：

```bash
conan create archives/t/tmux/3.4 -pr:h=<ohos-profile> -pr:b=default
```

## HarmonyOS 适配

| 问题 | 根因 | 处理方式 |
|---|---|---|
| configure 无法在当前目录创建临时目录 | HMDFS 对临时目录创建有限制 | 使用 `${TMPDIR:-/tmp}`，不写入用户专属绝对路径 |
| config.guess 无法识别 HarmonyOS | 上游脚本缺少 HarmonyOS 分支 | 返回对应架构的 `*-unknown-linux-ohos` 三元组 |
| config.sub 拒绝 linux-ohos | 上游校验列表缺少该组合 | 增加 `linux-ohos*` 校验分支 |
| 依赖路径不可复现 | ncurses 不在 Conan 制品仓，libevent 在制品仓 | libevent 由 Conan 注入；ncurses 默认从当前 Worker 用户的 `usr/local` 系统前缀发现，可用 Conan conf `user.tmux:system_prefix` 覆盖，缺少 `include`/`lib` 时明确终止 |

## 测试说明

tmux 3.4 提供 `make check` 目标，但默认配置下没有断言式上游测试程序；
`fuzz/input-fuzzer` 仅在显式启用 fuzzing 时构建。配方仍执行 `make check`，
并由 `test_package/test.sh` 运行打包后的 `tmux -V`，精确核对输出为 `tmux 3.4`。

源码包 SHA-256 已按下载字节核对为：

```text
551ab8dea0bf505c0ad6b7bb35ef567cdde0ccb84357df142c254f35a23e19aa
```

## 交付范围

PR 只提交 Conan 配方、元数据、测试和三个可复现补丁，不提交预编译二进制。
