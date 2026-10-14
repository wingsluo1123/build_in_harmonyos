# pd-markex 0.85 适配笔记

## 上游构成

`pd-markex_0.85.orig.tar.gz` 是 Mark Danks 的 Pure Data 外部对象集合
**markex**，共 20 个类（`abs~`、`average`、`counter`、`hsv2rgb`、`rgb2hsv`、
`reson~`、`strcat`、`vectorpack`、`tripleLine` 等）。使用上游**老式 Pd library
template Makefile**（非 pd-lib-builder），每个类产出一个 `<class>.pd_linux`。

## 构建

- **Pd API 头**：制品仓 `puredata/0.54.1` 是 *application*，不暴露 `m_pd.h`。
  配方在 `source()` 额外拉取同版本 `pure-data 0.54-1` 源码树，`-I` 指向其 `src`。
- **平台识别**：老式模板用 `uname -s` 判平台；OHOS 报 `HarmonyOS` 不匹配任何分支
  → 在 `make` 命令行强制 `UNAME=Linux`（选中 `pd_linux` 扩展名与 `-shared` 链接旗标）。
- `CFLAGS` 在命令行整体给出（命令行为最高优先级，模板里的 `+= -O6` 被覆盖），
  内容为 `-I<pd-api>/src -DPD -fPIC -O2 -w`。纯 C，零三方依赖。
- 构建产出 **20** 个 `.pd_linux`。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 20 个 markex 外部对象 |
| `lib/pd-externals/*-help.pd` | 帮助补丁 |
| `lib/pd-externals/markex-meta.pd` | 库元数据 |

## 测试

上游无自动化测试套件（只有帮助补丁）→ 上游 N=0。

消费者测试 `test_package/test_pd_markex.sh`（3 项断言）用**真机 OHOS `pd`** 无头
加载安装后的外部对象，驱动三个确定性类：

- `[rgb2hsv]` 输入 `1 0 0` → `0 1 1`
- `[hsv2rgb]` 输入 `0 1 1` → `1 0 0`
- `[strcat foo]` 输入 `symbol bar` → `foobar`

真机 `conan create`：`CREATE_RC=0`，消费者 3/3。

> 备注：`pd` 的 `; pd quit;` 退出会与 `loadbang` 输出竞争丢行，测试改用
> `timeout 20` 结束 pd。
