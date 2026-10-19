# pnc

## 简介

`pnc` 是 libphonenumber 的命令行封装：校验、格式化、从文本中抽取电话号码，
并给出归属地（离线地理编码）与国际拨号串——全部本地完成，不访问网络。

上游：<https://git.sr.ht/~anjan/pnc>（已归档的 Orange-OpenSource/pn 的延续分支，
由 Sxmo 项目维护）

- 包名：`pnc/0.9.5`
- 构建系统：CMake
- 语言：C++ / C
- 许可：GPL-3.0-only

## 产物

| 路径 | 说明 |
|------|------|
| `bin/pnc` | 命令行工具（valid / info / format / find / dialout） |
| `share/man/man1/pnc.1` | 手册页 |
| `share/doc/pnc/README.md` | 上游说明 |
| `licenses/LICENSE` | GPL-3.0-only |

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| `libphonenumber` | 8.13.51 | 号码解析/校验/格式化 + 离线地理编码（静态库） |

`libphonenumber` 的静态传递依赖（protobuf / abseil-cpp / icu4c / zlib）由
pkg-config 元数据带入，见 `0.9.5/notes.md`。

## 使用

```sh
pnc format -c FR "0123456789"        # → +33123456789
pnc format -c FR -f nat "0123456789" # → 01 23 45 67 89
pnc valid -c US "(202) 555-0110"     # 退出码 0 表示有效
pnc info -c FR "0123456789"          # 含 location: France（离线地理编码）
pnc find -c FR "rappelle-moi au 01 23 4 56789"
pnc dialout -c FR "+12025550110"     # → 00 1 202-555-0110
```

## OHOS 适配

见 `0.9.5/notes.md`：依赖发现从硬编码 `/usr/local` 改为 pkg-config、protobuf
缺声明的 utf8 静态库补齐、上游测试用真实 shell 驱动。

## 未包含：GNU AWK 扩展（`gawkpn.so`）

上游同一份源码还带一个 GNU AWK 扩展（`gawkext/`）。**本包不构建它**：在
OHOS PC 上实测，该扩展会在**进程退出阶段**随机以 SIGTRAP/SIGABRT 终止
（输出已完整产出），触发条件是走 ICU 的地理编码路径（`pn_info`）。同一批
测量里 gawk 自带的 `filefuncs` 扩展 40/40 正常、同一批代码在 CLI 里 180/180
正常，而 `gawkpn.so` 每项 40 次运行有 **10–17 次失败（成功率 57.5%–75%）**；
复现命令与逐项数据见 `0.9.5/notes.md`。

这也是上游 CMakeLists 自身的分支：探不到 `gawkapi.h` 就打印
`Excluding gawk plugin` 并跳过，本包环境即落在这一分支。扩展的适配作为
独立任务（`pnc-gawk`）跟进，不在本包内发布已知会崩溃的产物。

## 参考

- 上游：<https://git.sr.ht/~anjan/pnc>
- 前身：<https://github.com/Orange-OpenSource/pn>
- libphonenumber：<https://github.com/google/libphonenumber>
