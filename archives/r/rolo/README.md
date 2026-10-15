# rolo 021 - HarmonyOS 编译记录

## 概述

rolo（https://github.com/libvc/rolo）是基于 vCard 格式的终端联系人管理程序，
ncurses 全屏前端，ANSI C 编写，Autotools 构建。附带专为 rolo 编写的 vCard 解析库
libvc（独立上游 https://github.com/libvc/libvc）与 `mutt_vc_query` 查询工具。

**编译状态**: 待真机预检（首轮工作树；已知阻塞见下）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel aarch64 |
| 编译器 | clang/clang++ 15 |
| C 库 | musl libc |
| 三元组 | aarch64-unknown-linux-gnu（显式指定，config.guess 不识别 HarmonyOS） |

## 编译步骤

```bash
# v021 tag 无生成物，先 autoreconf（tool_requires automake/1.18 + libtool/2.5.4）
bash autoreconf -fi
bash configure --prefix=/ --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
make SHELL=<device-sh> -j1
make SHELL=<device-sh> -j1 check   # 上游 4 个 shunit2 用例，输出记 make_check.log 并落证
make SHELL=<device-sh> install DESTDIR=<package_folder>   # → {bin,share/man,share/doc}
```

in-source 构建：`test/run-tests` 相对自身定位 `../configure.ac`、`contacts.vcf`、
`../src/rolo`，外树构建必坏。

## 已知阻塞（R36 前置依赖）

- `libvc` 在本仓尚无配方：已改为配方内 vendoring（官方 v013 tag 源码，hash 锁定，私有 prefix 静态编译，不发布、不导出，`requires` 不再声明）。
  其余依赖（ncurses/6.6、glib/2.84.0.2、unac/1.8.0）均有配方，待真机逐个核验发布状态。

## 验证结果

待 HMBS 真机预检回填：上游 4 用例（shunit2）与消费者 5 断言的实测数以预检日志为准，
本轮不猜测。详见 `021/notes.md`。
