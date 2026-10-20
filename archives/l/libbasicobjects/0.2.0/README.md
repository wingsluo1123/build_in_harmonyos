# libbasicobjects 0.2.0(OHOS 适配)

## 简介

libbasicobjects 是 SSSD [ding-libs](https://github.com/SSSD/ding-libs) 集合中的
基础数据对象库,核心是 simplebuffer——一个可增长的字节缓冲区,用于序列化 IO
(growing buffer with automatic NUL termination)。它是 libini_config 等库的
底层依赖。

## 版本映射

| 项 | 值 |
|---|---|
| Conan 包版本 | 0.2.0(任务标识,制品仓无历史版本,R37 无冲突)|
| 上游源 | ding-libs 0.6.2 官方发行包 |
| 上游子库版本 | basicobjects 0.1.1(0.6.2 是最后提供独立库的版本;0.7.0 起并入 libini_config)|
| soname | libbasicobjects.so.0(上游 ABI 保持不变)|

## OHOS 适配

- 官方 autotools 构建(带预生成 configure 的发行包,构建机无需 autotools;
  codeload 备源走 autoreconf 兜底)。
- `--disable-nls`:OHOS musl 无 GNU gettext(伞形仓库中 path_utils 的
  libintl 声明会阻断全量构建;本库 API 纯 ASCII 零 NLS 依赖)。
- OHOS 显式 `--build/--host=aarch64-unknown-linux-gnu`(bundled
  config.guess 不识别 HarmonyOS)。
- 目标级构建 `make simplebuffer_ut`(连带 libbasicobjects.la),不执行
  伞形 `make all/install`;产物手动部署到 conan 包布局。
- 受限执行环境对策:make 传绝对路径 `SHELL`/`MKDIR_P`,UT 直跑 `.libs/`
  真 ELF(绕开 libtool /bin/sh wrapper)。
- 上游官方单测 simplebuffer_ut 在 build() 内执行(CI L1 门禁)。

## 依赖

无外部依赖(纯 libc)。

## 测试

- 上游官方:simplebuffer_ut(make check 的 basicobjects 条目),exit 0。
- 消费者探针(test_package):16 项断言,覆盖全部公开 API 与字节级
  round-trip、临时文件 IO 路径。

## 参考

- 上游仓库:https://github.com/SSSD/ding-libs
- 发行包:https://github.com/SSSD/ding-libs/releases/tag/0.6.2
