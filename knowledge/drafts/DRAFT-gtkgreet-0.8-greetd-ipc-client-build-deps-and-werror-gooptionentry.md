# greetd greeter 客户端的真构建依赖与 meson i18n 工具注入、werror 终止项补全

## 问题

gtkgreet 0.8 是 greetd 的 GTK 欢迎界面。它按惯例被当成「必须等 greetd 发布才能做」的包，
实际构建期与 greetd 无关。同一轮里还连着撞了两个与依赖无关的构建问题。

## 根因

三处独立机制，都能单独复现。

其一，**依赖面**。`gtkgreet/proto.c` 自己实现 greetd IPC 协议：用 json-c 编解码，
走 `AF_UNIX` socket 与 daemon 通信。源码只 include `gtk/gtk.h`、`glib/gi18n.h` 与
`json-c/*`，既不链接 greetd 提供的库也不包含它的头文件。所以构建期真依赖是
`gtk+-3.0` 与 `json-c` 两个，greetd 只是运行期配套件。

其二，**i18n 工具面**。`po/meson.build` 无条件调用 `i18n.gettext()`。meson 在
**配置阶段**就要在 PATH 上找到 `msgfmt`、`xgettext`、`msgmerge`。把 gettext 放在
`requirements()`（host context）时，Conan 的 VirtualBuildEnv 只把 host 依赖的
`bindirs` 放进 runenv，**不进 build PATH**（实测生成的 conanbuildenv 里 gettext 的
bin 目录不存在）。于是要么配置阶段失败，要么退回到构建机共享前缀里那份按 glibc
假设构建的 gettext（OHOS 上加载不了 `libintl.so.8`，po 目标直接崩）。

其三，**werror × 新 clang**。上游 `meson.build` 写死 `warning_level=2` 与
`werror=true`。clang15 的 `-Wextra` 包含 `-Wmissing-field-initializers`，
`GOptionEntry entries[]` 以 `{ NULL }` 收尾时只填了第一个字段，被判缺 `short_name`
初始化，警告被 `werror` 升级为硬错误，编译在 5/10 步停住。

## 最小解决与边界

依赖面：配方只声明 `gtk` 与 `json-c`，**不声明 greetd**；把 greetd 当运行期配套。

i18n 工具面：仍把 gettext 放在 `requirements()`（与 test_package 链接面一致），
在 `generate()` 里把它的 `bin` 目录前置进构建环境 PATH。这样 `msgfmt` 来自制品仓里
为 OHOS 构建的那份，而不是构建机共享前缀那份。

werror 面：用补丁把终止项补全为 `{ NULL, 0, 0, G_OPTION_ARG_NONE, NULL, NULL, NULL }`，
**不**用 `-Wno-missing-field-initializers` 全局压制。压制的代价是把整包该类告警一起
关掉，而终止项补全只改一处且保留上游其余告警的拦截能力。

边界：若某 greeter 真的链接 greetd 提供的库或头文件，greetd 必须进构建依赖。
若 gettext 以 `tool_requires` 引入且 remote 上有对应工具链二进制，则无需手动前置 PATH。
补丁手法只适用于以默认零值收尾的数组；上游显式列举全部字段时不存在该问题。
不要用平台宏 `__OHOS__` 包住任何一处 —— 三者都与平台无关。

## 验证

`conan install --build=never` 探针一次通过（gtk 3.24.43、json-c 0.18、gettext 0.22.5.1
全部 `Package installed`），说明依赖面无缺口。

`meson setup` 日志同时出现 `Program msgfmt found: YES`、
`Run-time dependency gtk+-3.0 found: YES 3.24.43`、`Run-time dependency json-c found: YES 0.18`；
`meson compile` 在补丁后无 missing field 报错并完成 7 个目标。

`conan create` 退出码 0，test_package 在制品上执行 `--help` 退出码 0。
`conan-verify` 四道门全过：G1 配方完整性、G0 预构建风险、G2 干净 `conan create`
（`--user=ohpcd --channel=stable`）、G3 系统同名库隔离。

## 七轴查重

对知识图谱与草稿池检索。

| 轴 | 结果 | 证据 |
| --- | --- | --- |
| exact_duplicate | 否 | `gtkgreet` 与 `greetd` 在 doc、graph、drafts 全库零命中 |
| causal_duplicate | 否 | DRAFT-5027 的报错是共享前缀 glibc 版 msgfmt 加载失败（`libintl.so.8`），本轮是 host 依赖的 bin 不进 build PATH，根因不同 |
| trigger_overlap | 弱 | DRAFT-kf-skip-po-processing-gettext-toolchain 也涉及 msgfmt，但它的解法是关掉 po 处理，本轮是换用制品仓的 msgfmt |
| solution_overlap | 弱 | DRAFT-stc-5.0 用 `-Wno-missing-field-initializers` 压警告，本轮补全终止项字段，解法方向相反 |
| combination_novelty | 是 | 依赖判定加 i18n 工具注入加 werror 终止项三者组合，且依赖面结论（greetd 不是构建依赖）此前无条目 |
| boundary_novelty | 是 | 明确区分「协议自实现」与「链接 greetd 库」两种情形，前者不进构建依赖 |
| test_migration_novelty | 否 | 上游无测试套件，未改上游测试 |

决定：写成这一对草稿。`msgfmt` 与 `-lintl` 各自在 E015、E142 等条目中有同族记录，
但签名与解法都不同，本轮不另写条目，只在 `similar_to` 里互指。

## 适用边界

适用于「以 IPC 协议自行实现 greetd 客户端」的 greetd 族 greeter 包、以及 meson 项目里
i18n 工具只在 host requires 的场合。不适用于真正链接 greetd 库的包，也不适用于
已经在 remote 上发布 gettext 工具链二进制、可直接 `tool_requires` 的场景。
