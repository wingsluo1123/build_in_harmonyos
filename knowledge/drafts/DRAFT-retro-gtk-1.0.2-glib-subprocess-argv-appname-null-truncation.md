# DRAFT: 库以 g_get_application_name() 作为子进程 argv 元素 —— 未设置应用名时 argv 提前截断（retro-gtk 1.0.2 实测）

## 现象

消费者程序（只链接 libretro-gtk、纯 GLib 环境）调用 `retro_core_boot()` 后，被测库拉起的
包内 `libexec/retro-runner` 子进程直接断言失败：

```
(RetroRunner): ...: assertion failed: (argc >= 3)
Bail out!
```

被测库侧 `retro_core_boot()` 拿到子进程异常退出，`video-output` 信号一帧都不产生；
而同样的代码在 GTK/GApplication 应用里、或在上游 `g_test_init()` / `gtk_test_init()`
环境里运行**不会复现**——该隐藏前提被顺带满足。

## 根因

`retro-gtk` 的 `RetroCore` 启动 runner 时执行：

```c
g_subprocess_launcher_spawn (launcher, &err,
                             runner_path,
                             g_get_application_name(),   /* argv[1] */
                             self->filename,             /* argv[2] */
                             NULL);
```

`g_get_application_name()` 在调用方**未显式设置应用名**时返回 `NULL`；GLib 的 spawn
把 `NULL` 当作 argv 结束标记，于是子进程实际只收到 `runner_path` 一个参数，
`retro-runner` 内的 `g_assert (argc >= 3)` 立即失败（`Bail out!`）。

**上游隐藏该前提**：GTK/GApplication 初始化、`g_test_init()`、`gtk_test_init()` 都会
顺带设置应用名，因此上游自身的测试与该库的 GTK 前端永远命中不到这个空值分支；
只有纯 GLib 消费者、以及把上游 reftest 从 `gtk_test_init()` 改成 `g_test_init()` 的
headless 适配，才会把它暴露出来。

## 修复（本包采用的路径）

消费者侧在创建 `RetroCore` 之前显式初始化应用名：

```c
g_set_application_name ("my-frontend");   // 之后再做 retro_core_new / retro_core_boot
```

配方侧把该前提写入 `notes.md` 与 `test_package/MANIFEST.yml` 的"使用注意"
（`retro-runner` 以应用名作为 argv[1]、内部断言 `argc >= 3`），供后续消费者参照。

## 备选

- 在库内对 argv 元素做空值兜底（`g_get_application_name() ? g_get_application_name() : "retro-runner"`）。
  这属**上游行为变更**，需与上游协商，并须在 PR 的"上游测试/源码修改说明"里单列理由；
  本适配默认不做。

## 验证

retro-gtk 1.0.2 消费者测试：

- 不调用 `g_set_application_name()` 时：`retro-runner` 报 `assertion failed: (argc >= 3)`；
- 调用后：`retro_core_boot()` 正常返回，`video-output` 信号按帧到达（3 次 iteration
  均拿到 pixdata，逐像素契约与整帧 FNV-1a 校验和 `0x52f0e94d` 逐帧比对通过）。
