# pmacct 1.7.8

pmacct 是一套被动的网络监控工具集：从链路层抓包（或接收 NetFlow/sFlow/IPFIX/BGP/BMP/
流式遥测）出发，做流量统计、BGP/BMP 路由监控与 RPKI 校验，并通过内置插件把结果落库
（MySQL/PostgreSQL/SQLite3）、导出（Kafka/AMQP/Avro）或打包转发（tee/nfprobe）。

- Homepage: http://www.pmacct.net/
- 依赖: `libpcap/1.10.6`（制品仓静态包）
- 随包 vendored: `libcdada 0.4.0`（上游 git submodule，制品仓未发布）
- 安装命令（全部落在 `bin/`）:
  `pmacct`、`pmacctd`、`nfacctd`、`sfacctd`、`pmtelemetryd`、`pmbgpd`、`pmbmpd`
- 文档与示例: `share/pmacct/`

> 上游第 8 个守护进程 `uacctd` 依赖 `libnetfilter_log`（制品仓未发布），本版本不构建。

## OHOS 适配要点

- 上游 tag 归档不含 `configure`（git 树快照），`build()` 内 `autoreconf -f -i -I m4` 自举。
- conan 同 profile 下不是 cross build，AutotoolsToolchain 不会自动补三元组；设备
  `uname -s = HarmonyOS` 而 config.guess（2024-07-27）不识别 ⇒ 必须显式传
  `--build` / `--host`，否则 configure 直接失败。
- conanbuild 环境的 conan perl 5.42.2 与 hnp perl 5.42.0 的 XS 模块 ABI 不兼容，
  automake/1.18 的 `.aclocal-real`/`.automake-real` shebang 写死 hnp perl ⇒
  需要 perl shim 把 aclocal/automake 显式指到 conan perl，否则 `Perl_my_cxt_init`
  符号缺失。
- `libcdada` 作为 git submodule 未发布，随包 vendored 后交给 pmacct 自带的
  submodule 构建系统（`--with-external-deps=yes`）就地编译为静态库。
- OHOS clang 会把 `-lstdc++` 归一化为 `-lc++`，故上游硬编码的 `LIBS=-lstdc++` 无需补丁。
- 唯一源码补丁：`mallopt(M_CHECK_ACTION)` 的宏守卫（OHOS/musl 有 `mallopt()` 但没有
  `M_CHECK_ACTION`）。
