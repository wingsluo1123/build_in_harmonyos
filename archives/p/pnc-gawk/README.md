# pnc-gawk

## 简介

`pnc-gawk` 是 [pnc](https://git.sr.ht/~anjan/pnc) 项目提供的 GNU AWK 扩展
（Alpine Linux 子包 `pnc-gawk`，内容为 `usr/lib/gawk/gawkpn.so`）。它把
Google libphonenumber 的能力暴露给 AWK 程序：

- `pn_valid(NUMBER)` —— 号码/短号合法性（返回 0/1/2）
- `pn_format(NUMBER)` —— 按 `pn_set_format()` 指定的格式输出（e164/int/nat/teluri）
- `pn_info(NUMBER, ARRAY)` —— 国家码、国家、号码类型、离线归属地、短号/紧急号
- `pn_find(TEXT, ARRAY)` —— 从自由文本中提取号码
- `pn_dialout(E164NUMBER[, COUNTRY])` —— 生成国际拨号串
- `pn_set_country(CC)` / `pn_set_format(FMT)` / `pn_set_leniency(L)`

> **命名空间**：上游 `dl_load_func(func_table, "phonenumber", "phonenumber")`
> 把函数注册在 `phonenumber` 命名空间。GNU Awk 5.x 下需写
> `phonenumber::pn_format(...)`，或先 `@namespace "phonenumber"`。

## OHOS 适配

- 依赖发现：上游 `find_library(... PATHS /usr/local/lib)` 与
  `include_directories(BEFORE SYSTEM /usr/local/include)` 硬编码系统前缀，
  改为由构建驱动（Conan）注入 include 目录与静态链接闭包。
- 安装路径：上游 configure 期执行 `gawk` 读取 `AWKLIBPATH` 作为安装目录，
  交叉编译会得到构建机的绝对路径，改为前缀相对目录 `lib/gawk`
  （`-DAWKLIBPATH=` 可覆盖）。
- 运行期：`gawkpn.so` 依赖 `libc.so` 与 `libc++_shared.so`，OHOS 系统自带
  `/system/lib64/libc++_shared.so`，无需额外部署。

## 依赖

- `libphonenumber/8.13.51`（同包内含同源 `libgeocoding.a`）
- `icu4c/78`
- `gawk/5.3.0`（构建期 `gawkapi.h` + 运行期宿主）

## 功能验证

```bash
# 安装 gawk 扩展后（AWKLIBPATH=<pnc-gawk 包目录>/lib/gawk）
gawk -l gawkpn '@namespace "phonenumber"
BEGIN { pn_set_country("FR"); pn_set_format("e164"); print pn_format("0123456789") }'
# +33123456789
```

## 参考

- 上游仓库：https://git.sr.ht/~anjan/pnc
- 扩展说明：`gawkext/README.md`（上游）
